import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from storage import create_storage_handler


@dataclass
class DetectionMatch:
    """Represents a match between ground truth and predicted detection."""

    gt_id: str
    pred_id: str
    iou: float
    category_match: bool
    gt_category: str
    pred_category: str


@dataclass
class EvaluationMetrics:
    """Container for evaluation metrics."""

    # Attribute metrics
    attribute_accuracy: Dict[str, float]
    overall_attribute_accuracy: float

    # Object detection metrics
    precision: float
    recall: float
    f1_score: float
    map_50: float  # mAP at IoU=0.5
    map_50_95: float  # mAP at IoU=0.5:0.95

    # Per-class metrics (after mapping)
    per_class_metrics: Dict[str, Dict[str, float]]

    # Original category metrics (before mapping)
    original_category_metrics: Dict[str, Dict[str, Any]]

    # Counts
    total_images: int
    total_gt_objects: int
    total_pred_objects: int
    true_positives: int
    false_positives: int
    false_negatives: int


class AnnotationEvaluator:
    """Evaluates generated annotations against ground truth."""

    def __init__(self, config: dict):
        """Initialize evaluator with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)

        try:
            self.generated_annotations_store = create_storage_handler(config["storage"]["generated_annotations"])
            self.ground_truth_annotations_store = create_storage_handler(config["storage"]["ground_truth_annotations"])
            self.evaluation_output_store = create_storage_handler(config["storage"]["evaluation_output"])

        except Exception as e:
            self.logger.error(f"Failed to initialize components: {str(e)}")
            raise

        # IoU thresholds
        self.iou_threshold = config.get("evaluation", {}).get("iou_threshold", 0.5)
        self.iou_thresholds = np.arange(0.5, 1.0, 0.05)  # For mAP calculation

        # Category mapping for flexible evaluation
        self.category_mapping = self._load_category_mapping()

        # Results storage
        self.results = {
            "per_image_results": [],
            "aggregate_metrics": None,
            "error_analysis": {},
        }

    def _load_category_mapping(self) -> Dict[str, str]:
        """Load category mapping from config or use default."""
        evaluation_config = self.config.get("evaluation", {})

        # Default mapping - maps similar categories to canonical names
        default_mapping = {
            "car": "vehicle",
            "truck": "vehicle",
            "bus": "vehicle",
            "motorcycle": "vehicle",
            "bicycle": "vehicle",
            "traffic light": "traffic_light",
            "traffic sign": "traffic_sign",
            "stop sign": "traffic_sign",
            "person": "person",
            "pedestrian": "person",
        }

        # Allow override from config
        category_mapping = evaluation_config.get("category_mapping", default_mapping)

        self.logger.info(f"Using category mapping: {category_mapping}")
        return category_mapping

    def _normalize_category(self, category: str) -> str:
        """Normalize category using the mapping."""
        return self.category_mapping.get(category.lower(), category.lower())

    def _calculate_iou(self, box1: Dict, box2: Dict) -> float:
        """Calculate Intersection over Union (IoU) between two bounding boxes."""
        # Extract coordinates
        x1_1, y1_1, x2_1, y2_1 = box1["x1"], box1["y1"], box1["x2"], box1["y2"]
        x1_2, y1_2, x2_2, y2_2 = box2["x1"], box2["y1"], box2["x2"], box2["y2"]

        # Calculate intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)

        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0

        intersection = (x2_i - x1_i) * (y2_i - y1_i)

        # Calculate union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y2_2)
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    def _match_detections(
        self, gt_labels: List[Dict], pred_labels: List[Dict]
    ) -> Tuple[List[DetectionMatch], List[str], List[str]]:
        """
        Match ground truth and predicted detections using IoU.

        Returns:
            Tuple of (matches, unmatched_gt_ids, unmatched_pred_ids)
        """
        matches = []
        unmatched_gt = list(range(len(gt_labels)))
        unmatched_pred = list(range(len(pred_labels)))

        # Calculate IoU matrix
        iou_matrix = np.zeros((len(gt_labels), len(pred_labels)))
        for i, gt_label in enumerate(gt_labels):
            for j, pred_label in enumerate(pred_labels):
                if "box2d" in gt_label and "box2d" in pred_label:
                    iou_matrix[i, j] = self._calculate_iou(gt_label["box2d"], pred_label["box2d"])

        # Greedy matching - assign highest IoU pairs first
        while len(unmatched_gt) > 0 and len(unmatched_pred) > 0:
            # Find the highest IoU among unmatched pairs
            max_iou = 0.0
            best_gt_idx = None
            best_pred_idx = None

            for gt_idx in unmatched_gt:
                for pred_idx in unmatched_pred:
                    if iou_matrix[gt_idx, pred_idx] > max_iou:
                        max_iou = iou_matrix[gt_idx, pred_idx]
                        best_gt_idx = gt_idx
                        best_pred_idx = pred_idx

            # If best IoU is above threshold, create a match
            if max_iou >= self.iou_threshold and best_gt_idx is not None:
                gt_label = gt_labels[best_gt_idx]
                pred_label = pred_labels[best_pred_idx]

                gt_category = self._normalize_category(gt_label.get("category", ""))
                pred_category = self._normalize_category(pred_label.get("category", ""))

                match = DetectionMatch(
                    gt_id=gt_label.get("id", str(best_gt_idx)),
                    pred_id=pred_label.get("id", str(best_pred_idx)),
                    iou=max_iou,
                    category_match=(gt_category == pred_category),
                    gt_category=gt_category,
                    pred_category=pred_category,
                )
                matches.append(match)

                unmatched_gt.remove(best_gt_idx)
                unmatched_pred.remove(best_pred_idx)
            else:
                break  # No more valid matches

        # Convert remaining indices to IDs
        unmatched_gt_ids = [gt_labels[i].get("id", str(i)) for i in unmatched_gt]
        unmatched_pred_ids = [pred_labels[i].get("id", str(i)) for i in unmatched_pred]

        return matches, unmatched_gt_ids, unmatched_pred_ids

    def _evaluate_attributes(self, gt_attributes: Dict, pred_attributes: Dict) -> Dict[str, bool]:
        """Evaluate scene attributes."""
        attribute_matches = {}

        for attr_name in gt_attributes.keys():
            gt_value = gt_attributes.get(attr_name, "").lower()
            pred_value = pred_attributes.get(attr_name, "").lower()
            attribute_matches[attr_name] = gt_value == pred_value

        return attribute_matches

    def _calculate_precision_recall_at_iou(
        self,
        all_matches: List[List[DetectionMatch]],
        all_unmatched_gt: List[List[str]],
        all_unmatched_pred: List[List[str]],
        iou_threshold: float,
    ) -> Tuple[float, float]:
        """Calculate precision and recall at specific IoU threshold."""
        tp = 0
        fp = 0
        fn = 0

        for img_idx, matches in enumerate(all_matches):
            # Count true positives (category-correct matches above IoU threshold)
            tp += sum(1 for match in matches if match.iou >= iou_threshold and match.category_match)

            # False positives: predictions with no match or wrong category
            fp += len(all_unmatched_pred[img_idx])
            fp += sum(1 for match in matches if match.iou >= iou_threshold and not match.category_match)

            # False negatives: ground truth with no match
            fn += len(all_unmatched_gt[img_idx])
            fn += sum(1 for match in matches if match.iou < iou_threshold)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        return precision, recall

    def evaluate_single_prediction(self, image_name: str, annotation_name: str) -> Optional[Dict]:
        """Evaluate a single prediction."""
        pred_annotation = self.generated_annotations_store.load_json_file(annotation_name)
        gt_annotation = self.ground_truth_annotations_store.load_json_file(annotation_name)

        try:
            # Evaluate attributes
            gt_attributes = gt_annotation.get("attributes", {})
            pred_attributes = pred_annotation.get("attributes", {})
            attribute_matches = self._evaluate_attributes(gt_attributes, pred_attributes)

            # Evaluate object detection
            gt_labels = gt_annotation.get("labels", [])
            pred_labels = pred_annotation.get("labels", [])

            matches, unmatched_gt, unmatched_pred = self._match_detections(gt_labels, pred_labels)

            # Calculate metrics for this image
            tp = sum(1 for match in matches if match.category_match)
            fp = len(unmatched_pred) + sum(1 for match in matches if not match.category_match)
            fn = len(unmatched_gt)

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

            result = {
                "image_name": image_name,
                "attributes": {
                    "matches": attribute_matches,
                    "accuracy": (
                        sum(attribute_matches.values()) / len(attribute_matches) if attribute_matches else 1.0
                    ),
                },
                "detection": {
                    "matches": matches,
                    "unmatched_gt": unmatched_gt,
                    "unmatched_pred": unmatched_pred,
                    "tp": tp,
                    "fp": fp,
                    "fn": fn,
                    "precision": precision,
                    "recall": recall,
                    "f1": f1,
                    "total_gt": len(gt_labels),
                    "total_pred": len(pred_labels),
                },
            }

            return result

        except Exception as e:
            self.logger.error(f"Error evaluating prediction {image_name}: {e}")
            return None

    def execute(self) -> dict:
        """Evaluate all images and calculate aggregate metrics."""
        start_time = time.time()
        self.logger.info("Starting evaluation of all images...")

        # Get list of generated annotation files (these are the ones we can evaluate)
        pred_files = self.generated_annotations_store.list_files(pattern="*.json")
        self.logger.info(f"Found {len(pred_files)} prediction files to evaluate...")

        per_image_results = []
        all_matches = []
        all_unmatched_gt = []
        all_unmatched_pred = []
        completed_files = []
        failed_files = []
        # Aggregate counters
        total_attribute_matches = defaultdict(int)
        total_attribute_counts = defaultdict(int)
        category_tp = defaultdict(int)
        category_fp = defaultdict(int)
        category_fn = defaultdict(int)

        # Original category tracking (before mapping)
        original_gt_categories = defaultdict(int)
        original_pred_categories = defaultdict(int)
        # Track what each GT category gets predicted as
        gt_to_pred_confusion = defaultdict(lambda: defaultdict(int))
        # Track unmatched GT categories
        unmatched_gt_categories = defaultdict(int)
        # Track unmatched predicted categories
        unmatched_pred_categories = defaultdict(int)

        # Process each image that has both ground truth and predictions
        evaluated_count = 0
        for pred_file in pred_files:
            annotation_name = pred_file
            image_name = self.generated_annotations_store.get_filename(pred_file)

            # Only evaluate if both files exist
            if not self.ground_truth_annotations_store.file_exists(annotation_name):
                self.logger.warning(f"Ground truth file not found for {pred_file}, skipping...")
                failed_files.append(image_name)
                continue

            result = self.evaluate_single_prediction(image_name=image_name, annotation_name=annotation_name)

            if result is None:
                failed_files.append(image_name)
                continue

            per_image_results.append(result)
            completed_files.append(image_name)
            evaluated_count += 1

            gt_data = self.ground_truth_annotations_store.load_json_file(annotation_name)
            pred_data = self.generated_annotations_store.load_json_file(annotation_name)

            # Count original categories (before mapping)
            gt_labels = gt_data.get("labels", [])
            pred_labels = pred_data.get("labels", [])

            for gt_label in gt_labels:
                original_category = gt_label.get("category", "").lower()
                original_gt_categories[original_category] += 1

            for pred_label in pred_labels:
                original_category = pred_label.get("category", "").lower()
                original_pred_categories[original_category] += 1

            # Track category confusion matrix (original categories)
            # For matched detections
            for match in result["detection"]["matches"]:
                # Get original categories from the data
                gt_idx = None
                pred_idx = None

                # Find the original indices for this match
                for i, gt_label in enumerate(gt_labels):
                    if gt_label.get("id", str(i)) == match.gt_id:
                        gt_idx = i
                        break

                for i, pred_label in enumerate(pred_labels):
                    if pred_label.get("id", str(i)) == match.pred_id:
                        pred_idx = i
                        break

                if gt_idx is not None and pred_idx is not None:
                    gt_original = gt_labels[gt_idx].get("category", "").lower()
                    pred_original = pred_labels[pred_idx].get("category", "").lower()

                    gt_to_pred_confusion[gt_original][pred_original] += 1

            # Track unmatched ground truth objects
            for unmatched_id in result["detection"]["unmatched_gt"]:
                for i, gt_label in enumerate(gt_labels):
                    if gt_label.get("id", str(i)) == unmatched_id:
                        gt_original = gt_label.get("category", "").lower()
                        unmatched_gt_categories[gt_original] += 1
                        break

            # Track unmatched predicted objects
            for unmatched_id in result["detection"]["unmatched_pred"]:
                for i, pred_label in enumerate(pred_labels):
                    if pred_label.get("id", str(i)) == unmatched_id:
                        pred_original = pred_label.get("category", "").lower()
                        unmatched_pred_categories[pred_original] += 1
                        break

            # Aggregate attribute results
            for attr_name, match in result["attributes"]["matches"].items():
                total_attribute_counts[attr_name] += 1
                if match:
                    total_attribute_matches[attr_name] += 1

            # Aggregate detection results
            all_matches.append(result["detection"]["matches"])
            all_unmatched_gt.append(result["detection"]["unmatched_gt"])
            all_unmatched_pred.append(result["detection"]["unmatched_pred"])

            # Per-category counting (after mapping)
            for match in result["detection"]["matches"]:
                if match.category_match:
                    category_tp[match.gt_category] += 1
                else:
                    category_fp[match.pred_category] += 1
                    category_fn[match.gt_category] += 1

            # Count unmatched (after mapping)
            for i in result["detection"]["unmatched_gt"]:
                gt_labels_data = gt_data.get("labels", [])
                if i.isdigit() and int(i) < len(gt_labels_data):
                    category = self._normalize_category(gt_labels_data[int(i)].get("category", ""))
                    category_fn[category] += 1

            for i in result["detection"]["unmatched_pred"]:
                pred_labels_data = pred_data.get("labels", [])
                if i.isdigit() and int(i) < len(pred_labels_data):
                    category = self._normalize_category(pred_labels_data[int(i)].get("category", ""))
                    category_fp[category] += 1

        # Calculate original category metrics
        original_category_metrics = {}

        # Get all unique GT categories
        all_gt_categories = set(original_gt_categories.keys())

        for gt_category in all_gt_categories:
            gt_count = original_gt_categories[gt_category]

            # Count how many of this GT category were correctly predicted
            correct_predictions = gt_to_pred_confusion[gt_category].get(gt_category, 0)

            # Count how many total instances of this GT category were matched (correctly or incorrectly)
            total_matched = sum(gt_to_pred_confusion[gt_category].values())

            # Count how many were unmatched
            unmatched = unmatched_gt_categories[gt_category]

            # Build full confusion matrix for this GT category
            confusion_matrix = dict(gt_to_pred_confusion[gt_category])
            if unmatched > 0:
                confusion_matrix["unmatched"] = unmatched

            # Calculate metrics
            recall = correct_predictions / gt_count if gt_count > 0 else 0.0

            # Calculate how many times this category was predicted (total across all GT categories)
            total_pred_as_this_category = original_pred_categories.get(gt_category, 0)
            precision = correct_predictions / total_pred_as_this_category if total_pred_as_this_category > 0 else 0.0

            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

            original_category_metrics[gt_category] = {
                "ground_truth_count": gt_count,
                "correct_predictions": correct_predictions,
                "total_matched": total_matched,
                "unmatched": unmatched,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "predicted_as": confusion_matrix,
                "total_times_predicted": total_pred_as_this_category,
            }

        # Calculate aggregate metrics
        attribute_accuracy = {
            attr: total_attribute_matches[attr] / total_attribute_counts[attr] for attr in total_attribute_counts
        }
        overall_attribute_accuracy = (
            sum(total_attribute_matches.values()) / sum(total_attribute_counts.values())
            if sum(total_attribute_counts.values()) > 0
            else 0.0
        )

        # Calculate detection metrics
        precision_50, recall_50 = self._calculate_precision_recall_at_iou(
            all_matches, all_unmatched_gt, all_unmatched_pred, 0.5
        )
        f1_50 = 2 * precision_50 * recall_50 / (precision_50 + recall_50) if (precision_50 + recall_50) > 0 else 0.0

        # Calculate mAP
        precisions = []
        recalls = []
        for iou_thresh in self.iou_thresholds:
            p, r = self._calculate_precision_recall_at_iou(
                all_matches, all_unmatched_gt, all_unmatched_pred, iou_thresh
            )
            precisions.append(p)
            recalls.append(r)

        map_50_95 = np.mean(precisions)

        # Per-class metrics (after mapping)
        per_class_metrics = {}
        for category in set(list(category_tp.keys()) + list(category_fp.keys()) + list(category_fn.keys())):
            tp = category_tp[category]
            fp = category_fp[category]
            fn = category_fn[category]

            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

            per_class_metrics[category] = {
                "precision": prec,
                "recall": rec,
                "f1": f1,
                "tp": tp,
                "fp": fp,
                "fn": fn,
            }

        # Count totals
        total_gt_objects = sum(result["detection"]["total_gt"] for result in per_image_results)
        total_pred_objects = sum(result["detection"]["total_pred"] for result in per_image_results)
        total_tp = sum(category_tp.values())
        total_fp = sum(category_fp.values())
        total_fn = sum(category_fn.values())

        metrics = EvaluationMetrics(
            attribute_accuracy=attribute_accuracy,
            overall_attribute_accuracy=overall_attribute_accuracy,
            precision=precision_50,
            recall=recall_50,
            f1_score=f1_50,
            map_50=precision_50,  # Simplified - in practice would be calculated properly
            map_50_95=map_50_95,
            per_class_metrics=per_class_metrics,
            original_category_metrics=original_category_metrics,
            total_images=evaluated_count,
            total_gt_objects=total_gt_objects,
            total_pred_objects=total_pred_objects,
            true_positives=total_tp,
            false_positives=total_fp,
            false_negatives=total_fn,
        )

        # Store results
        self.results["per_image_results"] = per_image_results
        self.results["aggregate_metrics"] = metrics

        # Print report (previously called separately)
        self.print_evaluation_report(metrics)

        # Save results (previously called separately)
        self.save_results()

        end_time = time.time()
        processing_time = end_time - start_time

        self.logger.info("Evaluation completed successfully")

        # Return simple stats for run manager
        return {
            "processed": evaluated_count,
            "failed": len(pred_files) - evaluated_count,
            "completed_files": completed_files,
            "failed_files": failed_files,
            "processing_time": processing_time,
            "metrics": metrics,
        }

    def print_evaluation_report(self, metrics: EvaluationMetrics):
        """Print a comprehensive evaluation report."""
        print("\n" + "=" * 80)
        print("ANNOTATION EVALUATION REPORT")
        print("=" * 80)

        print("\n📊 DATASET OVERVIEW:")
        print(f"   Total Images Evaluated: {metrics.total_images}")
        print(f"   Total Ground Truth Objects: {metrics.total_gt_objects}")
        print(f"   Total Predicted Objects: {metrics.total_pred_objects}")

        print("\n🎯 SCENE ATTRIBUTE ACCURACY:")
        print(f"   Overall Accuracy: {metrics.overall_attribute_accuracy:.1%}")
        for attr, acc in metrics.attribute_accuracy.items():
            print(f"   {attr.capitalize()}: {acc:.1%}")

        print(f"\n🔍 OBJECT DETECTION METRICS (IoU ≥ {self.iou_threshold}):")
        print(f"   Precision: {metrics.precision:.1%}")
        print(f"   Recall: {metrics.recall:.1%}")
        print(f"   F1-Score: {metrics.f1_score:.1%}")
        print(f"   mAP@0.5: {metrics.map_50:.1%}")
        print(f"   mAP@0.5:0.95: {metrics.map_50_95:.1%}")

        print("\n📈 DETECTION COUNTS:")
        print(f"   True Positives: {metrics.true_positives}")
        print(f"   False Positives: {metrics.false_positives}")
        print(f"   False Negatives: {metrics.false_negatives}")

        print("\n📋 PER-CLASS PERFORMANCE:")
        for category, class_metrics in metrics.per_class_metrics.items():
            print(f"   {category.upper()}:")
            print(f"     Precision: {class_metrics['precision']:.1%}")
            print(f"     Recall: {class_metrics['recall']:.1%}")
            print(f"     F1-Score: {class_metrics['f1']:.1%}")
            print(f"     TP/FP/FN: {class_metrics['tp']}/{class_metrics['fp']}/{class_metrics['fn']}")

        print("\n" + "=" * 80)

    def save_results(self, output_path: Optional[str] = None):
        """Save evaluation results using the storage handler."""
        # Convert metrics to dict for JSON serialization
        metrics = self.results["aggregate_metrics"]
        if metrics:
            results_dict = {
                "summary": {
                    "total_images": metrics.total_images,
                    "overall_attribute_accuracy": metrics.overall_attribute_accuracy,
                    "precision": metrics.precision,
                    "recall": metrics.recall,
                    "f1_score": metrics.f1_score,
                    "map_50": metrics.map_50,
                    "map_50_95": metrics.map_50_95,
                },
                "attribute_accuracy": metrics.attribute_accuracy,
                "per_class_metrics": metrics.per_class_metrics,
                "original_category_metrics": metrics.original_category_metrics,
                "configuration": {
                    "iou_threshold": self.iou_threshold,
                    "category_mapping": self.category_mapping,
                },
            }

            # Use storage handler to save results
            if output_path:
                # If specific path provided, extract directory and filename
                output_path_obj = Path(output_path)
                filename = output_path_obj.name
                directory = str(output_path_obj.parent)
            else:
                # Use default evaluation results filename
                filename = "evaluation_results.json"
                directory = None  # Use storage handler's default output path

            self.evaluation_output_store.save_json_file(filename, results_dict, directory)
            self.logger.info(f"Evaluation results saved: {filename}")
        else:
            self.logger.warning("No metrics available to save")
