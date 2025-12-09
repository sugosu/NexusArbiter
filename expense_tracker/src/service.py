from typing import List, Optional, Dict, Any, Callable
from dataclasses import asdict, replace
import copy

# Import domain types and error types from project modules.
# These modules are expected to exist as described in the manifest/story.
from models import Expense, Settings, ExpenseStore
from errors import ValidationError, NotFoundError


class ExpenseService:
    """Business service for expense operations.

    Responsibilities:
    - Validate inputs via provided ExpenseValidator.
    - Perform read-modify-write operations via provided ExpenseRepository.

    Note: This implementation assumes repository.perform_transaction(modifier)
    will return the saved ExpenseStore instance on success and that the
    repository and validator raise the documented exceptions defined in
    errors.py (ValidationError, NotFoundError, IOError, etc.).
    """

    def __init__(self, repository, validator) -> None:
        # repository: ExpenseRepository implementing the interface described in manifest
        # validator: ExpenseValidator instance
        self.repository = repository
        self.validator = validator

    def list_expenses(self) -> List[Expense]:
        """Return a copy of all expenses ordered by id ascending.

        May raise repository IO-related exceptions.
        """
        store: ExpenseStore = self.repository.load_store()
        # Ensure stable ordering by id ascending
        expenses_sorted = sorted(store.expenses, key=lambda e: e.id)
        # Return deep copies to avoid accidental external mutation
        return [copy.deepcopy(e) for e in expenses_sorted]

    def get_expense(self, expense_id: int) -> Optional[Expense]:
        """Return the expense with given id or None if not found."""
        store: ExpenseStore = self.repository.load_store()
        for e in store.expenses:
            if e.id == expense_id:
                return copy.deepcopy(e)
        return None

    def add_expense(self, expense_input: Dict[str, Any]) -> Expense:
        """Validate and append a new expense using repository.perform_transaction.

        The caller-provided id (if any) is ignored and a deterministic id is assigned
        by the repository-level transaction (max existing id + 1, first id = 1).

        Returns the persisted Expense including assigned id.
        Raises ValidationError for invalid input or IOErrors from repository.
        """
        # Validate candidate fields (exclude id if present to ensure repository assigns it)
        candidate = dict(expense_input)
        candidate.pop("id", None)
        validated: Expense = self.validator.validate_expense_input(candidate)

        def modifier(store: ExpenseStore) -> ExpenseStore:
            # Determine next id deterministically
            max_id = 0
            for ex in store.expenses:
                try:
                    if ex.id > max_id:
                        max_id = ex.id
                except Exception:
                    # Defensive: if malformed entry missing id, treat as 0
                    continue
            new_id = max_id + 1 if max_id >= 0 else 1

            # Ensure the validated object has the assigned id
            # Use dataclasses.replace if possible, otherwise set attribute.
            try:
                new_exp = replace(validated, id=new_id)
            except Exception:
                # Fallback: shallow copy and set attribute
                new_exp = copy.deepcopy(validated)
                setattr(new_exp, "id", new_id)

            store.expenses.append(new_exp)
            return store

        saved_store: ExpenseStore = self.repository.perform_transaction(modifier)
        # Find and return the newly added expense
        for ex in saved_store.expenses:
            if ex.id == getattr(validated, "id", None) or ex.id == (max((e.id for e in saved_store.expenses), default=0)):
                # Return deep copy
                if ex.id == getattr(validated, "id", None) or True:
                    return copy.deepcopy(ex)
        # As a fallback, try to locate by the max id
        max_id = max((e.id for e in saved_store.expenses), default=None)
        if max_id is not None:
            for ex in saved_store.expenses:
                if ex.id == max_id:
                    return copy.deepcopy(ex)
        # Should not happen; defensive error
        raise RuntimeError("Failed to locate newly added expense after save")

    def update_expense(self, expense_id: int, patch: Dict[str, Any]) -> Expense:
        """Update an existing expense by id with provided patch fields.

        The patch may include date, amount, category, description. Any id in the patch
        is ignored. Validation is applied to the merged result. Raises NotFoundError
        if the target expense does not exist.
        """
        patch = dict(patch)
        patch.pop("id", None)

        def modifier(store: ExpenseStore) -> ExpenseStore:
            for idx, ex in enumerate(store.expenses):
                if ex.id == expense_id:
                    # Merge existing fields with patch for validation
                    # Convert existing expense to dict for merging
                    try:
                        base = asdict(ex)
                    except Exception:
                        # Fallback: build minimal dict
                        base = {
                            "id": getattr(ex, "id", None),
                            "date": getattr(ex, "date", None),
                            "amount": getattr(ex, "amount", None),
                            "category": getattr(ex, "category", None),
                            "description": getattr(ex, "description", None),
                        }
                    merged = dict(base)
                    merged.update(patch)
                    # Validate merged candidate
                    validated = self.validator.validate_expense_input(merged)
                    # Ensure id is preserved as expense_id
                    try:
                        validated = replace(validated, id=expense_id)
                    except Exception:
                        setattr(validated, "id", expense_id)
                    store.expenses[idx] = validated
                    return store
            # Not found
            raise NotFoundError(f"Expense with id {expense_id} not found")

        saved_store: ExpenseStore = self.repository.perform_transaction(modifier)
        # Return updated expense copy
        for ex in saved_store.expenses:
            if ex.id == expense_id:
                return copy.deepcopy(ex)
        # Should not happen
        raise RuntimeError(f"Expense {expense_id} not present after update")

    def delete_expense(self, expense_id: int) -> None:
        """Remove expense by id using a transaction. Raises NotFoundError if missing."""
        def modifier(store: ExpenseStore) -> ExpenseStore:
            new_expenses = [ex for ex in store.expenses if ex.id != expense_id]
            if len(new_expenses) == len(store.expenses):
                raise NotFoundError(f"Expense with id {expense_id} not found")
            store.expenses = new_expenses
            return store

        self.repository.perform_transaction(modifier)

    def get_settings(self) -> Settings:
        """Return current settings from store."""
        store: ExpenseStore = self.repository.load_store()
        # Return a defensive copy
        return copy.deepcopy(store.settings)

    def update_settings(self, settings_patch: Dict[str, Any]) -> Settings:
        """Validate and replace settings using a transaction.

        The validator returns a Settings instance; repository persists it.
        """
        validated_settings: Settings = self.validator.validate_settings(settings_patch)

        def modifier(store: ExpenseStore) -> ExpenseStore:
            store.settings = validated_settings
            return store

        self.repository.perform_transaction(modifier)
        return copy.deepcopy(validated_settings)
