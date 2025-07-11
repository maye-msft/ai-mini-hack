# core/storage/__init__.py

from typing import Any, Dict

from .azure_blob_storage import AzureBlobStorageHandler
from .base_storage import BaseStorageHandler
from .local_storage import LocalStorageHandler


def create_storage_handler(config: Dict[str, Any]) -> BaseStorageHandler:
    """
    Factory function to create appropriate storage handler instance based on config type.

    Args:
        config (dict): Configuration containing storage type and parameters

    Returns:
        BaseStorageHandler: Instance of the appropriate storage handler

    Raises:
        ValueError: If storage type is not supported
    """
    storage_type = config.get("type")

    if not storage_type:
        raise ValueError("Storage type must be specified in config")

    if storage_type == "local":
        return LocalStorageHandler(config)
    elif storage_type == "azure_blob":
        return AzureBlobStorageHandler(config)
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}. " f"Available types: ['local', 'azure_blob']")


__all__ = [
    "BaseStorageHandler",
    "LocalStorageHandler",
    "AzureBlobStorageHandler",
    "create_storage_handler",
]
