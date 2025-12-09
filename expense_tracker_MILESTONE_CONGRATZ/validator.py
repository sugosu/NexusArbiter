from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Sequence


class ValidationError(Exception):
    """Raised when one or more domain validation rules fail.

    The `errors` attribute is a mapping of field name -> error message.
    """

    def __init__(self, errors: Dict[str, str]) -> None:
        super().__init__("Validation failed: " + "; ".join(f"{k}: {v}" for k, v in errors.items()))
        self.errors = errors


@dataclass(frozen=True)
class Expense:
    id: Optional[int]
    date: str
    amount: Decimal
    category: str
    description: Optional[str] = None


@dataclass(frozen=True)
class Settings:
    currency: str


class ExpenseValidator:
    """Validate expense and settings inputs against domain invariants.

    Responsibilities implemented:
    - validate_expense_input(candidate) -> Expense
      Validates required fields (date, amount, category), optional id and description.
    - validate_settings(settings_candidate) -> Settings
      Validates that currency is a 3-letter code and normalizes to upper-case.

    Note: This validator expects merged/complete expense data for full validation
    (i.e. for updates the caller should merge existing expense values with a patch
    before calling validate_expense_input).
    """

    def __init__(self, allowed_categories: Sequence[str], description_max_length: int) -> None:
        # Normalize categories to a set of lower-case canonical names for membership tests
        self.allowed_categories = {str(c).lower() for c in allowed_categories}
        self.description_max_length = int(description_max_length)

    def validate_expense_input(self, candidate: Dict[str, Any]) -> Expense:
        """Validate a candidate expense mapping and return a typed Expense.

        Required keys (must be present in candidate):
        - date: string in YYYY-MM-DD representing a valid calendar date
        - amount: numeric or string value convertible to Decimal and > 0
        - category: string present in allowed_categories

        Optional:
        - id: non-negative integer when present
        - description: string no longer than description_max_length

        Raises ValidationError with a dict of field->message on failure.
        """
        errors: Dict[str, str] = {}

        # ID (optional)
        id_val = candidate.get("id")
        if id_val is not None:
            if not isinstance(id_val, int):
                errors["id"] = "id must be an integer"
            else:
                if id_val < 0:
                    errors["id"] = "id must be non-negative"

        # Date (required)
        date_val = candidate.get("date")
        if date_val is None:
            errors["date"] = "date is required and must be in YYYY-MM-DD format"
        else:
            if not isinstance(date_val, str):
                errors["date"] = "date must be a string in YYYY-MM-DD format"
            else:
                try:
                    # datetime.date.fromisoformat enforces YYYY-MM-DD and valid calendar date
                    _ = date.fromisoformat(date_val)
                except Exception:
                    errors["date"] = "date must be a valid date in YYYY-MM-DD format"

        # Amount (required)
        amount_val = candidate.get("amount")
        amount_dec: Optional[Decimal] = None
        if amount_val is None:
            errors["amount"] = "amount is required and must be a positive number"
        else:
            try:
                # Accept numeric types and strings. Use Decimal for precise representation.
                amount_dec = Decimal(str(amount_val))
            except (InvalidOperation, TypeError, ValueError):
                errors["amount"] = "amount must be a numeric value"
            else:
                if amount_dec <= 0:
                    errors["amount"] = "amount must be greater than zero"

        # Category (required)
        category_val = candidate.get("category")
        if category_val is None:
            errors["category"] = "category is required"
        else:
            if not isinstance(category_val, str):
                errors["category"] = "category must be a string"
            else:
                if category_val.lower() not in self.allowed_categories:
                    errors["category"] = (
                        "category is not allowed: must be one of " + ", ".join(sorted(self.allowed_categories))
                    )

        # Description (optional)
        description_val = candidate.get("description")
        if description_val is not None:
            if not isinstance(description_val, str):
                errors["description"] = "description must be a string"
            else:
                if len(description_val) > self.description_max_length:
                    errors["description"] = (
                        f"description must be at most {self.description_max_length} characters"
                    )

        if errors:
            raise ValidationError(errors)

        # At this point fields are valid; construct canonical typed Expense
        description_out: Optional[str]
        if description_val is None:
            description_out = None
        else:
            # Normalize empty string to None to represent omitted description
            description_out = description_val if description_val != "" else None

        # amount_dec is not None here because we validated
        assert amount_dec is not None

        return Expense(
            id=id_val,
            date=str(date_val),
            amount=amount_dec,
            category=str(category_val),
            description=description_out,
        )

    def validate_settings(self, settings_candidate: Dict[str, Any]) -> Settings:
        """Validate settings mapping and return a typed Settings.

        Required:
        - currency: 3-letter currency code (letters). Normalized to upper-case.

        Raises ValidationError on failure.
        """
        errors: Dict[str, str] = {}

        currency = settings_candidate.get("currency")
        if currency is None:
            errors["currency"] = "currency is required"
        else:
            if not isinstance(currency, str):
                errors["currency"] = "currency must be a 3-letter string"
            else:
                cur = currency.strip()
                if len(cur) != 3 or not cur.isalpha():
                    errors["currency"] = "currency must be a 3-letter alphabetic code (e.g. PLN)"

        if errors:
            raise ValidationError(errors)

        # Normalize to upper-case canonical form
        return Settings(currency=currency.strip().upper())
