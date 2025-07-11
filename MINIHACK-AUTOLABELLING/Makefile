.PHONY: help lint format check test clean install-dev

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install-dev:  ## Install development dependencies
	pip install -r .devcontainer/requirements.txt
	pre-commit install

format:  ## Format code with black and isort
	black src/
	isort src/

lint:  ## Run all linters
	flake8 src/
	pylint src/

check:  ## Run format check without modifying files
	black --check src/
	isort --check-only src/
	flake8 src/

pre-commit:  ## Run pre-commit hooks on all files
	pre-commit run --all-files

test:  ## Run tests (placeholder - add your test command here)
	@echo "Add your test command here"

clean:  ## Clean up cache files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

fix:  ## Auto-fix linting issues where possible
	autopep8 --in-place --recursive src/
	black src/
	isort src/
