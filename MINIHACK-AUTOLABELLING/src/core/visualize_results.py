# core/visualizer.py

import logging
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

from storage import create_storage_handler


class AnnotationVisualizer:
    """Visualizer for comparing generated annotations with ground truth."""

    def __init__(self, config: dict):
        """
        Initialize the visualizer.

        Args:
            config (dict): Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Color scheme for different types of annotations
        self.colors = {
            "generated": (0, 255, 0),  # Green for generated
            "ground_truth": (0, 0, 255),  # Red for ground truth
            "text": (255, 255, 255),  # White for text
        }

        try:
            self.images_store = create_storage_handler(self.config["storage"]["images"])
            self.ground_truth_annotations_store = create_storage_handler(
                self.config["storage"]["ground_truth_annotations"]
            )
            self.generated_annotations_store = create_storage_handler(self.config["storage"]["generated_annotations"])
            self.visualizations_output_store = create_storage_handler(self.config["storage"]["visualizations_output"])

        except Exception as e:
            self.logger.error(f"Failed to initialize components: {str(e)}")
            raise

    def get_annotation_color(self, annotation_type: str) -> Tuple[int, int, int]:
        """
        Get color for annotation type.

        Args:
            annotation_type (str): 'generated' or 'ground_truth'

        Returns:
            Tuple[int, int, int]: BGR color tuple
        """
        return self.colors[annotation_type]

    def draw_bounding_box(
        self,
        image: np.ndarray,
        bbox: Dict,
        category: str,
        annotation_type: str,
        confidence: Optional[float] = None,
    ) -> np.ndarray:
        """
        Draw a bounding box on the image.

        Args:
            image (np.ndarray): Image to draw on
            bbox (Dict): Bounding box with x1, y1, x2, y2
            category (str): Object category
            annotation_type (str): 'generated' or 'ground_truth'
            confidence (Optional[float]): Confidence score if available

        Returns:
            np.ndarray: Image with bounding box drawn
        """
        x1, y1, x2, y2 = (
            int(bbox["x1"]),
            int(bbox["y1"]),
            int(bbox["x2"]),
            int(bbox["y2"]),
        )
        color = self.get_annotation_color(annotation_type)

        # Line thickness based on annotation type
        thickness = 3 if annotation_type == "ground_truth" else 2
        line_type = cv2.LINE_8 if annotation_type == "ground_truth" else cv2.LINE_4

        # Draw bounding box
        cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness, lineType=line_type)

        # Prepare label text
        label_parts = [category]
        if confidence is not None:
            label_parts.append(f"{confidence:.2f}")

        # Add annotation type indicator
        type_indicator = "GT" if annotation_type == "ground_truth" else "GEN"
        label_parts.append(f"[{type_indicator}]")

        label = " ".join(label_parts)

        # Calculate text size and position
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        text_thickness = 2
        (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, text_thickness)

        # Position text above the box, or inside if there's no space
        text_y = y1 - 10 if y1 - 10 > text_height else y1 + text_height + 10
        text_x = x1

        # Draw text background
        cv2.rectangle(
            image,
            (text_x, text_y - text_height - baseline),
            (text_x + text_width, text_y + baseline),
            color,
            -1,
        )

        # Draw text
        cv2.putText(
            image,
            label,
            (text_x, text_y),
            font,
            font_scale,
            self.colors["text"],
            text_thickness,
        )

        return image

    def create_legend(self, image: np.ndarray) -> np.ndarray:
        """
        Add a legend to the image explaining the color coding.

        Args:
            image (np.ndarray): Input image

        Returns:
            np.ndarray: Image with legend added
        """
        height, width = image.shape[:2]
        legend_height = 100
        legend_width = 300

        # Create legend background
        legend = np.zeros((legend_height, legend_width, 3), dtype=np.uint8)
        legend.fill(50)  # Dark gray background

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1

        # Legend entries
        entries = [
            ("Ground Truth", self.colors["ground_truth"]),
            ("Generated", self.colors["generated"]),
        ]

        y_offset = 25
        for i, (label, color) in enumerate(entries):
            y_pos = y_offset + i * 30

            # Draw color box
            cv2.rectangle(legend, (10, y_pos - 10), (30, y_pos + 10), color, -1)

            # Draw label
            cv2.putText(
                legend,
                label,
                (40, y_pos + 5),
                font,
                font_scale,
                self.colors["text"],
                thickness,
            )

        # Position legend in top-right corner
        legend_y = 10
        legend_x = width - legend_width - 10

        # Ensure legend fits in image
        if legend_x < 0:
            legend_x = 10
        if legend_y + legend_height > height:
            legend_y = height - legend_height - 10

        # Overlay legend on image
        image[legend_y : legend_y + legend_height, legend_x : legend_x + legend_width] = legend

        return image

    def create_attributes_comparison(
        self,
        image: np.ndarray,
        generated_annotation: Dict,
        ground_truth_annotation: Optional[Dict] = None,
    ) -> np.ndarray:
        """
        Add attribute comparison text to the upper part of the image.

        Args:
            image (np.ndarray): Input image
            generated_annotation (Dict): Generated annotation data
            ground_truth_annotation (Optional[Dict]): Ground truth annotation data

        Returns:
            np.ndarray: Image with attribute comparison added
        """
        height, width = image.shape[:2]

        # Extract attributes
        gen_attrs = generated_annotation.get("attributes", {})
        gt_attrs = ground_truth_annotation.get("attributes", {}) if ground_truth_annotation else {}

        # Prepare comparison text
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        line_height = 20

        # Create attribute comparison lines
        attr_lines = []
        attr_names = ["weather", "timeofday", "scene"]

        for attr_name in attr_names:
            gen_val = gen_attrs.get(attr_name, "unknown")
            gt_val = gt_attrs.get(attr_name, "N/A")

            line_text = f"{attr_name.capitalize()}: GT={gt_val} | GEN={gen_val}"
            attr_lines.append((line_text, gen_val == gt_val and gt_val != "N/A"))

        # Calculate background size
        max_text_width = 0
        for line_text, _ in attr_lines:
            (text_width, text_height), _ = cv2.getTextSize(line_text, font, font_scale, thickness)
            max_text_width = max(max_text_width, text_width)

        bg_height = len(attr_lines) * line_height + 20  # 10px padding top/bottom
        bg_width = max_text_width + 20  # 10px padding left/right

        # Position in upper-left corner
        bg_x = 10
        bg_y = 10

        # Create semi-transparent background
        overlay = image.copy()
        cv2.rectangle(overlay, (bg_x, bg_y), (bg_x + bg_width, bg_y + bg_height), (0, 0, 0), -1)  # Black background

        # Apply transparency
        alpha = 0.7
        cv2.addWeighted(overlay, alpha, image, 1 - alpha, 0, image)

        # Draw attribute comparison lines
        for i, (line_text, is_match) in enumerate(attr_lines):
            text_x = bg_x + 10
            text_y = bg_y + 20 + i * line_height

            # Color based on match status
            if is_match:
                text_color = (0, 255, 0)  # Green for match
            else:
                text_color = (0, 100, 255)  # Orange for mismatch

            cv2.putText(
                image,
                line_text,
                (text_x, text_y),
                font,
                font_scale,
                text_color,
                thickness,
            )

        return image

    def visualize_annotations(
        self,
        image_name: str,
        generated_annotation: Dict,
        ground_truth_annotation: Optional[Dict] = None,
    ) -> np.ndarray:
        """
        Create visualization comparing generated and ground truth annotations.

        Args:
            image_name (str): Filename of the source image
            generated_annotation (Dict): Generated annotation data
            ground_truth_annotation (Optional[Dict]): Ground truth annotation data

        Returns:
            np.ndarray: Visualization image with bounding boxes
        """
        # Load image using storage handler
        image_bytes = self.images_store.load_file(image_name)
        if image_bytes is None:
            raise ValueError(f"Could not load image: {image_name}")

        # Convert bytes to cv2 image
        if isinstance(image_bytes, str):
            # If it's a string (shouldn't happen for images), encode it
            image_bytes = image_bytes.encode("utf-8")

        # Convert bytes to numpy array and then to cv2 image
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError(f"Could not decode image: {image_name}")

        # Draw ground truth annotations first (so they appear behind generated ones)
        if ground_truth_annotation and "labels" in ground_truth_annotation:
            for label in ground_truth_annotation["labels"]:
                if "box2d" in label and "category" in label:
                    self.draw_bounding_box(image, label["box2d"], label["category"], "ground_truth")

        # Draw generated annotations
        if "labels" in generated_annotation:
            for label in generated_annotation["labels"]:
                if "box2d" in label and "category" in label:
                    # Extract confidence if available
                    confidence = label.get("confidence", None)
                    self.draw_bounding_box(
                        image,
                        label["box2d"],
                        label["category"],
                        "generated",
                        confidence,
                    )

        # Add legend
        image = self.create_legend(image)

        # Add attributes comparison
        image = self.create_attributes_comparison(image, generated_annotation, ground_truth_annotation)

        # Add image info text
        image_name = Path(image_name).name
        info_text = f"Image: {image_name}"

        # Add processing status if available
        if "processing_status" in generated_annotation:
            status = generated_annotation["processing_status"]
            scene_status = status.get("scene_classification", "unknown")
            object_status = status.get("object_detection", "unknown")
            info_text += f" | Scene: {scene_status} | Objects: {object_status}"

        # Draw info text at bottom
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        (text_width, text_height), baseline = cv2.getTextSize(info_text, font, font_scale, thickness)

        # Background for text
        text_bg_height = text_height + baseline + 10
        cv2.rectangle(
            image,
            (0, image.shape[0] - text_bg_height),
            (image.shape[1], image.shape[0]),
            (0, 0, 0),
            -1,
        )

        # Draw text
        cv2.putText(
            image,
            info_text,
            (10, image.shape[0] - 10),
            font,
            font_scale,
            self.colors["text"],
            thickness,
        )

        return image

    def execute(self):
        """
        Process all images that have generated annotations and create visualizations.
        """
        start_time = time.time()

        # Get all images that have generated annotations
        generated_files = self.generated_annotations_store.list_files(pattern="*.json")

        self.logger.info(f"Found {len(generated_files)} generated annotation files")
        self.logger.info("Starting visualization processing...")

        processed_count = 0
        failed_count = 0
        skipped_count = 0
        completed_files = []
        failed_files = []

        for annotation_file in generated_files:
            try:
                # Extract image name from annotation filename
                annotation_filename = self.generated_annotations_store.get_filename(annotation_file)

                # Double extension case: remove only .json
                image_name = annotation_filename[:-5]

                # Check if visualization already exists
                viz_filename = image_name
                if self.visualizations_output_store.file_exists(viz_filename):
                    self.logger.debug(f"Skipping {image_name} - visualization already exists")
                    skipped_count += 1
                    continue

                if not self.images_store.file_exists(image_name):
                    self.logger.warning(f"Source image not found: {image_name}")
                    failed_count += 1
                    failed_files.append(image_name)
                    continue

                # Load generated annotation using storage handler
                generated_annotation = self.generated_annotations_store.load_json_file(annotation_filename)
                if not generated_annotation:
                    self.logger.warning(f"Could not load generated annotation for {image_name}")
                    failed_count += 1
                    failed_files.append(image_name)
                    continue

                # Load ground truth annotation with same filename as generated annotation
                ground_truth_annotation = self.ground_truth_annotations_store.load_json_file(annotation_filename)

                # Create visualization
                viz_image = self.visualize_annotations(image_name, generated_annotation, ground_truth_annotation)

                # Convert to bytes and save using storage handler
                success, img_encoded = cv2.imencode(".jpg", viz_image)
                if success:
                    self.visualizations_output_store.save_file(viz_filename, img_encoded.tobytes())
                    processed_count += 1
                    completed_files.append(image_name)
                    if processed_count % 10 == 0:
                        self.logger.info(f"Processed {processed_count} visualizations")
                else:
                    self.logger.error(f"Failed to encode visualization for {image_name}")
                    failed_count += 1
                    failed_files.append(image_name)

            except Exception as e:
                annotation_filename = self.generated_annotations_store.get_filename(annotation_file)
                image_name = annotation_filename[:-5] if annotation_filename.endswith(".json") else annotation_filename
                self.logger.error(f"Error processing {annotation_file}: {str(e)}")
                failed_count += 1
                failed_files.append(image_name)

        end_time = time.time()
        processing_time = end_time - start_time

        # Simple logging
        if skipped_count > 0:
            self.logger.info(f"Skipped {skipped_count} images that already have visualizations")

        self.logger.info(f"Visualization complete: {processed_count} processed, {failed_count} failed")
        self.logger.info("Visualizations saved using configured storage handler")

        # Return simple stats
        return {
            "processed": processed_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "completed_files": completed_files,
            "failed_files": failed_files,
            "processing_time": processing_time,
        }
