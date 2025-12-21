from typing import List, Dict, Any
import os

from storage.json_storage import JsonStorage
from app_logging import AppLogger


class TransactionRepository:
    """Repository responsible for loading and saving transactions.json under a provided data_dir.

    Responsibilities follow the manifest: compute the concrete file path by joining data_dir with
    'transactions.json', delegate reads/writes to the injected JsonStorage, and use the injected
    AppLogger for logging. No file I/O is performed directly by this class.
    """

    def __init__(self, storage: JsonStorage, logger: AppLogger) -> None:
        """Initialize the repository with its dependencies.

        Do not perform I/O in the constructor.
        """
        self._storage = storage
        self._logger = logger

    def load_all(self, data_dir: str) -> List[Dict[str, Any]]:
        """Load all transaction records from the data directory.

        Returns a list of dicts. If the storage indicates no file (None) or data is missing/malformed,
        an empty list is returned (bootstrap-safe read). Access is logged via the injected logger.
        """
        file_path = os.path.join(data_dir, "transactions.json")
        try:
            raw = self._storage.read(file_path)
        except Exception as e:
            # Log and propagate the error; callers may handle exceptions as needed.
            self._logger.error("Failed to read transactions file", {"file_path": file_path, "error": str(e)})
            raise

        if raw is None:
            self._logger.debug("No transactions file found; returning empty list", {"file_path": file_path})
            return []

        if not isinstance(raw, list):
            # Unexpected shape from storage; log and return empty list to remain bootstrap-safe.
            self._logger.error("Unexpected data shape for transactions; expected list", {"file_path": file_path, "type": type(raw).__name__})
            return []

        records: List[Dict[str, Any]] = []
        for idx, item in enumerate(raw):
            if isinstance(item, dict):
                records.append(item)
            else:
                # Convert non-dict items conservatively into a dict wrapper so callers receive a consistent type.
                # This is a minimal deterministic conversion to satisfy the manifest's expectation of dicts.
                self._logger.debug("Converting non-dict transaction item to dict wrapper", {"index": idx, "file_path": file_path})
                records.append({"_raw": item})

        self._logger.debug("Loaded transactions", {"file_path": file_path, "count": len(records)})
        return records

    def save_all(self, data_dir: str, transactions: List[Dict[str, Any]]) -> None:
        """Persist the provided list of transaction dicts to transactions.json under data_dir.

        Ensures each record includes the required 'id' field before delegating to storage.write.
        Logs success or errors via the injected logger. The storage adapter is responsible for atomic
        persistence semantics.
        """
        file_path = os.path.join(data_dir, "transactions.json")

        # Validate records satisfy required schema (each must have an 'id')
        for idx, rec in enumerate(transactions):
            if not isinstance(rec, dict):
                msg = "Transaction record is not a dict"
                self._logger.error(msg, {"index": idx, "file_path": file_path, "record_type": type(rec).__name__})
                raise ValueError(f"Transaction at index {idx} is not a dict")
            if "id" not in rec:
                msg = "Transaction record missing required 'id' field"
                self._logger.error(msg, {"index": idx, "file_path": file_path, "record": rec})
                raise ValueError(f"Transaction at index {idx} missing required 'id' field")

        serializable_data = transactions  # Assume callers supply JSON-serializable primitives per manifest

        try:
            self._storage.write(file_path, serializable_data)
            self._logger.debug("Saved transactions", {"file_path": file_path, "count": len(transactions)})
        except Exception as e:
            # Log and re-raise so callers can react; storage.write is expected to raise on failure.
            self._logger.error("Failed to write transactions file", {"file_path": file_path, "error": str(e)})
            raise
