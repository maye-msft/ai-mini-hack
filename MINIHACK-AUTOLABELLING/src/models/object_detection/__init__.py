# models/object_detection/__init__.py

from typing import Any, Dict

from .azure_computer_vision_detector import AzureComputerVisionDetector
from .azure_foundry_detector import AzureFoundryObjectDetector
from .object_detector import ObjectDetector
from .yolo_detector import YOLOObjectDetector


def create_object_detector(config: Dict[str, Any]) -> ObjectDetector:
    """
    Factory function to create appropriate object detector instance based on
    config type.

    Args:
        config (dict): Configuration containing detector type and parameters

    Returns:
        ObjectDetector: Instance of the appropriate object detector

    Raises:
        ValueError: If detector type is not supported
    """
    # Support both 'type' and 'model_type'
    detector_type = config.get("type", config.get("model_type"))

    if not detector_type:
        raise ValueError("Detector type must be specified in config " "(use 'type' or 'model_type')")

    if detector_type in ["yolo", "yolov5"]:
        return YOLOObjectDetector(config)
    elif detector_type == "azure_computer_vision":
        return AzureComputerVisionDetector(config)
    elif detector_type in ["azure_foundry", "azure_ai_foundry", "foundry"]:
        return AzureFoundryObjectDetector(config)
    else:
        raise ValueError(
            f"Unsupported detector type: {detector_type}. "
            f"Available types: ['yolo', 'yolov5', 'azure_computer_vision', "
            f"'azure_foundry']"
        )


__all__ = [
    "ObjectDetector",
    "YOLOObjectDetector",
    "AzureComputerVisionDetector",
    "AzureFoundryObjectDetector",
    "create_object_detector",
]
