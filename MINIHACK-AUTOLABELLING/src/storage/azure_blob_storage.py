# core/storage/azure_storage.py

import logging
from typing import List, Optional, Union

from azure.storage.blob import BlobServiceClient

from .base_storage import BaseStorageHandler


class AzureBlobStorageHandler(BaseStorageHandler):
    """Storage handler for Azure Blob Storage."""

    def __init__(self, config: dict):
        super().__init__(config)

        # Initialize logger
        self.logger = logging.getLogger(__name__)

        self.base_path = self.config.get("path", "")
        self._setup_clients()

    def _setup_clients(self):
        """Setup Azure Blob Storage clients with account key authentication."""
        # Get storage account endpoint and container name
        account_endpoint = self.config.get("account_endpoint")
        container_name = self.config.get("container_name")
        account_key = self.config.get("account_key")

        if not account_endpoint:
            raise ValueError("Storage account endpoint is required in config")
        if not container_name:
            raise ValueError("Container name is required in config")
        if not account_key:
            raise ValueError("Account key is required in config")

        self.account_url = account_endpoint
        self.container_name = container_name

        self.blob_service_client = BlobServiceClient(account_url=self.account_url, credential=account_key)

        self.container_client = self.blob_service_client.get_container_client(self.container_name)

        self.logger.debug(f"Azure Blob Storage client initialized for container: " f"{container_name}")

    def _get_blob_name(self, filename: str = None, path: str = None) -> str:
        """
        Helper to construct blob name from base path and optional
        path/filename.
        """
        # Start with base path
        parts = []
        if self.base_path:
            parts.append(self.base_path.strip("/"))

        # Add optional path
        if path:
            parts.append(path.strip("/"))

        # Add filename if provided
        if filename:
            parts.append(filename)

        # Join with "/" and ensure no leading slash
        blob_name = "/".join(parts)
        return blob_name.lstrip("/")

    def save_file(self, filename: str, content: Union[str, bytes], output_path: str = None):
        """Save a file to Azure Blob Storage."""
        blob_name = self._get_blob_name(filename, output_path)

        blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)

        if isinstance(content, str):
            content = content.encode("utf-8")

        try:
            blob_client.upload_blob(content, overwrite=True)
            self.logger.debug(f"Saved file to blob: {blob_name}")
        except Exception as e:
            self.logger.error(f"Failed to save file to blob {blob_name}: {e}")
            raise

    def load_file(self, filename: str, input_path: str = None) -> Optional[Union[str, bytes]]:
        """Load a file from Azure Blob Storage."""
        blob_name = self._get_blob_name(filename, input_path)

        try:
            blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)
            blob_data = blob_client.download_blob().readall()

            self.logger.debug(f"Loaded file from blob: {blob_name}")

            # Try to decode as UTF-8, return as bytes if it fails
            try:
                return blob_data.decode("utf-8")
            except UnicodeDecodeError:
                return blob_data
        except Exception as e:
            self.logger.warning(f"Failed to load file from blob {blob_name}: {e}")
            return None

    def file_exists(self, filename: str, path: str = None) -> bool:
        """Check if a file exists in Azure Blob Storage."""
        blob_name = self._get_blob_name(filename, path)

        try:
            blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)
            exists = blob_client.exists()
            self.logger.debug(f"File exists check for {blob_name}: {exists}")
            return exists
        except Exception as e:
            self.logger.warning(f"Error checking if file exists {blob_name}: {e}")
            return False

    def list_files(self, path: str = None, pattern: str = "*") -> List[str]:
        """List files in Azure Blob Storage."""
        import fnmatch

        try:
            # Get the prefix for the search
            prefix = self._get_blob_name(path=path)
            if prefix:
                prefix = prefix + "/"

            blob_names = []
            for blob in self.container_client.list_blobs(name_starts_with=prefix):
                # Extract relative path from the base path and optional path
                relative_path = blob.name
                if prefix and relative_path.startswith(prefix):
                    relative_path = relative_path[len(prefix) :]
                elif self.base_path:
                    # Remove base path if no additional path was specified
                    base_prefix = self.base_path.strip("/") + "/"
                    if relative_path.startswith(base_prefix):
                        relative_path = relative_path[len(base_prefix) :]

                # Skip if this is a directory-like blob or empty
                if relative_path.endswith("/") or not relative_path:
                    continue

                # Only include files in immediate directory
                if "/" not in relative_path:
                    # Apply pattern matching
                    if fnmatch.fnmatch(relative_path, pattern):
                        blob_names.append(relative_path)

            self.logger.debug(f"Listed {len(blob_names)} files from path: {path}")
            return sorted(blob_names)
        except Exception as e:
            self.logger.error(f"Failed to list files from path {path}: {e}")
            return []

    def list_directories(self, path: str = None) -> List[str]:
        """List directories/prefixes in Azure Blob Storage."""
        try:
            # Get the prefix for the search
            prefix = self._get_blob_name(path=path)
            if prefix:
                prefix = prefix + "/"

            directories = set()
            for blob in self.container_client.list_blobs(name_starts_with=prefix):
                # Extract relative path from the base path and optional path
                relative_path = blob.name
                if prefix and relative_path.startswith(prefix):
                    relative_path = relative_path[len(prefix) :]
                elif self.base_path:
                    # Remove base path if no additional path was specified
                    base_prefix = self.base_path.strip("/") + "/"
                    if relative_path.startswith(base_prefix):
                        relative_path = relative_path[len(base_prefix) :]

                # Extract the first directory component
                if "/" in relative_path:
                    first_dir = relative_path.split("/")[0]
                    if first_dir:  # Ensure it's not empty
                        directories.add(first_dir)

            self.logger.debug(f"Listed {len(directories)} directories from path: {path}")
            return sorted(list(directories))
        except Exception as e:
            self.logger.error(f"Failed to list directories from path {path}: {e}")
            return []

    def create_directory(self, path):
        """
        Create directory in Azure Blob Storage (no-op since blobs create
        paths implicitly).
        """
        # In blob storage, directories are created implicitly when
        # files are uploaded
        pass

    def get_filename(self, path: str) -> str:
        """Extract filename from a blob path."""
        # For Azure blob storage, always use forward slash as separator
        # Get the last component after splitting by "/"
        if "/" in path:
            return path.split("/")[-1]
        else:
            return path
