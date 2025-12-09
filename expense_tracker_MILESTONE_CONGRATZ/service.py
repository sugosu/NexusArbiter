from typing import Any, Callable, Dict, List, Optional, Protocol
import copy

# Minimal helper exception types used by the service. In the full system these
# may be provided by a shared errors module; defined here to keep the service
# self-contained for testing.


class ValidationError(Exception):
    """Raised when domain validation fails."""


class NotFoundError(Exception):
    """Raised when an entity cannot be found."""


# Protocols describing the interfaces the service expects from the
# repository and validator. These are intentionally minimal and match the
# manifest's required methods used by ExpenseService.


class ExpenseRepositoryProtocol(Protocol):
    path: str

    def load_store(self) -> Dict[str, Any]:
        ...

    def perform_transaction(self, modifier: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
        ...


class ExpenseValidatorProtocol(Protocol):
    allowed_categories: List[str]
    description_max_length: int

    def validate_expense_input(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        ...

    def validate_settings(self, settings_candidate: Dict[str, Any]) -> Dict[str, Any]:
        ...


# Type aliases for clarity
Expense = Dict[str, Any]
Settings = Dict[str, Any]
ExpenseStore = Dict[str, Any]


class ExpenseService:
    """Business-level operations for expenses and settings.

    Responsibilities:
    - Validate inputs via the provided ExpenseValidator.
    - Use the provided ExpenseRepository for all persistence via read-modify-write
      transactions (perform_transaction) or read-only loads (load_store).

    This class intentionally does not perform any filesystem IO directly.
    """

    def __init__(self, repository: ExpenseRepositoryProtocol, validator: ExpenseValidatorProtocol) -> None:
        self.repository = repository
        self.validator = validator

    def list_expenses(self) -> List[Expense]:
        """Return a list of all expenses ordered by id ascending.

        Returns copies of the expense objects to avoid exposing internal
        repository state.
        """
        store = self.repository.load_store()
        expenses = store.get("expenses", [])
        # Defensive copy and sort by id (missing id treated as 0)
        sorted_expenses = sorted(expenses, key=lambda e: int(e.get("id", 0)))
        return [copy.deepcopy(e) for e in sorted_expenses]

    def get_expense(self, expense_id: int) -> Optional[Expense]:
        """Return the expense with given id or None if not found."""
        store = self.repository.load_store()
        for e in store.get("expenses", []):
            if int(e.get("id", -1)) == int(expense_id):
                return copy.deepcopy(e)
        return None

    def add_expense(self, expense_input: Dict[str, Any]) -> Expense:
        """Validate and add a new expense. The repository assigns a deterministic id.

        Returns the persisted Expense including assigned id.
        """
        # Validate input (validator may ignore id if present)
        validated = self.validator.validate_expense_input(dict(expense_input))

        def modifier(store: ExpenseStore) -> ExpenseStore:
            expenses: List[Expense] = store.get("expenses")
            if expenses is None:
                expenses = []
                store["expenses"] = expenses
            # Compute next id deterministically
            max_id = 0
            for ex in expenses:
                try:
                    iid = int(ex.get("id", 0))
                except Exception:
                    iid = 0
                if iid > max_id:
                    max_id = iid
            new_id = max_id + 1 if max_id >= 0 else 1
            new_expense = dict(validated)
            new_expense["id"] = new_id
            expenses.append(new_expense)
            return store

        saved_store = self.repository.perform_transaction(modifier)
        # find new expense by id
        for e in saved_store.get("expenses", []):
            if int(e.get("id", -1)) == int(validated.get("id", new_id if (new_id := None) is None else -1)):
                # The above is defensive; prefer locating by the id assigned in store.
                pass
        # Simpler: determine highest id in saved_store and return that expense
        max_assigned = 0
        found: Optional[Expense] = None
        for e in saved_store.get("expenses", []):
            try:
                iid = int(e.get("id", 0))
            except Exception:
                iid = 0
            if iid >= max_assigned:
                max_assigned = iid
                found = e
        if found is None:
            # This should not happen; raise IOError-like to indicate persistence problem
            raise IOError("Failed to persist new expense")
        return copy.deepcopy(found)

    def update_expense(self, expense_id: int, patch: Dict[str, Any]) -> Expense:
        """Update an existing expense by id with fields from patch.

        The patch may contain subset of fields (date, amount, category, description).
        The id in patch, if any, is ignored.
        """
        patch_clean = dict(patch)
        patch_clean.pop("id", None)

        def modifier(store: ExpenseStore) -> ExpenseStore:
            expenses: List[Expense] = store.get("expenses", [])
            for idx, ex in enumerate(expenses):
                if int(ex.get("id", -1)) == int(expense_id):
                    merged = dict(ex)
                    merged.update(patch_clean)
                    # Ensure id remains the same when validating/producing canonical expense
                    merged["id"] = int(ex.get("id"))
                    # Validator is expected to raise ValidationError on bad input
                    validated = self.validator.validate_expense_input(merged)
                    # Preserve the id from existing
                    validated["id"] = ex["id"]
                    expenses[idx] = validated
                    return store
            raise NotFoundError(f"Expense with id {expense_id} not found")

        saved_store = self.repository.perform_transaction(modifier)
        # locate updated expense
        for e in saved_store.get("expenses", []):
            if int(e.get("id", -1)) == int(expense_id):
                return copy.deepcopy(e)
        # If not found after save, treat as inconsistent state
        raise IOError(f"Updated expense {expense_id} not found after save")

    def delete_expense(self, expense_id: int) -> None:
        """Remove expense with given id. Raises NotFoundError if missing."""

        def modifier(store: ExpenseStore) -> ExpenseStore:
            expenses: List[Expense] = store.get("expenses", [])
            new_expenses: List[Expense] = []
            found = False
            for ex in expenses:
                if int(ex.get("id", -1)) == int(expense_id):
                    found = True
                    continue
                new_expenses.append(ex)
            if not found:
                raise NotFoundError(f"Expense with id {expense_id} not found")
            store["expenses"] = new_expenses
            return store

        self.repository.perform_transaction(modifier)

    def get_settings(self) -> Settings:
        """Return current settings."""
        store = self.repository.load_store()
        settings = store.get("settings", {})
        return copy.deepcopy(settings)

    def update_settings(self, settings_patch: Dict[str, Any]) -> Settings:
        """Validate and replace settings using a repository transaction.

        The validator.validate_settings is expected to return a canonical Settings
        object (or raise ValidationError).
        """
        validated = self.validator.validate_settings(dict(settings_patch))

        def modifier(store: ExpenseStore) -> ExpenseStore:
            store["settings"] = validated
            return store

        saved_store = self.repository.perform_transaction(modifier)
        settings_after = saved_store.get("settings")
        if settings_after is None:
            # Should not happen; treat as IO/consistency error
            raise IOError("Failed to persist updated settings")
        return copy.deepcopy(settings_after)
