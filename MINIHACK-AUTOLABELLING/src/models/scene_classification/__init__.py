# models/scene_classification/__init__.py

from typing import Any, Dict

from .openai_classifier import OpenAISceneClassifier
from .phi_classifier import PhiSceneClassifier
from .scene_classifier import SceneClassifier


def create_scene_classifier(config: Dict[str, Any]) -> SceneClassifier:
    """
    Factory function to create appropriate scene classifier instance based on config type.

    Args:
        config (dict): Configuration containing classifier type and parameters

    Returns:
        SceneClassifier: Instance of the appropriate scene classifier

    Raises:
        ValueError: If classifier type is not supported
    """
    classifier_type = config.get("type")

    if not classifier_type:
        raise ValueError("Classifier type must be specified in config")

    if classifier_type == "openai":
        return OpenAISceneClassifier(config)

    elif classifier_type == "phi":
        return PhiSceneClassifier(config)

    raise ValueError(f"Unsupported classifier type: {classifier_type}. " f"Available types: ['openai', 'phi']")


__all__ = [
    "SceneClassifier",
    "OpenAISceneClassifier",
    "PhiSceneClassifier",
    "create_scene_classifier",
]
