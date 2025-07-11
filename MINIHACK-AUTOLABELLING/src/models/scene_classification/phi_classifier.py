# models/scene_classification/phi_classifier.py

import base64
import json
import logging
import os
import time
from pathlib import Path

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

from .scene_classifier import SceneClassifier


class PhiSceneClassifier(SceneClassifier):
    """Microsoft Phi-4-Multimodal scene classifier with error handling."""

    def __init__(self, config: dict):
        """Initialize the Phi classifier with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Error handling configuration
        self.retries = config.get("retries", 3)
        self.delay = config.get("retry_delay", 2)
        self.max_delay = config.get("max_retry_delay", 60)

        # Track failure statistics
        self.failure_stats = {
            "total_attempts": 0,
            "total_failures": 0,
            "rate_limit_errors": 0,
            "content_filter_errors": 0,
            "auth_errors": 0,
            "other_errors": 0,
        }

        # Get endpoint and API key directly from resolved config
        endpoint = config.get("endpoint")
        api_key = config.get("api_key")
        api_version = config.get("api_version", "2024-12-01-preview")

        if not endpoint:
            raise ValueError("endpoint is required in config")
        if not api_key:
            raise ValueError("api_key is required in config")

        # Initialize Azure AI Foundry project client with API key credential
        self.client = ChatCompletionsClient(
            endpoint=endpoint, credential=AzureKeyCredential(api_key), api_version=api_version
        )

        # Load prompts
        prompt_version = config.get("prompt_version", "v1")
        system_prompt_file = os.path.join(Path(__file__).parent, "prompts", prompt_version, "system_message.md")
        if not os.path.exists(system_prompt_file):
            raise FileNotFoundError(f"Prompt directory {system_prompt_file} does not exist")

        self.system_prompt = ""
        with open(system_prompt_file, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

        self.model_name = config.get("model_name", "Phi-4-multimodal-instruct")
        self.temperature = config.get("temperature", 0.2)
        self.max_tokens = config.get("max_tokens", 512)

    def get_failure_stats(self) -> dict:
        """Get current failure statistics."""
        stats = self.failure_stats.copy()
        if stats["total_attempts"] > 0:
            success_count = stats["total_attempts"] - stats["total_failures"]
            stats["success_rate"] = success_count / stats["total_attempts"]
        else:
            stats["success_rate"] = 0.0
        return stats

    def log_failure_stats(self):
        """Log current failure statistics."""
        stats = self.get_failure_stats()
        self.logger.info(
            f"Scene classification stats: {stats['total_attempts']} attempts, "
            f"{stats['total_failures']} failures, "
            f"{stats['success_rate']:.2%} success rate"
        )

    def classify_scene(self, image_name: str, image_data: bytes) -> dict:
        """
        Classify scene attributes using Phi-4-Multimodal with error handling.

        Args:
            image_name: Name of the image file
            image_data: The image data in bytes

        Returns:
            dict: Dictionary with keys: weather, timeofday, scene
        """

        self.failure_stats["total_attempts"] += 1

        # Prepare fallback response
        fallback_response = {
            "weather": "unknown",
            "timeofday": "unknown",
            "scene": "unknown",
        }

        try:
            # Convert image to base64
            image_base64 = base64.b64encode(image_data).decode("utf-8")

            # Create messages for multimodal chat completion
            messages = [
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                    ],
                },
            ]

            # Retry loop for API calls
            for attempt in range(self.retries):
                try:
                    response = self.client.complete(
                        model=self.model_name,
                        messages=messages,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                    )

                    # Parse response
                    try:
                        content = response.choices[0].message.content

                        # Try to extract JSON from the response
                        if "```json" in content:
                            # Extract JSON block
                            start = content.find("```json") + 7
                            end = content.find("```", start)
                            json_content = content[start:end].strip()
                        elif "{" in content and "}" in content:
                            # Find JSON object
                            start = content.find("{")
                            end = content.rfind("}") + 1
                            json_content = content[start:end]
                        else:
                            json_content = content

                        attributes = json.loads(json_content)
                        result = attributes.get("attributes", attributes)

                        # Validate required keys exist
                        for key in ["weather", "timeofday", "scene"]:
                            if key not in result:
                                result[key] = "unknown"

                        return result

                    except (
                        json.JSONDecodeError,
                        KeyError,
                        AttributeError,
                    ) as parse_error:
                        self.logger.warning(f"Failed to parse Phi response for " f"{image_name}: {parse_error}")
                        if attempt + 1 == self.retries:
                            self.failure_stats["other_errors"] += 1
                            return fallback_response
                        continue

                except Exception as e:
                    error_message = str(e).lower()

                    # Check for specific error types
                    if "rate limit" in error_message or "429" in error_message:
                        self.failure_stats["rate_limit_errors"] += 1
                        retry_after = self.delay * (2**attempt)
                        retry_after = min(retry_after, self.max_delay)

                        if attempt + 1 < self.retries:
                            self.logger.warning(
                                f"Rate limit hit for {image_name}. "
                                f"Retrying after {retry_after} seconds "
                                f"(attempt {attempt + 1}/{self.retries})"
                            )
                            time.sleep(retry_after)
                            continue
                        else:
                            self.logger.error(
                                f"Rate limit exhausted after {self.retries} " f"attempts for {image_name}"
                            )
                            self.failure_stats["total_failures"] += 1
                            return fallback_response

                    elif "auth" in error_message or "unauthorized" in error_message or "403" in error_message:
                        # Authentication error - don't retry
                        self.logger.error(f"Authentication error for {image_name}: {str(e)}")
                        self.failure_stats["auth_errors"] += 1
                        self.failure_stats["total_failures"] += 1
                        # Re-raise auth errors as they need immediate attention
                        raise

                    elif "content filter" in error_message or "400" in error_message:
                        # Content filtering or bad request - don't retry
                        self.logger.warning(f"Content filter or bad request for " f"{image_name}: {str(e)}")
                        self.failure_stats["content_filter_errors"] += 1
                        self.failure_stats["total_failures"] += 1
                        return fallback_response

                    else:
                        # Other unexpected errors
                        if attempt + 1 < self.retries:
                            delay = self.delay * (2**attempt)
                            self.logger.warning(
                                f"Unexpected error for {image_name}: {str(e)}."
                                f" Retrying after {delay} seconds "
                                f"(attempt {attempt + 1}/{self.retries})"
                            )
                            time.sleep(delay)
                            continue
                        else:
                            self.logger.error(
                                f"Unexpected error after {self.retries} " f"attempts for {image_name}: {str(e)}"
                            )
                            self.failure_stats["other_errors"] += 1
                            self.failure_stats["total_failures"] += 1
                            return fallback_response

            # Should not reach here, but just in case
            self.failure_stats["total_failures"] += 1
            return fallback_response

        except Exception as e:
            # Catch-all for any other errors (like image processing errors)
            self.logger.error(f"Failed to process image {image_name}: {str(e)}")
            self.failure_stats["other_errors"] += 1
            self.failure_stats["total_failures"] += 1
            return fallback_response
