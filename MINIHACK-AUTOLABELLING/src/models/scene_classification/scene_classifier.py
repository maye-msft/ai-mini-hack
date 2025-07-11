# models/scene_classifier.py

from abc import ABC, abstractmethod
from typing import Any, Dict


class SceneClassifier(ABC):
    """Abstract base class for scene classification models."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the scene classifier with configuration.

        Args:
            config (dict): Classifier configuration
        """
        self.config = config

    @abstractmethod
    def classify_scene(self, image_name: str, image_data: bytes) -> dict:
        """
        Classify scene-level attributes from an image.

        Args:
            image_data: The image data
            config (dict): Optional runtime configuration (uses instance config if None)

        Returns:
            dict: Dictionary with keys: weather, timeofday, scene
        """
        pass
