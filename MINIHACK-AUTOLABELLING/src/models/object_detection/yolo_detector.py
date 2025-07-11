# models/object_detection/yolo_detector.py

import logging
import uuid
from io import BytesIO
from typing import Any, Dict, List, Optional

from PIL import Image
from ultralytics import YOLO

from .object_detector import ObjectDetector


class YOLOObjectDetector(ObjectDetector):
    """YOLO-based object detector implementation."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize the YOLO detector with configuration."""
        super().__init__(config)

        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Get model path from config or use default
        model_path = config.get("model_path", "yolov5s.pt")
        self.confidence_threshold: float = config.get("confidence_threshold", 0.25)

        # Load the YOLO model
        self.logger.debug(f"Loading YOLO model from: {model_path}")
        self.model = YOLO(model_path)
        self.logger.debug("YOLO model loaded successfully")

    def detect_objects(self, image_data: bytes, confidence_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Detect objects in an image using YOLO and return BDD-style annotations.

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
            # Create PIL Image from bytes for YOLO
            image = Image.open(BytesIO(image_data))

            self.logger.debug(f"Running YOLO inference with confidence threshold: " f"{confidence_threshold}")

            results = self.model(image)[0]
            results = results.boxes

            labels: List[Dict[str, Any]] = []
            for box in results:
                conf = float(box.conf)
                if conf < confidence_threshold:
                    continue

                x1, y1, x2, y2 = map(float, box.xyxy[0])
                category = self.model.names[int(box.cls[0])]

                label = {
                    "id": str(uuid.uuid4().int)[:6],
                    "category": category,
                    "box2d": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                }

                labels.append(label)

            self.logger.debug(f"YOLO detected {len(labels)} objects above confidence " f"threshold")
            return labels

        except Exception as e:
            self.logger.error(f"Failed to detect objects with YOLO: {e}")
            return []
