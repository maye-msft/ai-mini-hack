# models/object_detection/azure_computer_vision_detector.py

import io
import logging
import uuid
from typing import Any, Dict, List, Optional

from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
from PIL import Image

from .object_detector import ObjectDetector


class AzureComputerVisionDetector(ObjectDetector):
    """Azure Computer Vision-based object detector implementation."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the Azure Computer Vision detector with configuration."""
        super().__init__(config)

        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Get configuration
        self.endpoint = config.get("endpoint")
        self.key = config.get("api_key")
        self.confidence_threshold = config.get("confidence_threshold", 0.5)

        if not self.endpoint:
            raise ValueError("Azure Computer Vision requires endpoint")

        if not self.key:
            raise ValueError("Azure Computer Vision requires key")

        credentials = CognitiveServicesCredentials(self.key)

        self.client = ComputerVisionClient(self.endpoint, credentials)

    def detect_objects(self, image_data: bytes, confidence_threshold: Optional[float] = None) -> List[Dict]:
        """
        Detect objects in an image using Azure Computer Vision and return
        BDD-style annotations.

        Args:
            image_data: The image data
            confidence_threshold (float): Minimum confidence for keeping
                detections (uses config default if None)

        Returns:
            List[Dict]: List of object label dicts in BDD format
        """
        if confidence_threshold is None:
            confidence_threshold = self.confidence_threshold

        try:
            # Get image dimensions for coordinate conversion
            image = Image.open(io.BytesIO(image_data))
            img_width, img_height = image.size

            # Create a stream from image data
            image_stream = io.BytesIO(image_data)

            # Detect objects using Computer Vision API
            self.logger.debug(
                f"Calling Azure Computer Vision API with confidence " f"threshold: {confidence_threshold}"
            )
            detect_objects_results = self.client.detect_objects_in_stream(image_stream)

            labels = []
            for obj in detect_objects_results.objects:
                if obj.confidence < confidence_threshold:
                    continue

                # Convert from Computer Vision rectangle to BDD format
                # Computer Vision returns absolute pixel coordinates
                bbox = obj.rectangle

                label = {
                    "id": str(uuid.uuid4().int)[:6],
                    "category": obj.object_property,
                    "box2d": {
                        "x1": bbox.x,
                        "y1": bbox.y,
                        "x2": bbox.x + bbox.w,
                        "y2": bbox.y + bbox.h,
                    },
                }

                labels.append(label)

            self.logger.debug(f"Azure Computer Vision detected {len(labels)} objects " f"above confidence threshold")
            return labels

        except Exception as e:
            self.logger.error(f"Failed to detect objects with Azure Computer Vision: {e}")
            return []
