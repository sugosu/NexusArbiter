from storage.json_storage import JsonStorage
from app_logging import AppLogger
from typing import List, Dict, Any
import os


class CategoryRepository:
    """Repository for category entities persisted as JSON in a fixed file 'categories.json'.

    Responsibilities:
    - Compute the file path by joining the provided data_dir with 'categories.json'.
    - Delegate reads/writes to the injected JsonStorage instance.
    - Use the injected AppLogger for logging; do not use stdlib logging directly.
    """

    _storage: JsonStorage
    _logger: AppLogger

    def __init__(self, storage: JsonStorage, logger: AppLogger) -> None:
        """Initialize repository with storage and logger dependencies.

        Do not perform I/O in the constructor.
        """
        self._storage = storage
        self._logger = logger

    def load_all(self, data_dir: str) -> List[Dict[str, Any]]:
        """Load all category records from the categories.json file.

        Returns an empty list when the file is missing or storage returns None (bootstrap-safe read).
        """
        file_path = os.path.join(data_dir, "categories.json")
        try:
            raw = self._storage.read(file_path)
        except Exception as exc:  # propagate storage errors after logging
            self._logger.error("Failed to read categories file", {"file_path": file_path, "error": str(exc)})
            raise

        if raw is None:
            # Missing file -> bootstrap-safe empty collection
            self._logger.debug("No categories file found; returning empty list", {"file_path": file_path})
            return []

        if not isinstance(raw, list):
            # Conservatively treat unexpected shapes as empty; log for operators to investigate
            self._logger.debug("Categories data is not a list; returning empty list", {"file_path": file_path, "type": type(raw).__name__})
            return []

        self._logger.debug("Loaded categories", {"count": len(raw), "file_path": file_path})
        # No domain-model conversion is performed; return JSON-serializable dicts
        return raw

    def save_all(self, data_dir: str, categories: List[Dict[str, Any]]) -> None:
        """Persist the provided list of category records atomically via JsonStorage.

        Ensures each record is a dict and includes the required 'id' field per the persistence schema before delegating to storage.
        """
        file_path = os.path.join(data_dir, "categories.json")

        if not isinstance(categories, list):
            raise TypeError("categories must be a list of dicts")

        serializable_data: List[Dict[str, Any]] = []
        for idx, rec in enumerate(categories):
            if not isinstance(rec, dict):
                self._logger.error("Category record is not a dict and cannot be serialized", {"index": idx, "file_path": file_path})
                raise TypeError("Each category record must be a dict")
            if "id" not in rec:
                self._logger.error("Category record missing required 'id' field", {"index": idx, "record": rec, "file_path": file_path})
                raise ValueError("Each category record must contain an 'id' field")
            serializable_data.append(rec)

        try:
            self._storage.write(file_path, serializable_data)
        except Exception as exc:
            self._logger.error("Failed to write categories file", {"file_path": file_path, "error": str(exc)})
            raise

        self._logger.debug("Saved categories", {"count": len(serializable_data), "file_path": file_path})
