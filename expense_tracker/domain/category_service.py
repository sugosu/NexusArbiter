from typing import List, Dict, Any, Optional

from repository.category_repository import CategoryRepository
from app_logging import AppLogger


class CategoryService:
    """Domain service responsible for CRUD operations over category entities.

    Behavior follows the manifest: delegates persistence to CategoryRepository
    and uses the injected AppLogger for logging. Methods accept data_dir and
    forward it to the repository. Validation and conflict conditions raise
    exceptions (deterministic choice documented below).

    Notes on deterministic error handling (chosen because the manifest allows
    either returning or raising errors but does not prescribe a concrete error
    contract):
      - Validation failures (missing 'id') raise ValueError.
      - Conflicts (duplicate id on create) raise ValueError.
      - Not-found on update raises KeyError.

    These choices are conservative and deterministic; callers may catch and
    translate these exceptions into application-level error payloads as needed.
    """

    def __init__(self, repository: CategoryRepository, logger: AppLogger) -> None:
        """Initialize the service with its repository and logger.

        Do not perform I/O or business logic in constructor; just assign
        dependencies per manifest guidance.
        """
        self._repository = repository
        self._logger = logger

    def create(self, category_params: Dict[str, Any], data_dir: str) -> Dict[str, Any]:
        """Create a new category.

        Raises:
            ValueError: if required validation fails or id conflict detected.
        Returns the created category dict on success.
        """
        # Validate required 'id' per identity policy
        if not isinstance(category_params, dict) or 'id' not in category_params:
            self._logger.error("Category create failed: missing 'id' in params", category_params)
            raise ValueError("'id' is required in category_params")

        existing = self._repository.load_all(data_dir)
        # Check id uniqueness
        new_id = category_params['id']
        for rec in existing:
            if rec.get('id') == new_id:
                self._logger.error("Category create conflict: id already exists", {'id': new_id})
                raise ValueError(f"Category with id '{new_id}' already exists")

        # Append and persist
        updated = list(existing)  # shallow copy
        updated.append(category_params)
        self._repository.save_all(data_dir, updated)
        self._logger.info("Category created", {'id': new_id})
        return category_params

    def list(self, query_params: Dict[str, Any], data_dir: str) -> List[Dict[str, Any]]:
        """Return list of categories, optionally filtered by simple equality.

        Filtering implementation (conservative): for each key/value in
        query_params, include records where record.get(key) == value. This is a
        simple in-memory filter and does not modify persisted data.
        """
        all_categories = self._repository.load_all(data_dir)
        if not query_params:
            self._logger.debug("Listing all categories", {'count': len(all_categories)})
            return all_categories

        # Apply simple equality-based filtering
        def matches(record: Dict[str, Any]) -> bool:
            for k, v in query_params.items():
                if record.get(k) != v:
                    return False
            return True

        filtered = [r for r in all_categories if matches(r)]
        self._logger.debug("Listing categories with filter", {'requested': query_params, 'count': len(filtered)})
        return filtered

    def get(self, record_id: str, data_dir: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single category by id. Returns None if not found."""
        all_categories = self._repository.load_all(data_dir)
        for rec in all_categories:
            if rec.get('id') == record_id:
                return rec

        self._logger.info("Category not found", {'id': record_id})
        return None

    def update(self, record_id: str, update_fields: Dict[str, Any], data_dir: str) -> Dict[str, Any]:
        """Update an existing category and persist changes.

        Raises:
            KeyError: if the target record is not found.
        Returns the updated record on success.
        """
        all_categories = self._repository.load_all(data_dir)
        updated = False
        new_list: List[Dict[str, Any]] = []
        updated_record: Optional[Dict[str, Any]] = None

        for rec in all_categories:
            if rec.get('id') == record_id:
                # Do not allow changing the id via update_fields unless domain
                # contract explicitly allows it; ignore 'id' in update_fields.
                merged = dict(rec)
                for k, v in update_fields.items():
                    if k == 'id':
                        continue
                    merged[k] = v
                updated_record = merged
                new_list.append(merged)
                updated = True
            else:
                new_list.append(rec)

        if not updated or updated_record is None:
            self._logger.info("Category update failed: not found", {'id': record_id})
            raise KeyError(f"Category with id '{record_id}' not found")

        self._repository.save_all(data_dir, new_list)
        self._logger.info("Category updated", {'id': record_id})
        return updated_record

    def delete(self, record_id: str, data_dir: str) -> bool:
        """Delete a category by id. Returns True if removed, False if not found."""
        all_categories = self._repository.load_all(data_dir)
        new_list: List[Dict[str, Any]] = []
        removed = False
        for rec in all_categories:
            if rec.get('id') == record_id:
                removed = True
                continue
            new_list.append(rec)

        if removed:
            self._repository.save_all(data_dir, new_list)
            self._logger.info("Category deleted", {'id': record_id})
            return True

        self._logger.info("Category delete attempted but not found", {'id': record_id})
        return False
