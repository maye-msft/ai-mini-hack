# main.py
import argparse
import sys
from datetime import datetime

import yaml

from core.run_manager import RunManager
from utils.logging_config import setup_logger


def main():
    parser = argparse.ArgumentParser(description="Image processing pipeline.")

    parser.add_argument(
        "action",
        choices=["run", "list", "status"],
        help="Action to perform: run (execute pipeline), list (show all runs), status (show run details)",
    )

    parser.add_argument("--config", type=str, default="config/local.yaml", help="Path to config file")

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set the logging level",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of images to process (for testing)",
    )

    parser.add_argument(
        "--processes",
        type=str,
        default="annotate",
        help="Processes to run (comma-separated: annotate,visualize,evaluate)",
    )

    # Run management arguments
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Specify a run ID. For 'run' action: if provided, resumes existing run; if not, creates new run",
    )

    args = parser.parse_args()

    # Configure logging
    setup_logger(args.log_level)

    try:
        is_resume = True
        if not args.run_id:
            # If run_id is not specified, it is a new run
            is_resume = False
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            args.run_id = f"run_{timestamp}"

        # Load configuration template
        try:
            with open(args.config, "r", encoding="utf-8") as f:
                config_template = yaml.safe_load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load config template: {e}") from e

        # Initialize run manager with config template (it will handle env var resolution internally)
        run_manager = RunManager(config_template, run_id=args.run_id)

        # Handle list action
        if args.action == "list":
            runs = run_manager.list_runs()
            if runs:
                print("\n=== Available Runs ===")
                for run in runs:
                    print(f"  {run['run_id']} - {run['status']} ({run['created_at']})")
            else:
                print("No runs found.")
            return

        # Handle status action
        if args.action == "status":
            if not args.run_id:
                print("Error: 'status' action requires --run-id")
                sys.exit(1)

            run_manager.print_status(args.run_id)
            return

        # Handle run action
        if args.action == "run":
            # Parse processes - comma-separated only
            if isinstance(args.processes, str):
                args.processes = [p.strip() for p in args.processes.split(",") if p.strip()]

            if is_resume:
                run_manager.print_status(args.run_id)

                # Use processes from existing run if not specified (default value)
                if args.processes == ["annotate"]:  # Default value
                    metadata = run_manager._load_or_create_metadata(args.run_id)  # pylint: disable=protected-access
                    args.processes = metadata.get("processes", ["annotate"])

            print(f"Run ID: {args.run_id}")

            # Execute the pipeline - RunManager will handle config resolution internally
            success = run_manager.run_pipeline(args.run_id, args.processes, limit=args.limit)

            # Print final status
            print()
            run_manager.print_status(args.run_id)

            sys.exit(0 if success else 1)

    except FileNotFoundError:
        print(f"Error: Config file '{args.config}' not found")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML in config file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
