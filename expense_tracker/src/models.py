from __future__ import annotations

"""
Domain models for the ExpenseTracker system.

This module defines the primary domain dataclasses: Expense, Settings, ExpenseStore,
and the AppState enum. These types are lightweight containers and intentionally do
not perform domain validation (validators live in validator.py).

Reasonable defaults and small helper conversion methods are provided to aid
serialization/deserialization. If callers prefer a different representation for
Decimal/JSON, the Serializer component is expected to handle final formatting.
"""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Dict, Any
from enum import Enum


@dataclass
class Expense:
    """Domain expense record.

    Fields:
    - id: unique non-negative integer (assignment responsibility lies with repository)
    - date: string in YYYY-MM-DD format (validation elsewhere)
    - amount: Decimal representing positive monetary amount
    - category: category string
    - description: optional textual description
    """

    id: int
    date: str
    amount: Decimal
    category: str
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, obj: Dict[str, Any]) -> "Expense":
        """Create an Expense from a plain mapping. Performs minimal type conversions
        (e.g. amount -> Decimal). Does not perform domain validation.
        """
        # Minimal deterministic conversions; do not validate semantics here.
        _id = obj.get("id")
        _date = obj.get("date")
        _category = obj.get("category")
        _description = obj.get("description")
        raw_amount = obj.get("amount")

        # Convert amount to Decimal in a deterministic way.
        if isinstance(raw_amount, Decimal):
            _amount = raw_amount
        else:
            try:
                # Use str() to avoid float precision artifacts when given a float.
                _amount = Decimal(str(raw_amount)) if raw_amount is not None else Decimal('0')
            except (InvalidOperation, TypeError):
                # Fall back to zero Decimal; callers/validators should catch invalid domain values.
                _amount = Decimal('0')

        return cls(id=int(_id), date=str(_date), amount=_amount, category=str(_category), description=_description)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a plain mapping. Decimal is represented as a string to preserve
        exact value; serializers may choose to render it as numeric if desired.
        """
        result: Dict[str, Any] = {
            "id": self.id,
            "date": self.date,
            # Represent amount as string to avoid lossy float conversions at the model layer.
            "amount": format(self.amount, 'f'),
            "category": self.category,
        }
        # Include description explicitly (may be None)
        result["description"] = self.description
        return result


@dataclass
class Settings:
    """Application settings.

    Fields:
    - currency: three-letter currency code string.
    """

    currency: str

    @classmethod
    def from_dict(cls, obj: Dict[str, Any]) -> "Settings":
        # Minimal conversion; validation of currency format happens in ExpenseValidator.
        return cls(currency=str(obj.get("currency")))

    def to_dict(self) -> Dict[str, Any]:
        return {"currency": self.currency}


@dataclass
class ExpenseStore:
    """Top-level store mapping persisted to disk.

    Fields (stable ordering for serializer expected):
    - expenses: list of Expense
    - settings: Settings

    Note: A default settings.currency of 'PLN' is provided as a reasonable
    deterministic default when callers do not supply settings. The repository
    typically constructs the canonical default using Config.default_currency.
    """

    expenses: List[Expense] = field(default_factory=list)
    settings: Settings = field(default_factory=lambda: Settings(currency="PLN"))

    @classmethod
    def from_dict(cls, obj: Dict[str, Any]) -> "ExpenseStore":
        # Expect a mapping with keys 'expenses' and 'settings'. Perform minimal conversions.
        raw_expenses = obj.get("expenses") or []
        expenses: List[Expense] = []
        for item in raw_expenses:
            # Assume each item is a mapping; let Expense.from_dict handle conversions.
            expenses.append(Expense.from_dict(item))

        raw_settings = obj.get("settings") or {}
        settings = Settings.from_dict(raw_settings)

        return cls(expenses=expenses, settings=settings)

    def to_dict(self) -> Dict[str, Any]:
        # Return a plain mapping suitable for deterministic serialization by JsonSerializer.
        return {
            "expenses": [e.to_dict() for e in self.expenses],
            "settings": self.settings.to_dict(),
        }


class AppState(Enum):
    INIT = "INIT"
    READY = "READY"
    ERROR = "ERROR"
    SHUTDOWN = "SHUTDOWN"


# Exported names for consumers
__all__ = ["Expense", "Settings", "ExpenseStore", "AppState"]
