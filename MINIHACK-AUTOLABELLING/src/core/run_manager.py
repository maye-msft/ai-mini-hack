import logging
import os
from datetime import datetime, timezone
from typing import List

import yaml
from jinja2 import BaseLoader, Environment, StrictUndefined, TemplateError

from core.annotate_image import ImageAnnotator
from core.evaluate_results import AnnotationEvaluator
from core.visualize_results import AnnotationVisualizer
from storage import create_storage_handler


class RunManager:
    """Manages pipeline runs with versioning, progress tracking, and resumability."""

    def __init__(self, config_template: dict, run_id: str = None):
        """
        Initialize the run manager with the config template.

        Args:
            config_template: Configuration template with ${VAR} placeholders (safe to save)
            run_id: Optional run ID for environment variable resolution
        """
        self.config_template = config_template
        self.run_id = run_id
        self.logger = logging.getLogger(__name__)

        # Resolve environment variables to get working config
        self.config = self._resolve_config_variables(config_template, run_id)

        # Create storage handler with resolved config
        try:
            self.storage_handler = create_storage_handler(self.config["storage"]["base_output"])
        except Exception as e:
            self.logger.error("Failed to initialize storage handler: " + str(e))
            raise

    def _resolve_config_variables(self, config_template: dict, run_id: str = None) -> dict:
        """
        Resolve environment variables in the config template using Jinja2.

        Args:
            config_template: Configuration template with ${VAR} placeholders
            run_id: Run ID for ${RUN_ID} substitution

        Returns:
            dict: Configuration with environment variables resolved
        """
        # Convert config back to YAML string
        config_yaml = yaml.dump(config_template)

        # Set up environment variables
        env_vars = os.environ.copy()
        if run_id:
            env_vars["RUN_ID"] = run_id

        try:
            # Create Jinja2 environment with variable syntax matching envsubst
            jinja_env = Environment(
                loader=BaseLoader(),
                variable_start_string="${",
                variable_end_string="}",
                undefined=StrictUndefined,
            )

            # Create template from the YAML string
            template = jinja_env.from_string(config_yaml)

            # Render the template with environment variables
            resolved_yaml = template.render(**env_vars)

            # Parse the resolved YAML
            return yaml.safe_load(resolved_yaml)

        except TemplateError as e:
            raise RuntimeError("Failed to substitute template variables: " + str(e))
        except Exception as e:
            raise RuntimeError("Failed to resolve config variables: " + str(e))

    def _generate_run_id(self) -> str:
        """Generate a new run ID with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"run_{timestamp}"

    def _load_or_create_metadata(self, run_id: str) -> dict:
        """Load existing metadata or create new metadata structure."""
        try:
            # Use storage handler's load_json_file method directly
            metadata = self.storage_handler.load_json_file("run_metadata.json", run_id)
            if metadata:
                return metadata
        except Exception as e:
            self.logger.warning("Could not load metadata: " + str(e) + ", creating new")

        # Create new metadata structure
        return {
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "config": {},
            "processes": [],
            "status": "initialized",
            "progress": {},
            "error_log": [],
            "file_tracking": {},
        }

    def _save_metadata(self, run_id: str, metadata: dict):
        """Save metadata to storage."""
        metadata["updated_at"] = datetime.now(timezone.utc).isoformat()

        try:
            # Use storage handler's save_json_file method directly
            self.storage_handler.save_json_file("run_metadata.json", metadata, run_id)
        except Exception as e:
            self.logger.error("Failed to save metadata: " + str(e))
            raise

    def list_runs(self) -> List[dict]:
        """List all available runs using the configured storage."""
        runs = []

        try:
            # List all run directories using the storage abstraction
            run_directories = self.storage_handler.list_directories()

            for run_id in run_directories:
                # Try to load metadata for each run
                metadata = self.storage_handler.load_json_file("run_metadata.json", run_id)

                if metadata:
                    runs.append(
                        {
                            "run_id": metadata.get("run_id", run_id),
                            "created_at": metadata.get("created_at", "unknown"),
                            "status": metadata.get("status", "unknown"),
                            "processes": metadata.get("processes", []),
                        }
                    )

        except Exception as e:
            # Log error but return empty list
            self.logger.error("Failed to list runs: " + str(e))

        return sorted(runs, key=lambda x: x["created_at"], reverse=True)

    def print_status(self, run_id: str):
        """Print a formatted status report for the specified run."""
        metadata = self._load_or_create_metadata(run_id)

        status = {
            "run_id": run_id,
            "status": metadata["status"],
            "created_at": metadata["created_at"],
            "updated_at": metadata["updated_at"],
            "processes": {},
        }

        for process_name, progress in metadata["progress"].items():
            status["processes"][process_name] = {
                "status": progress["status"],
                "total": progress["total_files"],
                "completed": progress["processed"],
                "failed": progress["failed"],
                "percentage": (progress["processed"] / max(progress["total_files"], 1)) * 100,
            }

        print("\n=== Run Status: " + status["run_id"] + " ===")
        print("Overall Status: " + status["status"])
        print("Created: " + status["created_at"])
        print("Updated: " + status["updated_at"])

        print("\nProcess Details:")
        for process_name, process_status in status["processes"].items():
            print("  " + process_name + ":")
            print("    Status: " + process_status["status"])
            print(
                "    Progress: "
                + str(process_status["completed"])
                + "/"
                + str(process_status["total"])
                + " "
                + "("
                + f"{process_status['percentage']:.1f}"
                + "%)"
            )
            if process_status["failed"] > 0:
                print("    Failed: " + str(process_status["failed"]))

        if metadata["error_log"]:
            print("\nRecent Errors:")
            for error in metadata["error_log"][-3:]:  # Show last 3 errors
                print("  " + error["timestamp"] + ": " + error.get("process", "unknown") + " - " + error["error"])

    def run_pipeline(self, run_id: str, processes: List[str], limit: int = None):
        """Execute a complete pipeline run with the given configuration."""
        self.logger.info("Starting pipeline run: " + run_id)

        # Update run_id and re-resolve config if needed
        if self.run_id != run_id:
            self.run_id = run_id
            self.config = self._resolve_config_variables(self.config_template, run_id)

        # Store limit for use by process methods
        self.limit = limit

        metadata = self._load_or_create_metadata(run_id)

        # Initialize run if it's new
        if metadata["status"] == "initialized":
            metadata = self._initialize_run(run_id, metadata, processes)
            self._save_metadata(run_id, metadata)

        # Fixed pipeline order: annotate → visualize → evaluate
        pipeline_steps = [
            ("annotate", self._run_annotate_process),
            ("visualize", self._run_visualize_process),
            ("evaluate", self._run_evaluate_process),
        ]

        # Execute pipeline steps in order, but only if they're in the processes list
        for step_name, step_function in pipeline_steps:
            if step_name in processes:
                # Update process status to running
                metadata["progress"][step_name]["status"] = "running"
                metadata["progress"][step_name]["start_time"] = datetime.now(timezone.utc).isoformat()
                self._save_metadata(run_id, metadata)

                success = step_function(run_id, metadata)

                if success:
                    # Update process status to completed
                    metadata["progress"][step_name]["status"] = "completed"
                    metadata["progress"][step_name]["end_time"] = datetime.now(timezone.utc).isoformat()
                    self._save_metadata(run_id, metadata)
                    self.logger.info("Process '" + step_name + "' completed successfully")
                else:
                    # Update process status to failed
                    metadata["progress"][step_name]["status"] = "failed"
                    metadata["progress"][step_name]["end_time"] = datetime.now(timezone.utc).isoformat()
                    metadata["status"] = "failed"
                    self._save_metadata(run_id, metadata)
                    return False
            else:
                self.logger.info("Skipping step: " + step_name)

        metadata["status"] = "completed"
        self._save_metadata(run_id, metadata)
        self.logger.info("Pipeline run " + run_id + " completed successfully")
        return True

    def _initialize_run(self, run_id: str, metadata: dict, processes: List[str]):
        """Initialize a new run with configuration and processes."""
        # Always initialize all steps, even if some will be skipped
        all_processes = ["annotate", "visualize", "evaluate"]

        metadata.update(
            {
                "config": self.config_template,  # Save the safe template, not resolved config
                "processes": processes,
                "status": "in_progress",
                "progress": {
                    process: {
                        "status": "pending" if process in processes else "skipped",
                        "total_files": 0,
                        "processed": 0,
                        "failed": 0,
                        "completed_files": [],
                        "failed_files": [],
                        "start_time": None,
                        "end_time": None,
                    }
                    for process in all_processes
                },
            }
        )

        self.logger.info("Initialized pipeline run with steps: " + ", ".join(processes))
        return metadata

    def _run_annotate_process(self, run_id: str, metadata: dict) -> bool:
        """Execute the annotation process."""
        self.logger.info("Starting image annotation process...")

        try:
            annotator = ImageAnnotator(self.config["annotate"], limit=self.limit)

            # Just call execute and get comprehensive stats
            stats = annotator.execute()

            # Merge results with existing metadata to preserve previous runs
            progress = metadata["progress"]["annotate"]

            # Add to totals (don't overwrite)
            progress["total_files"] = (
                progress.get("total_files", 0) + stats.get("processed", 0) + stats.get("failed", 0)
            )
            progress["processed"] = progress.get("processed", 0) + stats.get("processed", 0)
            progress["failed"] = progress.get("failed", 0) + stats.get("failed", 0)

            # Merge file lists (don't overwrite)
            existing_completed = progress.get("completed_files", [])
            existing_failed = progress.get("failed_files", [])

            progress["completed_files"] = existing_completed + stats.get("completed_files", [])
            progress["failed_files"] = existing_failed + stats.get("failed_files", [])

            self.logger.info("Image annotation process completed successfully")
            return True

        except Exception as e:
            error_msg = "Image annotation process failed: " + str(e)
            self.logger.error(error_msg)
            return False

    def _run_visualize_process(self, run_id: str, metadata: dict) -> bool:
        """Execute the visualization process."""
        self.logger.info("Starting annotation visualization process...")

        try:
            visualizer = AnnotationVisualizer(self.config["visualize"])

            # Just call execute and get comprehensive stats
            stats = visualizer.execute()

            # Merge results with existing metadata to preserve previous runs
            progress = metadata["progress"]["visualize"]

            # Add to totals (don't overwrite)
            progress["processed"] = progress.get("processed", 0) + stats.get("processed", 0)
            progress["failed"] = progress.get("failed", 0) + stats.get("failed", 0)

            # Merge file lists (don't overwrite)
            existing_completed = progress.get("completed_files", [])
            existing_failed = progress.get("failed_files", [])

            progress["completed_files"] = existing_completed + stats.get("completed_files", [])
            progress["failed_files"] = existing_failed + stats.get("failed_files", [])

            self.logger.info("Annotation visualization process completed successfully")
            return True

        except Exception as e:
            error_msg = "Annotation visualization process failed: " + str(e)
            self.logger.error(error_msg)
            return False

    def _run_evaluate_process(self, run_id: str, metadata: dict) -> bool:
        """Execute the evaluation process."""
        self.logger.info("Starting annotation evaluation process...")

        try:
            evaluator = AnnotationEvaluator(self.config["evaluate"])

            # Just call execute and get comprehensive stats (includes print report and save results)
            stats = evaluator.execute()

            # For evaluation, we always want the latest complete results, not merged
            # because evaluation should reflect the current state of all annotations
            progress = metadata["progress"]["evaluate"]

            progress["processed"] = stats.get("processed", 0)
            progress["failed"] = stats.get("failed", 0)
            progress["completed_files"] = stats.get("completed_files", [])
            progress["failed_files"] = stats.get("failed_files", [])

            self.logger.info("Annotation evaluation process completed successfully")
            return True

        except Exception as e:
            error_msg = "Annotation evaluation process failed: " + str(e)
            self.logger.error(error_msg)
            return False

    def print_process_info(self):
        """Print detailed process information."""
        print("\nProcess Details:")
        print("   PID: " + str(self.process.pid))
        print("   Status: " + self.get_status())
        print("   Runtime: " + f"{self.get_runtime():.1f}" + "s")
        print("   Memory Usage: " + f"{self.get_memory_usage():.1f}" + " MB")

        # Show recent output
        recent_output = self.get_recent_output(lines=5)
        if recent_output:
            print("\nRecent Output:")
            for line in recent_output:
                print("   " + line)

        # Show recent errors
        recent_errors = self.get_recent_errors(lines=3)
        if recent_errors:
            print("\nRecent Errors:")
            for line in recent_errors:
                print("   " + line)
