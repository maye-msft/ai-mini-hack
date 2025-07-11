# core/storage/base_storage.py

import json
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Union


class BaseStorageHandler(ABC):
    """Abstract base class for storage handlers."""

    def __init__(self, config: dict):
        """
        Initialize the storage handler with configuration.

        Args:
            config (dict): Storage configuration
        """
        self.config = config

    @abstractmethod
    def file_exists(self, filename: str, path: Optional[str] = None) -> bool:
        """
        Check if a file exists in storage.

        Args:
            filename (str): Name of the file to check
            path (str, optional): Directory/prefix to check in

        Returns:
            bool: True if file exists, False otherwise
        """
        pass

    @abstractmethod
    def list_directories(self, path: Optional[str] = None) -> List[str]:
        """
        List directories/prefixes in storage.

        Args:
            path (str, optional): Directory/prefix to list subdirectories from

        Returns:
            List[str]: List of directory names
        """
        pass

    def create_directory(self, path: str) -> None:
        """
        Create directory if it doesn't exist.

        Args:
            path: Directory path to create
        """
        pass

    @abstractmethod
    def list_files(self, path: Optional[str] = None, pattern: str = "*") -> List[str]:
        """
        List files in storage.

        Args:
            path (str, optional): Directory/prefix to list
            pattern (str, optional): File pattern to match

        Returns:
            List[str]: List of filenames
        """
        pass

    @abstractmethod
    def load_file(self, filename: str, input_path: Optional[str] = None) -> Optional[Union[str, bytes]]:
        """
        Load a file from storage.

        Args:
            filename (str): Name of the file to load
            input_path (str, optional): Directory/prefix path

        Returns:
            Optional[Union[str, bytes]]: File content or None if not found
        """
        pass

    @abstractmethod
    def save_file(self, filename: str, content: Union[str, bytes], output_path: Optional[str] = None) -> None:
        """
        Save a file to storage.

        Args:
            filename (str): Name of the file to save
            content (Union[str, bytes]): File content
            output_path (str, optional): Output directory/prefix. If None, uses default
        """
        pass

    @abstractmethod
    def get_filename(self, path: str) -> str:
        """
        Args:
            path (str): The path to the file
        """
        pass

    def load_json_file(self, filename: str, input_path: Optional[str] = None) -> Any:
        """
        Load and parse a JSON file from storage.

        Args:
            filename (str): Name of the JSON file to load
            input_path (str, optional): Input directory/prefix

        Returns:
            Optional[dict]: Parsed JSON data or None if not found/invalid
        """
        content = self.load_file(filename, input_path)
        if content:
            try:
                if isinstance(content, bytes):
                    content = content.decode("utf-8")
                return json.loads(content)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return None
        return None

    def save_json_file(self, filename: str, data: dict, output_path: Optional[str] = None) -> None:
        """
        Save data as a JSON file to storage.

        Args:
            filename (str): Name of the JSON file to save
            data (dict): Data to save as JSON
            output_path (str, optional): Output directory/prefix
        """
        json_content = json.dumps(data, indent=2)
        self.save_file(filename, json_content, output_path)
