from typing import Any, Dict, Optional, List
from decimal import Decimal, InvalidOperation
from datetime import datetime
import re


class ValidationError(Exception):
    """Exception raised when validation of input data fails.

    Attributes:
        message: human friendly message describing the validation failure
        field_errors: optional mapping of field -> error message for programmatic inspection
    """

    def __init__(self, message: str, field_errors: Optional[Dict[str, str]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.field_errors = field_errors or {}

    def __str__(self) -> str:
        if self.field_errors:
            return f"{self.message}: {self.field_errors}"
        return self.message


class ExpenseValidator:
    """Validate expense inputs and settings against domain invariants.

    Notes / deterministic defaults chosen when ambiguous:
    - Category comparison is performed case-insensitively but the returned category
      is the canonical form present in allowed_categories (assumed lower-case list).
    - Dates must match YYYY-MM-DD and represent a real calendar date.
    - Amounts are returned as Decimal and must be strictly > 0.
    - id is optional; when present it must be a non-negative integer.

    The class raises ValidationError on the first validation failure encountered with
    a descriptive message and a `field_errors` mapping when applicable.
    """

    DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    def __init__(self, allowed_categories: List[str], description_max_length: int) -> None:
        # store canonical allowed categories in a set for fast membership tests
        # assume allowed_categories contains canonical strings (e.g., lower-case)
        self.allowed_categories = list(allowed_categories)
        self._allowed_set = {c.lower() for c in allowed_categories}
        self.description_max_length = int(description_max_length)

    def validate_expense_input(self, candidate: Dict[str, Any]) -> Expense:
        """Validate a user-supplied expense mapping and return a canonical Expense instance.

        Expected keys in candidate: date, amount, category, description (optional), id (optional).
        Required keys: date, amount, category. If any are missing, a ValidationError is raised.

        Returned Expense fields:
        - id: int | None (if not supplied)
        - date: str (YYYY-MM-DD)
        - amount: Decimal (> 0)
        - category: canonical string from allowed_categories
        - description: Optional[str] (None if absent)
        """
        errors: Dict[str, str] = {}

        # id (optional)
        id_value = candidate.get("id")
        if id_value is not None:
            if not isinstance(id_value, int) or isinstance(id_value, bool):
                errors["id"] = "id must be an integer"
            elif id_value < 0:
                errors["id"] = "id must be non-negative"

        # date (required)
        date_value = candidate.get("date")
        if date_value is None:
            errors["date"] = "date is required and must be in YYYY-MM-DD format"
        elif not isinstance(date_value, str):
            errors["date"] = "date must be a string in YYYY-MM-DD format"
        else:
            if not self.DATE_RE.match(date_value):
                errors["date"] = "date must match YYYY-MM-DD"
            else:
                try:
                    # this ensures the date is a valid calendar date
                    datetime.strptime(date_value, "%Y-%m-%d")
                except ValueError:
                    errors["date"] = "date is not a valid calendar date"

        # amount (required)
        amount_value = candidate.get("amount")
        amount_decimal: Optional[Decimal] = None
        if amount_value is None:
            errors["amount"] = "amount is required and must be a positive decimal"
        else:
            try:
                # Accept int, float, Decimal, or numeric strings
                if isinstance(amount_value, Decimal):
                    amount_decimal = amount_value
                else:
                    # Convert via str to avoid float binary issues when a float is provided
                    amount_decimal = Decimal(str(amount_value))
                if amount_decimal <= Decimal("0"):
                    errors["amount"] = "amount must be greater than zero"
            except (InvalidOperation, ValueError, TypeError):
                errors["amount"] = "amount must be a valid decimal number"

        # category (required)
        category_value = candidate.get("category")
        canonical_category: Optional[str] = None
        if category_value is None:
            errors["category"] = "category is required and must be one of allowed categories"
        elif not isinstance(category_value, str):
            errors["category"] = "category must be a string"
        else:
            cat_norm = category_value.strip().lower()
            if cat_norm not in self._allowed_set:
                errors["category"] = f"category '{category_value}' is not allowed"
            else:
                # return the canonical form from allowed_categories list
                # prefer exact match if exists, otherwise pick lowercased match
                for c in self.allowed_categories:
                    if c.lower() == cat_norm:
                        canonical_category = c
                        break
                if canonical_category is None:
                    canonical_category = cat_norm

        # description (optional)
        description_value = candidate.get("description")
        if description_value is None:
            description_final: Optional[str] = None
        else:
            if not isinstance(description_value, str):
                errors["description"] = "description must be a string or omitted/null"
                description_final = None
            else:
                if len(description_value) > self.description_max_length:
                    errors["description"] = (
                        f"description exceeds maximum length of {self.description_max_length} characters"
                    )
                description_final = description_value

        if errors:
            # Aggregate into a single message but retain field-level errors
            raise ValidationError("expense validation failed", field_errors=errors)

        # At this point all required fields validated and converted
        # Construct and return Expense dataclass using keyword args to avoid reliance on ordering
        expense_kwargs: Dict[str, Any] = {
            "id": id_value,
            "date": date_value,
            "amount": amount_decimal,
            "category": canonical_category,
            "description": description_final,
        }

        return Expense(**expense_kwargs)

    def validate_settings(self, settings_candidate: Dict[str, Any]) -> Settings:
        """Validate settings mapping and return a canonical Settings instance.

        Expected keys: currency (required) - a 3-letter ISO-like code. Returns Settings with
        currency normalized to upper-case.
        """
        errors: Dict[str, str] = {}

        currency = settings_candidate.get("currency")
        if currency is None:
            errors["currency"] = "currency is required"
        elif not isinstance(currency, str):
            errors["currency"] = "currency must be a string of three letters"
        else:
            cur = currency.strip()
            if not re.fullmatch(r"[A-Za-z]{3}", cur):
                errors["currency"] = "currency must be a three-letter alphabetic code"
            else:
                currency = cur.upper()

        if errors:
            raise ValidationError("settings validation failed", field_errors=errors)

        return Settings(currency=currency)
