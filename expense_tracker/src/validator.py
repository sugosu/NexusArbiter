from typing import Any, Dict, Optional, List
import re
from decimal import Decimal, InvalidOperation
from datetime import date

# Import domain types and error types from project modules.
# These modules are expected to exist in the project as described in the manifest.
from models import Expense, Settings
from errors import ValidationError

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ExpenseValidator:
    """Validate expense and settings inputs according to domain invariants.

    Notes / deterministic choices made when information is ambiguous:
    - Category comparisons are case-insensitive; stored category is normalized to lower-case.
    - Empty string descriptions are treated as None (omitted/null in the store).
    - If an "id" is provided it must be a non-negative int; callers that don't want an id simply omit it.
    - The returned Expense object may have id==None when the caller did not provide an id (e.g., for add operations).
    """

    def __init__(self, allowed_categories: List[str], description_max_length: int) -> None:
        # store allowed categories as a lower-cased set for quick membership tests
        self.allowed_categories = {c.lower() for c in allowed_categories}
        self.description_max_length = int(description_max_length)

    def validate_expense_input(self, candidate: Dict[str, Any]) -> Expense:
        """Validate a user-supplied expense dict and return a canonical Expense instance.

        Expects candidate to contain at least: date, amount, category.
        id is optional; if present it must be a non-negative integer.

        Raises:
            ValidationError: with a descriptive message listing violations.
        Returns:
            Expense: a models.Expense instance with typed/normalized fields. id may be None when not provided.
        """
        errors: List[str] = []

        # id (optional)
        id_val: Optional[int] = candidate.get("id")
        if id_val is not None:
            if not isinstance(id_val, int) or id_val < 0:
                errors.append("id must be a non-negative integer if provided")

        # date (required)
        date_val = candidate.get("date")
        if not isinstance(date_val, str):
            errors.append("date is required and must be a string in YYYY-MM-DD format")
        else:
            if not DATE_RE.match(date_val):
                errors.append("date must match YYYY-MM-DD")
            else:
                try:
                    # fromisoformat will raise ValueError for invalid dates like 2021-02-30
                    date.fromisoformat(date_val)
                except ValueError:
                    errors.append("date must be a valid calendar date in YYYY-MM-DD format")

        # amount (required) - coerce to Decimal and ensure > 0
        if "amount" not in candidate:
            errors.append("amount is required and must be a positive number")
            amount_dec = None
        else:
            raw_amount = candidate.get("amount")
            try:
                # Use str() to avoid float precision pitfalls if a float is passed
                amount_dec = Decimal(str(raw_amount))
            except (InvalidOperation, TypeError, ValueError):
                amount_dec = None
                errors.append("amount must be a valid decimal number")
            else:
                if amount_dec <= Decimal("0"):
                    errors.append("amount must be greater than zero")

        # category (required) - normalize to lower-case
        category_val = candidate.get("category")
        if not isinstance(category_val, str):
            errors.append("category is required and must be a string")
        else:
            category_norm = category_val.lower()
            if category_norm not in self.allowed_categories:
                errors.append(f"category '{category_val}' is not allowed")

        # description (optional)
        description_raw = candidate.get("description")
        if description_raw is None or description_raw == "":
            description: Optional[str] = None
        else:
            if not isinstance(description_raw, str):
                errors.append("description must be a string when provided")
                description = None
            else:
                if len(description_raw) > self.description_max_length:
                    errors.append(
                        f"description length must be <= {self.description_max_length} characters"
                    )
                description = description_raw

        if errors:
            # Combine errors into a single ValidationError. Caller may choose to present
            # or log the message(s) individually.
            raise ValidationError("; ".join(errors))

        # Construct and return an Expense instance. It's acceptable for id to be None
        # when not provided by the caller (e.g., add_expense flow assigns the id later).
        expense = Expense(
            id=id_val,
            date=date_val,  # validated string in YYYY-MM-DD
            amount=amount_dec,
            category=category_norm,
            description=description,
        )
        return expense

    def validate_settings(self, settings_candidate: Dict[str, Any]) -> Settings:
        """Validate settings map and return a Settings instance.

        Requirements:
        - must contain 'currency' as a three-letter string. We'll normalize to upper-case.

        Raises:
            ValidationError: for missing/invalid currency.
        Returns:
            Settings: models.Settings with normalized currency code.
        """
        currency = settings_candidate.get("currency")
        if not isinstance(currency, str):
            raise ValidationError("settings.currency is required and must be a three-letter string")

        currency_norm = currency.strip().upper()
        if len(currency_norm) != 3 or not currency_norm.isalpha():
            raise ValidationError("settings.currency must be a three-letter alphabetic code (e.g., PLN)")

        return Settings(currency=currency_norm)
