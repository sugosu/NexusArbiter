from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional


# Models container: primary public class is `Models` which exposes
# domain data shapes as nested dataclasses: Expense, Settings, ExpenseStore.
# Note: Domain-level validation (format, allowed categories, etc.) is not
# performed here — this module only defines shapes and light coercion.
class Models:
    @dataclass
    class Expense:
        """Domain expense record.

        Fields mirror the persisted JSON structure. No domain validation is
        performed here beyond light type coercion.
        """

        id: int
        date: str
        amount: Decimal
        category: str
        description: Optional[str] = None

        @classmethod
        def from_dict(cls, data: Dict[str, Any]) -> "Models.Expense":
            """Create an Expense from a plain mapping.

            This method performs minimal coercion (e.g. amount -> Decimal,
            id -> int) but does not enforce domain invariants such as
            allowed categories or date format.
            """
            # id
            id_val = data.get("id")
            if id_val is None:
                raise ValueError("Expense.dict missing required 'id' field")
            try:
                id_int = int(id_val)
            except Exception as exc:  # deterministic, light coercion
                raise ValueError(f"Invalid id value: {id_val}") from exc

            # date
            date_val = data.get("date")
            if date_val is None:
                raise ValueError("Expense.dict missing required 'date' field")
            date_str = str(date_val)

            # amount -> Decimal
            amt = data.get("amount")
            if amt is None:
                raise ValueError("Expense.dict missing required 'amount' field")
            try:
                # Use string conversion for safe Decimal construction
                amount_dec = Decimal(str(amt))
            except (InvalidOperation, ValueError, TypeError) as exc:
                raise ValueError(f"Invalid amount value: {amt}") from exc

            # category
            cat = data.get("category")
            if cat is None:
                raise ValueError("Expense.dict missing required 'category' field")
            category_str = str(cat)

            # description (optional)
            desc = data.get("description")
            if desc is None:
                description_val = None
            else:
                description_val = str(desc)

            return cls(
                id=id_int,
                date=date_str,
                amount=amount_dec,
                category=category_str,
                description=description_val,
            )

        def to_dict(self) -> Dict[str, Any]:
            """Return a dict representation suitable for deterministic
            serialization. The order of insertion follows the canonical
            order expected by the serializer: id, date, amount, category,
            description (description omitted when None to allow serializer
            to omit nulls if desired).
            """
            d: Dict[str, Any] = {}
            d["id"] = int(self.id)
            d["date"] = str(self.date)
            # Convert Decimal to string to preserve exactness in JSON
            # serializer may choose to render numbers differently; using
            # str keeps precise lexical representation.
            d["amount"] = str(self.amount)
            d["category"] = str(self.category)
            if self.description is not None:
                d["description"] = self.description
            return d

    @dataclass
    class Settings:
        """Global settings for the ledger.

        Currently includes only currency (3-letter code). No validation
        of currency format is performed here.
        """

        currency: str

        @classmethod
        def from_dict(cls, data: Dict[str, Any]) -> "Models.Settings":
            curr = data.get("currency")
            if curr is None:
                raise ValueError("Settings.dict missing required 'currency' field")
            return cls(currency=str(curr))

        def to_dict(self) -> Dict[str, Any]:
            return {"currency": str(self.currency)}

    @dataclass
    class ExpenseStore:
        """Top-level in-memory representation of the persisted JSON store.

        Fields:
        - expenses: list of Expense instances
        - settings: Settings instance

        This class provides helpers to construct a default store and to
        convert to/from plain mappings used by serializers.
        """

        expenses: List["Models.Expense"] = field(default_factory=list)
        settings: "Models.Settings" = field(default_factory=lambda: Models.Settings(currency="PLN"))

        @classmethod
        def default_store(cls, default_currency: str = "PLN") -> "Models.ExpenseStore":
            """Create the canonical default safe store.

            Default currency is by convention supplied from Config in the
            application; a reasonable default ('PLN') is used here when one
            is not provided.
            """
            return cls(expenses=[], settings=Models.Settings(currency=default_currency))

        @classmethod
        def from_dict(cls, data: Dict[str, Any]) -> "Models.ExpenseStore":
            # Expect top-level keys 'expenses' and 'settings'
            if not isinstance(data, dict):
                raise ValueError("Store must be a mapping")

            if "expenses" not in data or "settings" not in data:
                raise ValueError("Store mapping must contain 'expenses' and 'settings' keys")

            raw_expenses = data["expenses"]
            if not isinstance(raw_expenses, list):
                raise ValueError("'expenses' must be a list")

            expenses: List[Models.Expense] = []
            for item in raw_expenses:
                if not isinstance(item, dict):
                    raise ValueError("Each expense must be an object")
                expenses.append(Models.Expense.from_dict(item))

            raw_settings = data["settings"]
            if not isinstance(raw_settings, dict):
                raise ValueError("'settings' must be an object")
            settings = Models.Settings.from_dict(raw_settings)

            return cls(expenses=expenses, settings=settings)

        def to_dict(self) -> Dict[str, Any]:
            # Preserve canonical top-level ordering: expenses, settings
            return {
                "expenses": [e.to_dict() for e in self.expenses],
                "settings": self.settings.to_dict(),
            }
