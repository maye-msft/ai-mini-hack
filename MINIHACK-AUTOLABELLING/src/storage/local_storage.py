# core/storage/local_storage.py

import logging
from pathlib import Path
from typing import List, Optional, Union

from .base_storage import BaseStorageHandler


class LocalStorageHandler(BaseStorageHandler):
    """Local file system storage handler."""

    def __init__(self, config: dict):
        super().__init__(config)

        # Initialize logger
        self.logger = logging.getLogger(__name__)

        self.base_path = Path(self.config.get("path", "."))

        if not self.base_path.exists():
            self.create_directory("")

        self.logger.debug(f"Local storage initialized with base path: {self.base_path}")

    def _get_full_path(self, filename: Optional[str] = None, path: Optional[str] = None) -> Path:
        """Helper to get full path for file operations."""
        if path:
            full_path = self.base_path / path
        else:
            full_path = self.base_path

        if filename:
            full_path = full_path / filename

        return full_path

    def file_exists(self, filename: str, path: Optional[str] = None) -> bool:
        """Check if a file exists in local storage."""
        exists = self._get_full_path(filename, path).exists()
        self.logger.debug(f"File exists check for {filename}: {exists}")
        return exists

    def list_directories(self, path: Optional[str] = None) -> List[str]:
        """List directories in local storage."""
        dir_path = self._get_full_path(path=path)
        if not dir_path.exists():
            self.logger.debug(f"Directory does not exist: {dir_path}")
            return []

        directories = []
        for item in dir_path.iterdir():
            if item.is_dir():
                # Get path relative to base_path
                relative_path = item.relative_to(self.base_path)
                directories.append(str(relative_path))

        self.logger.debug(f"Listed {len(directories)} directories from path: {path}")
        return sorted(directories)

    def create_directory(self, path: str) -> None:
        """Create directory if it doesn't exist."""
        full_path = self._get_full_path(path)
        full_path.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"Created directory: {full_path}")

    def list_files(self, path: Optional[str] = None, pattern: str = "*") -> List[str]:
        """List files in local storage directory."""
        dir_path = self._get_full_path(path=path)
        if not dir_path.exists():
            self.logger.debug(f"Directory does not exist: {dir_path}")
            return []

        files = []
        for f in dir_path.glob(pattern):
            if f.is_file():
                # Get path relative to base_path
                relative_path = f.relative_to(self.base_path)
                files.append(str(relative_path))

        self.logger.debug(f"Listed {len(files)} files from path: {path}")
        return sorted(files)

    def load_file(self, filename: str, input_path: Optional[str] = None) -> Optional[Union[str, bytes]]:
        """Load a file from local storage."""
        file_path = self._get_full_path(filename, input_path)
        if not file_path.exists():
            self.logger.warning(f"File not found: {file_path}")
            return None

        try:
            content = file_path.read_text(encoding="utf-8")
            self.logger.debug(f"Loaded text file: {file_path}")
            return content
        except UnicodeDecodeError:
            content = file_path.read_bytes()
            self.logger.debug(f"Loaded binary file: {file_path}")
            return content

    def save_file(self, filename: str, content: Union[str, bytes], output_path: Optional[str] = None) -> None:
        """Save a file to local storage."""
        output_dir = self._get_full_path(path=output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        file_path = output_dir / filename

        try:
            if isinstance(content, str):
                file_path.write_text(content, encoding="utf-8")
            else:
                file_path.write_bytes(content)

            self.logger.debug(f"Saved file to {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save file to {file_path}: {e}")
            raise

    def get_filename(self, path: str) -> str:
        """Extract filename from a file path."""
        full_path = self._get_full_path(path)
        return Path(full_path).name
