from typing import List, Dict, Any, Optional

from repository.transaction_repository import TransactionRepository
from app_logging import AppLogger


class TransactionService:
    """Domain service responsible for transaction CRUD semantics.

    Responsibilities (per manifest):
    - Enforce caller-provided 'id' identity policy and uniqueness on create.
    - Delegate all persistence to the injected TransactionRepository.
    - Use the injected AppLogger for all logging.
    """

    def __init__(self, repository: TransactionRepository, logger: AppLogger) -> None:
        """Construct TransactionService with repository and logger dependencies."""
        self._repository = repository
        self._logger = logger

    def create(self, transaction_params: Dict[str, Any], data_dir: str) -> dict:
        """Create a new transaction.

        Validates presence of 'id' per identity policy, enforces uniqueness, persists via repository,
        and returns the created record or a structured error dict on validation/conflict.
        """
        # Validate required identity field
        if not isinstance(transaction_params, dict) or "id" not in transaction_params:
            self._logger.error("Transaction create validation failed: missing id", transaction_params)
            return {"error": "validation", "message": "Missing required field: id"}

        record_id = transaction_params["id"]

        # Load existing transactions
        try:
            existing = self._repository.load_all(data_dir) or []
        except Exception as exc:  # propagate repository exceptions after logging
            self._logger.error("Failed to load transactions for create", {"exception": exc})
            raise

        # Check uniqueness
        for rec in existing:
            if rec.get("id") == record_id:
                self._logger.error("Transaction id conflict on create", {"id": record_id})
                return {"error": "conflict", "message": f"Transaction with id {record_id} already exists"}

        # Append and persist
        new_record = dict(transaction_params)  # shallow copy to avoid external mutation
        updated = list(existing) + [new_record]
        try:
            self._repository.save_all(data_dir, updated)
        except Exception as exc:
            self._logger.error("Failed to save transactions on create", {"exception": exc})
            raise

        self._logger.info("Transaction created", {"id": record_id})
        return new_record

    def list(self, query_params: Dict[str, Any], data_dir: str) -> List[Dict[str, Any]]:
        """Return a list of transactions, optionally filtered in-memory by simple equality matching.

        Conservative in-memory filtering: for each key in query_params, keep records where
        record.get(key) == query_params[key]. If query_params is falsy, return all records.
        """
        try:
            records = self._repository.load_all(data_dir) or []
        except Exception as exc:
            self._logger.error("Failed to load transactions for list", {"exception": exc})
            raise

        if query_params:
            def matches(rec: Dict[str, Any]) -> bool:
                for k, v in query_params.items():
                    # Skip None filters explicitly (caller may pass None meaning no-op)
                    if v is None:
                        continue
                    if rec.get(k) != v:
                        return False
                return True

            filtered = [r for r in records if matches(r)]
        else:
            filtered = list(records)

        self._logger.debug("Listed transactions", {"count": len(filtered)})
        return filtered

    def get(self, record_id: str, data_dir: str) -> Optional[Dict[str, Any]]:
        """Return the transaction dict with matching id or None if not found."""
        try:
            records = self._repository.load_all(data_dir) or []
        except Exception as exc:
            self._logger.error("Failed to load transactions for get", {"exception": exc})
            raise

        for rec in records:
            if rec.get("id") == record_id:
                return rec

        self._logger.info("Transaction not found", {"id": record_id})
        return None

    def update(self, record_id: str, update_fields: Dict[str, Any], data_dir: str) -> dict:
        """Update fields of an existing transaction and persist the collection.

        Does not allow changing the 'id' field.
        Returns the updated record on success or a structured error dict if not found.
        """
        try:
            records = self._repository.load_all(data_dir) or []
        except Exception as exc:
            self._logger.error("Failed to load transactions for update", {"exception": exc})
            raise

        found = False
        updated_record: Optional[Dict[str, Any]] = None
        updated_list: List[Dict[str, Any]] = []

        for rec in records:
            if rec.get("id") == record_id:
                found = True
                # Apply updates conservatively; do not change id
                new_rec = dict(rec)
                for k, v in (update_fields or {}).items():
                    if k == "id":
                        continue
                    new_rec[k] = v
                updated_record = new_rec
                updated_list.append(new_rec)
            else:
                updated_list.append(rec)

        if not found:
            self._logger.info("Transaction update attempted but not found", {"id": record_id})
            return {"error": "not_found", "message": f"Transaction with id {record_id} not found"}

        try:
            self._repository.save_all(data_dir, updated_list)
        except Exception as exc:
            self._logger.error("Failed to save transactions on update", {"exception": exc})
            raise

        self._logger.info("Transaction updated", {"id": record_id})
        # updated_record is guaranteed to be set when found is True
        return updated_record or {}

    def delete(self, record_id: str, data_dir: str) -> bool:
        """Delete the transaction with the given id. Return True if deleted, False if not found."""
        try:
            records = self._repository.load_all(data_dir) or []
        except Exception as exc:
            self._logger.error("Failed to load transactions for delete", {"exception": exc})
            raise

        new_list: List[Dict[str, Any]] = []
        deleted = False
        for rec in records:
            if rec.get("id") == record_id:
                deleted = True
            else:
                new_list.append(rec)

        if not deleted:
            self._logger.info("Transaction delete attempted but not found", {"id": record_id})
            return False

        try:
            self._repository.save_all(data_dir, new_list)
        except Exception as exc:
            self._logger.error("Failed to save transactions on delete", {"exception": exc})
            raise

        self._logger.info("Transaction deleted", {"id": record_id})
        return True
