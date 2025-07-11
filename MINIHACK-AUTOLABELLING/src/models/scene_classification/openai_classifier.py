# models/scene_classification/openai_classifier.py

import base64
import json
import logging
import os
import time
from pathlib import Path

from openai import AuthenticationError, AzureOpenAI, BadRequestError, RateLimitError

from .scene_classifier import SceneClassifier


class OpenAISceneClassifier(SceneClassifier):
    """OpenAI-based scene classifier implementation with robust error handling."""

    def __init__(self, config: dict):
        """Initialize the OpenAI classifier with configuration."""
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
        if not endpoint:
            raise ValueError("endpoint is required in config")

        api_version = config.get("api_version", "2024-12-01-preview")
        api_key = config.get("api_key")
        if not api_key:
            raise ValueError("api_key is required in config")

        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )

        # Load prompts
        prompt_version = config.get("prompt_version", "v1")
        system_prompt_file = os.path.join(Path(__file__).parent, "prompts", prompt_version, "system_message.md")
        if not os.path.exists(system_prompt_file):
            raise FileNotFoundError(f"Prompt directory {system_prompt_file} does not exist")

        self.system_prompt = ""
        with open(system_prompt_file, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

        self.model_name = config.get("model_name", "gpt-4o")
        self.temperature = config.get("temperature", 0.2)
        self.max_tokens = config.get("max_tokens", 512)

    def get_failure_stats(self) -> dict:
        """Get current failure statistics."""
        stats = self.failure_stats.copy()
        if stats["total_attempts"] > 0:
            stats["success_rate"] = (stats["total_attempts"] - stats["total_failures"]) / stats["total_attempts"]
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
        Classify scene-level attributes from an image using OpenAI VLM with robust error handling.

        Args:
            image_data: The image data

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
            image_content = {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(image_data).decode()}"},
            }

            # Retry loop for API calls
            for attempt in range(self.retries):
                try:
                    # Call Azure OpenAI
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=[
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": [image_content]},
                        ],
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        response_format={"type": "json_object"},
                    )

                    # Parse response
                    try:
                        attributes = json.loads(response.choices[0].message.content)
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
                        self.logger.warning(f"Failed to parse OpenAI response for {image_name}: {parse_error}")
                        if attempt + 1 == self.retries:
                            self.failure_stats["other_errors"] += 1
                            return fallback_response
                        continue

                except BadRequestError as e:
                    error_code = e.response.status_code if hasattr(e, "response") else 400
                    if error_code == 400:
                        # Content filtering or bad request - don't retry
                        self.logger.warning(f"Content filter or bad request for {image_name}: {str(e)}")
                        self.failure_stats["content_filter_errors"] += 1
                        self.failure_stats["total_failures"] += 1
                        return fallback_response
                    else:
                        self.logger.error(f"Bad request error {error_code} for {image_name}: {str(e)}")
                        if attempt + 1 == self.retries:
                            self.failure_stats["other_errors"] += 1
                            self.failure_stats["total_failures"] += 1
                            return fallback_response

                except RateLimitError as e:
                    self.failure_stats["rate_limit_errors"] += 1
                    retry_after = getattr(e, "retry_after", None) or self.delay * (2**attempt)
                    retry_after = min(retry_after, self.max_delay)

                    if attempt + 1 < self.retries:
                        self.logger.warning(
                            f"Rate limit hit for {image_name}. "
                            f"Retrying after {retry_after} seconds (attempt {attempt + 1}/{self.retries})"
                        )
                        time.sleep(retry_after)
                        continue
                    else:
                        self.logger.error(f"Rate limit exhausted after {self.retries} attempts for {image_name}")
                        self.failure_stats["total_failures"] += 1
                        return fallback_response

                except AuthenticationError as e:
                    # Authentication error - don't retry, this is a configuration issue
                    self.logger.error(f"Authentication error for {image_name}: {str(e)}")
                    self.failure_stats["auth_errors"] += 1
                    self.failure_stats["total_failures"] += 1
                    raise  # Re-raise auth errors as they need immediate attention

                except Exception as e:
                    # Other unexpected errors
                    if attempt + 1 < self.retries:
                        delay = self.delay * (2**attempt)
                        self.logger.warning(
                            f"Unexpected error for {image_name}: {str(e)}. "
                            f"Retrying after {delay} seconds (attempt {attempt + 1}/{self.retries})"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        self.logger.error(f"Unexpected error after {self.retries} attempts for {image_name}: {str(e)}")
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
