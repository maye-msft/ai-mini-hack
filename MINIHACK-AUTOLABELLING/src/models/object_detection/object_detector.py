# models/object_detection/object_detector.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ObjectDetector(ABC):
    """Abstract base class for object detection models."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the object detector with configuration.

        Args:
            config (dict): Detector configuration
        """
        self.config = config

    @abstractmethod
    def detect_objects(self, image_data: bytes, confidence_threshold: Optional[float] = None) -> List[Dict]:
        """
        Detect objects in an image and return a list of annotation labels in BDD-style format.

        Args:
            image_data: The image data
            confidence_threshold (float): Minimum confidence for keeping detections (uses config default if None)

        Returns:
            List[Dict]: List of object label dicts in BDD format
        """
        pass
