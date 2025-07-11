import logging
import time

from models.object_detection import create_object_detector
from models.scene_classification import create_scene_classifier
from storage import create_storage_handler


class ImageAnnotator:
    """Simple image annotator for generating annotations using AI models."""

    def __init__(self, config: dict, limit: int = None):
        """
        Initialize the annotator with configuration.

        Args:
            config (dict): Configuration dictionary
            limit (int, optional): Maximum number of images to process (for testing)
        """
        self.config = config
        self.limit = limit
        self.logger = logging.getLogger(__name__)

        # Processing statistics
        self.stats = {
            "total_images": 0,
            "successful_annotations": 0,
            "failed_images": 0,
            "scene_classification_failures": 0,
            "object_detection_failures": 0,
            "storage_failures": 0,
            "start_time": None,
            "end_time": None,
        }

        # Error handling configuration
        self.continue_on_error = config.get("continue_on_error", True)
        self.max_consecutive_failures = config.get("max_consecutive_failures", 10)

        try:
            self.images_store = create_storage_handler(config["storage"]["images"])
            self.annotation_store = create_storage_handler(config["storage"]["generated_annotations"])
            self.scene_classifier = create_scene_classifier(config["scene_classifier"])
            self.object_detector = create_object_detector(config["object_detector"])
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {str(e)}")
            raise

    def save_annotation(self, annotation: dict, image_name: str) -> bool:
        """Save annotation using the configured storage handler."""
        try:
            # Generate filename based on image resource
            filename = f"{image_name}.json"

            # Use the modern save_json_file method
            self.annotation_store.save_json_file(filename, annotation)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save annotation for {image_name}: {str(e)}")
            self.stats["storage_failures"] += 1
            return False

    def annotate_image(self, image: str) -> dict:
        """
        Generate annotation for a single image with error handling.

        Args:
            image: The image to be annotated

        Returns:
            dict: Annotation dictionary with success/failure indicators.
        """
        image_data = self.images_store.load_file(image)
        image_name = self.images_store.get_filename(image)
        annotation = {
            "name": image_name,
            "attributes": {
                "weather": "unknown",
                "timeofday": "unknown",
                "scene": "unknown",
            },
            "labels": [],
            "processing_status": {
                "scene_classification": "unknown",
                "object_detection": "unknown",
            },
        }

        # Scene classification with error handling
        try:
            scene_metadata = self.scene_classifier.classify_scene(image_name, image_data)
            if scene_metadata and not all(v == "unknown" for v in scene_metadata.values()):
                annotation["attributes"].update(scene_metadata)
                annotation["processing_status"]["scene_classification"] = "success"
            else:
                annotation["processing_status"]["scene_classification"] = "failed"
                self.stats["scene_classification_failures"] += 1
        except Exception as e:
            self.logger.error(f"Scene classification failed for {image_name}: {str(e)}")
            annotation["processing_status"]["scene_classification"] = "error"
            self.stats["scene_classification_failures"] += 1

        # Object detection with error handling
        try:
            object_labels = self.object_detector.detect_objects(image_data)
            if object_labels:
                annotation["labels"] = object_labels
                annotation["processing_status"]["object_detection"] = "success"
            else:
                annotation["processing_status"]["object_detection"] = "failed"
                self.stats["object_detection_failures"] += 1
        except Exception as e:
            self.logger.error(f"Object detection failed for {image_name}: {str(e)}")
            annotation["processing_status"]["object_detection"] = "error"
            self.stats["object_detection_failures"] += 1

        return annotation

    def log_progress_stats(self, current: int, total: int) -> None:
        """Log current progress and statistics."""
        if current % 10 == 0 or current == total:  # Log every 10 images or at the end
            success_rate = (self.stats["successful_annotations"] / current) * 100 if current > 0 else 0
            self.logger.info(
                f"Progress: {current}/{total} ({current / total * 100:.1f}%) - "
                f"Success rate: {success_rate:.1f}% - "
                f"Failures: {self.stats['failed_images']}"
            )

    def log_final_stats(self) -> None:
        """Log final processing statistics."""
        duration = (self.stats["end_time"] - self.stats["start_time"]) if self.stats["start_time"] else 0

        self.logger.info("=== PROCESSING COMPLETE ===")
        self.logger.info(f"Total images processed: {self.stats['total_images']}")
        self.logger.info(f"Successful annotations: {self.stats['successful_annotations']}")
        self.logger.info(f"Failed images: {self.stats['failed_images']}")
        self.logger.info(f"Scene classification failures: {self.stats['scene_classification_failures']}")
        self.logger.info(f"Object detection failures: {self.stats['object_detection_failures']}")
        self.logger.info(f"Storage failures: {self.stats['storage_failures']}")

        if self.stats["total_images"] > 0:
            success_rate = (self.stats["successful_annotations"] / self.stats["total_images"]) * 100
            self.logger.info(f"Overall success rate: {success_rate:.1f}%")

        if duration > 0:
            self.logger.info(f"Total processing time: {duration:.2f} seconds")
            images_per_second = self.stats["total_images"] / duration
            self.logger.info(f"Processing rate: {images_per_second:.2f} images/second")

        # Log component-specific stats if available
        if hasattr(self.scene_classifier, "log_failure_stats"):
            self.scene_classifier.log_failure_stats()

    def execute(self) -> dict:
        """Process images according to configuration with comprehensive error handling."""
        self.stats["start_time"] = time.time()
        consecutive_failures = 0

        # Lists to track individual files
        completed_files = []
        failed_files = []

        try:
            # Get all files from storage
            all_files = self.images_store.list_files()

            # Filter for image files and process on-the-fly
            valid_extensions = {
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".bmp",
                ".tiff",
                ".tif",
                ".webp",
            }

            processed_count = 0
            skipped_count = 0

            self.logger.info(f"Starting image processing with limit: {self.limit or 'unlimited'}")

            for file in all_files:
                filename = self.images_store.get_filename(file)

                # Check if it's an image file
                if "." in filename:
                    file_extension = "." + filename.split(".")[-1].lower()
                else:
                    file_extension = ""

                if file_extension not in valid_extensions:
                    continue  # Skip non-image files

                # Check if annotation already exists
                annotation_filename = f"{filename}.json"
                if self.annotation_store.file_exists(annotation_filename):
                    self.logger.debug(f"Skipping {filename} - annotation already exists")
                    skipped_count += 1
                    continue

                # Check if we've hit our limit
                if self.limit and processed_count >= self.limit:
                    break

                try:
                    self.logger.debug(f"Processing: {filename}")
                    annotation = self.annotate_image(file)

                    # Check if annotation was successful (at least one component worked)
                    scene_success = annotation["processing_status"]["scene_classification"] == "success"
                    object_success = annotation["processing_status"]["object_detection"] == "success"

                    if scene_success or object_success:
                        # Save annotation if at least one component succeeded
                        if self.save_annotation(annotation, filename):
                            self.stats["successful_annotations"] += 1
                            completed_files.append(filename)
                            consecutive_failures = 0  # Reset consecutive failure counter
                            processed_count += 1
                        else:
                            self.stats["failed_images"] += 1
                            failed_files.append(filename)
                            consecutive_failures += 1
                    else:
                        # Both components failed
                        self.stats["failed_images"] += 1
                        failed_files.append(filename)
                        consecutive_failures += 1
                        self.logger.warning(f"Both scene classification and object detection failed for {filename}")

                    # Update total processed for stats
                    self.stats["total_images"] = processed_count + len(failed_files)

                    # Check for too many consecutive failures
                    if consecutive_failures >= self.max_consecutive_failures:
                        if self.continue_on_error:
                            self.logger.warning(
                                f"Hit {consecutive_failures} consecutive failures. "
                                f"There may be a systemic issue. Consider checking your configuration."
                            )
                            consecutive_failures = 0  # Reset to continue processing
                        else:
                            self.logger.error(
                                f"Stopping after {consecutive_failures} consecutive failures. "
                                f"Set 'continue_on_error: false' in config to change this behavior."
                            )
                            break

                    # Log progress periodically
                    total_attempts = processed_count + len(failed_files)
                    if total_attempts % 10 == 0 and total_attempts > 0:
                        success_rate = (self.stats["successful_annotations"] / total_attempts) * 100
                        self.logger.info(
                            f"Progress: {total_attempts} processed ({processed_count} successful) - "
                            f"Success rate: {success_rate:.1f}% - "
                            f"Skipped: {skipped_count}"
                        )

                except KeyboardInterrupt:
                    self.logger.info("Processing interrupted by user")
                    break
                except Exception as e:
                    self.logger.error(f"Unexpected error processing {filename}: {str(e)}")
                    self.stats["failed_images"] += 1
                    failed_files.append(filename)
                    consecutive_failures += 1

                    if not self.continue_on_error:
                        self.logger.error(
                            "Stopping due to error. Set 'continue_on_error: true' in config to continue on errors."
                        )
                        break

        except Exception as e:
            self.logger.error(f"Critical error during processing: {str(e)}")
            raise

        finally:
            self.stats["end_time"] = time.time()
            self.stats["total_images"] = processed_count + len(failed_files)

            # Simple final logging - just what we actually know
            if skipped_count > 0:
                self.logger.info(f"Skipped {skipped_count} images that already have annotations")

            total_attempted = processed_count + len(failed_files)
            self.logger.info(
                f"Processed {total_attempted} images this run "
                f"({processed_count} successful, {len(failed_files)} failed)"
            )

            if self.limit and processed_count >= self.limit:
                self.logger.info(f"Reached processing limit of {self.limit} images")

            self.log_final_stats()

            # Add file lists to stats
            self.stats["completed_files"] = completed_files
            self.stats["failed_files"] = failed_files

            # Return simple stats for run manager
            return {
                "processed": self.stats["successful_annotations"],
                "failed": self.stats["failed_images"],
                "skipped": skipped_count,
                "completed_files": completed_files,
                "failed_files": failed_files,
                "scene_classification_failures": self.stats["scene_classification_failures"],
                "object_detection_failures": self.stats["object_detection_failures"],
                "storage_failures": self.stats["storage_failures"],
                "processing_time": (
                    self.stats["end_time"] - self.stats["start_time"] if self.stats["start_time"] else 0
                ),
            }
