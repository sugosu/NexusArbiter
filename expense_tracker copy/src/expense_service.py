from typing import Any, Dict, List, Optional

from .models import Expense, ExpenseStore, Settings
from .expense_repository import ExpenseRepository
from .expense_validator import ExpenseValidator


class ExpenseService:
    """Business service for expense operations.

    NOTE: Domain-specific exception classes (e.g. ValidationError, NotFoundError)
    are not referenced here because they were not provided in the manifest.
    Implementations may raise those specific exceptions from the validator or
    repository. This class will raise KeyError for missing expenses and will
    allow validator/repository exceptions to propagate.
    """

    def __init__(self, repository: ExpenseRepository, validator: ExpenseValidator) -> None:
        self.repository = repository
        self.validator = validator

    def list_expenses(self) -> List[Expense]:
        """Return a list of all expenses ordered by id ascending."""
        store = self.repository.load_store()
        # Assume store.expenses is a list of Expense objects
        return sorted(list(store.expenses), key=lambda e: e.id)

    def get_expense(self, expense_id: int) -> Optional[Expense]:
        """Return the expense with given id, or None if not found."""
        store = self.repository.load_store()
        for exp in store.expenses:
            if exp.id == expense_id:
                return exp
        return None

    def add_expense(self, expense_input: Dict[str, Any]) -> Expense:
        """Validate and add a new expense. Returns the persisted Expense with assigned id.

        The caller-provided id (if any) is ignored.
        """
        # Ensure caller-provided id is ignored
        candidate = dict(expense_input)
        candidate.pop("id", None)

        # Validate fields (may raise validator-specific ValidationError)
        validated = self.validator.validate_expense_input(candidate)

        created_holder: List[Expense] = []

        def modifier(store: ExpenseStore) -> ExpenseStore:
            # Determine next id deterministically
            max_id = 0
            for e in store.expenses:
                try:
                    if isinstance(e.id, int) and e.id > max_id:
                        max_id = e.id
                except Exception:
                    # Ignore malformed id during id computation; repository/serializer
                    # guarantees structural checks elsewhere.
                    pass
            new_id = max_id + 1

            new_exp = Expense(
                id=new_id,
                date=validated.date,
                amount=validated.amount,
                category=validated.category,
                description=getattr(validated, "description", None),
            )
            store.expenses.append(new_exp)
            created_holder.append(new_exp)
            return store

        # perform_transaction will load-modify-save atomically (may raise IO errors)
        self.repository.perform_transaction(modifier)

        # Return the created expense
        if not created_holder:
            # Defensive: should not happen
            raise RuntimeError("Failed to create expense")
        return created_holder[0]

    def update_expense(self, expense_id: int, patch: Dict[str, Any]) -> Expense:
        """Update an existing expense by id with fields from patch.

        Returns the updated Expense. Raises KeyError if not found.
        """
        updated_holder: List[Expense] = []

        def modifier(store: ExpenseStore) -> ExpenseStore:
            for idx, e in enumerate(store.expenses):
                if e.id == expense_id:
                    # Merge fields: start from existing expense values
                    merged: Dict[str, Any] = {
                        "id": e.id,
                        "date": e.date,
                        "amount": e.amount,
                        "category": e.category,
                        "description": getattr(e, "description", None),
                    }
                    # Apply patch (ignore id if present)
                    for k, v in patch.items():
                        if k == "id":
                            continue
                        merged[k] = v

                    # Validate merged data (validator returns an Expense-like object)
                    validated = self.validator.validate_expense_input(merged)

                    # Ensure id remains the same
                    updated_exp = Expense(
                        id=expense_id,
                        date=validated.date,
                        amount=validated.amount,
                        category=validated.category,
                        description=getattr(validated, "description", None),
                    )
                    store.expenses[idx] = updated_exp
                    updated_holder.append(updated_exp)
                    return store
            # Not found
            raise KeyError(f"Expense id {expense_id} not found")

        self.repository.perform_transaction(modifier)

        if not updated_holder:
            # Shouldn't reach here because modifier raises if not found
            raise KeyError(f"Expense id {expense_id} not found")
        return updated_holder[0]

    def delete_expense(self, expense_id: int) -> None:
        """Remove the expense with given id. Raises KeyError if not found."""
        def modifier(store: ExpenseStore) -> ExpenseStore:
            new_list = [e for e in store.expenses if e.id != expense_id]
            if len(new_list) == len(store.expenses):
                raise KeyError(f"Expense id {expense_id} not found")
            store.expenses = new_list
            return store

        self.repository.perform_transaction(modifier)

    def get_settings(self) -> Settings:
        """Return the current settings."""
        store = self.repository.load_store()
        return store.settings

    def update_settings(self, settings_patch: Dict[str, Any]) -> Settings:
        """Validate and replace settings. Returns the persisted Settings."""
        validated = self.validator.validate_settings(settings_patch)

        def modifier(store: ExpenseStore) -> ExpenseStore:
            store.settings = validated
            return store

        self.repository.perform_transaction(modifier)
        return validated
