# models/object_detection/azure_yolo.py

import base64
import logging
import uuid
from io import BytesIO
from typing import Any, Dict, List, Optional

import requests
from PIL import Image

from .object_detector import ObjectDetector


class AzureFoundryObjectDetector(ObjectDetector):
    """Azure AI Foundry deployed model object detector implementation."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize the Azure AI Foundry detector with configuration."""
        super().__init__(config)

        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Get configuration
        self.endpoint = config.get("endpoint")
        self.api_key = config.get("api_key")
        self.confidence_threshold = config.get("confidence_threshold", 0.5)
        self.deployment_name = config.get("deployment_name", "mmd-3x-yolof-r50-c5-8x8-1x-c-13")

        if not self.endpoint:
            raise ValueError("Azure AI Foundry requires endpoint")

        if not self.api_key:
            raise ValueError("Azure AI Foundry requires api_key")

        # Prepare headers for API requests
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        self.logger.debug(f"Initialized Azure AI Foundry detector with deployment: " f"{self.deployment_name}")

    def _prepare_image_payload(self, image_data: bytes) -> Dict[str, Any]:
        """
        Prepare the image payload for the Azure AI Foundry API.

        Args:
            image_data: Raw image bytes

        Returns:
            Dict containing the API payload
        """
        # Convert image to base64 for API
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        # Create payload in the format expected by the deployed model
        payload = {"input_data": {"columns": ["image"], "index": [0], "data": [image_b64]}}

        return payload

    def _parse_response(
        self, response_data: Dict[str, Any], confidence_threshold: float, image_width: int, image_height: int
    ) -> List[Dict[str, Any]]:
        """
        Parse the Azure AI Foundry API response into BDD format.

        Args:
            response_data: The API response data
            confidence_threshold: Minimum confidence for keeping detections
            image_width: Width of the image in pixels
            image_height: Height of the image in pixels

        Returns:
            List of object detections in BDD format
        """
        labels = []

        try:
            # Handle the specific response format from Azure AI Foundry
            # Expected format: response_data[0]['boxes'] contains the detections

            if not isinstance(response_data, list) or len(response_data) == 0:
                raise ValueError(f"Expected list response, got {type(response_data)}")

            if "boxes" not in response_data[0]:
                raise ValueError(f"Expected 'boxes' key in response[0], got keys: {list(response_data[0].keys())}")

            boxes_data = response_data[0]["boxes"]

            if not isinstance(boxes_data, list):
                raise ValueError(f"Expected 'boxes' to be a list, got {type(boxes_data)}")

            for detection in boxes_data:
                if isinstance(detection, dict):
                    # Extract confidence/score
                    confidence = detection.get("score", detection.get("confidence", 0.0))

                    if confidence < confidence_threshold:
                        continue

                    # Extract category/label
                    category = detection.get("label")
                    if not category:
                        self.logger.warning(f"Missing category in detection: {category}")
                        continue

                    # Extract bounding box
                    bbox = detection.get("box", detection.get("bbox", detection.get("bounding_box")))

                    if bbox and isinstance(bbox, dict):
                        # Azure AI Foundry format: topX, topY, bottomX, bottomY (normalized coordinates)
                        if all(key in bbox for key in ["topX", "topY", "bottomX", "bottomY"]):
                            x1, y1, x2, y2 = bbox["topX"], bbox["topY"], bbox["bottomX"], bbox["bottomY"]
                            # Convert normalized coordinates to absolute pixel values
                            x1 = x1 * image_width
                            y1 = y1 * image_height
                            x2 = x2 * image_width
                            y2 = y2 * image_height
                        else:
                            self.logger.warning(f"Unexpected bbox format: {bbox}")
                            continue

                        label = {
                            "id": str(uuid.uuid4().int)[:6],
                            "category": str(category),
                            "box2d": {"x1": float(x1), "y1": float(y1), "x2": float(x2), "y2": float(y2)},
                        }
                        labels.append(label)
                    else:
                        self.logger.warning(f"Missing or invalid bbox in detection: {detection}")
                        continue

            self.logger.debug(f"Parsed {len(labels)} detections above confidence threshold")
            return labels

        except Exception as e:
            self.logger.error(f"Failed to parse Azure AI Foundry response: {e}")
            return []

    def detect_objects(self, image_data: bytes, confidence_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Detect objects in an image using Azure AI Foundry deployed model.

        Args:
            image_data: The image data
            confidence_threshold: Minimum confidence for keeping detections
                (uses config default if None)

        Returns:
            List[Dict]: List of object label dicts in BDD format
        """
        if confidence_threshold is None:
            confidence_threshold = self.confidence_threshold

        try:
            # Load image to get dimensions
            image = Image.open(BytesIO(image_data))
            image_width, image_height = image.size

            # Prepare the API payload
            payload = self._prepare_image_payload(image_data)

            self.logger.debug(
                f"Calling Azure AI Foundry endpoint with confidence " f"threshold: {confidence_threshold}"
            )

            # Make API request
            response = requests.post(self.endpoint, headers=self.headers, json=payload, timeout=30)

            if response.status_code != 200:
                self.logger.error(
                    f"Azure AI Foundry API request failed with status " f"{response.status_code}: {response.text}"
                )
                return []

            response_data = response.json()

            # Parse response into BDD format
            labels = self._parse_response(response_data, confidence_threshold, image_width, image_height)

            self.logger.debug(f"Azure AI Foundry detected {len(labels)} objects above " f"confidence threshold")
            return labels

        except requests.exceptions.Timeout:
            self.logger.error("Azure AI Foundry API request timed out")
            return []
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Azure AI Foundry API request failed: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Failed to detect objects with Azure AI Foundry: {e}")
            return []
