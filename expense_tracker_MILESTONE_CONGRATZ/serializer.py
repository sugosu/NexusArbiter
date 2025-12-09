from __future__ import annotations

from collections import OrderedDict
from decimal import Decimal
from typing import Any, Dict, List
import json

# Minimal domain-agnostic type aliases to keep signatures explicit
Expense = Dict[str, Any]
Settings = Dict[str, Any]
ExpenseStore = Dict[str, Any]


class ParseError(ValueError):
    """Raised when JSON text cannot be parsed."""


class StructureError(ValueError):
    """Raised when parsed JSON does not match the expected structural shape."""


class JsonSerializer:
    """
    Deterministic JSON serializer/deserializer with stable field ordering and
    pretty-printing. Does not perform domain-level validation beyond structural
    checks (types and presence of expected top-level keys).

    The serializer expects a field_order mapping with keys:
      - 'store': list of top-level keys in desired order (e.g. ['expenses','settings'])
      - 'expense': list of expense object keys in desired order
      - 'settings': list of settings object keys in desired order

    Notes on design decisions (short):
    - Decimal values are preserved where possible; Decimal is converted to float
      for JSON encoding to produce numeric JSON values. This may lose precision
      for extreme decimals but keeps numeric types in JSON.
    - The serializer omits the `description` key from an expense when it is
      missing or None to match the project's representation where description
      may be omitted for no description.
    """

    def __init__(self, field_order: Dict[str, List[str]], indent: int = 2) -> None:
        self.field_order = field_order
        self.indent = indent

    def deserialize(self, raw_text: str) -> ExpenseStore:
        """
        Parse JSON text into an ExpenseStore, performing structural checks.

        Raises:
          ParseError: if JSON is syntactically invalid.
          StructureError: if the top-level shape or required types are not present.
        """
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ParseError(f"Invalid JSON: {exc.msg}") from exc

        if not isinstance(data, dict):
            raise StructureError("Top-level JSON must be an object (mapping).")

        expected_top_keys = list(self.field_order.get("store", ["expenses", "settings"]))
        if set(data.keys()) != set(expected_top_keys):
            raise StructureError(
                f"Top-level object must contain exactly the keys: {expected_top_keys}; found: {list(data.keys())}"
            )

        # expenses must be a list
        expenses = data.get("expenses")
        if not isinstance(expenses, list):
            raise StructureError("'expenses' must be an array/list.")

        for idx, item in enumerate(expenses):
            if not isinstance(item, dict):
                raise StructureError(f"Each expense must be an object; item at index {idx} is {type(item).__name__}.")

            # Minimal structural requirements: id, date, amount, category
            required_fields = ["id", "date", "amount", "category"]
            for f in required_fields:
                if f not in item:
                    raise StructureError(f"Expense at index {idx} missing required field '{f}'.")

            # Type checks (structural only)
            if not isinstance(item.get("id"), int):
                raise StructureError(f"Expense.id at index {idx} must be an integer.")
            if not isinstance(item.get("date"), str):
                raise StructureError(f"Expense.date at index {idx} must be a string.")
            amount_val = item.get("amount")
            if not (isinstance(amount_val, (int, float)) or isinstance(amount_val, str)):
                # allow string here (could be a serialized Decimal) but not other types
                # Note: domain-level validation will enforce numeric positivity.
                raise StructureError(f"Expense.amount at index {idx} must be a number or string representing a number.")
            if not isinstance(item.get("category"), str):
                raise StructureError(f"Expense.category at index {idx} must be a string.")
            desc = item.get("description", None)
            if desc is not None and not isinstance(desc, str):
                raise StructureError(f"Expense.description at index {idx} must be a string or null if present.")

        # settings must be an object with currency string
        settings = data.get("settings")
        if not isinstance(settings, dict):
            raise StructureError("'settings' must be an object/dict.")
        if "currency" not in settings or not isinstance(settings.get("currency"), str):
            raise StructureError("'settings' must contain a 'currency' string field.")

        # If all structural checks pass, return the raw parsed structure as-is.
        return data

    def serialize(self, store: ExpenseStore) -> str:
        """
        Produce a deterministic pretty-printed JSON string from an in-memory
        ExpenseStore using the configured field ordering.

        Raises:
          StructureError: if provided store does not have expected top-level shape.
        """
        if not isinstance(store, dict):
            raise StructureError("store must be a mapping/dict.")

        expected_top_keys = list(self.field_order.get("store", ["expenses", "settings"]))
        if set(store.keys()) != set(expected_top_keys):
            raise StructureError(
                f"store must contain exactly the keys: {expected_top_keys}; found: {list(store.keys())}"
            )

        # Build OrderedDict for top-level with stable order
        out_store: "OrderedDict[str, Any]" = OrderedDict()
        # Top-level: expenses then settings per field_order
        for key in expected_top_keys:
            if key == "expenses":
                expenses = store.get("expenses", [])
                if not isinstance(expenses, list):
                    raise StructureError("'expenses' must be a list for serialization.")

                ordered_expenses: List[OrderedDict] = []
                expense_keys = list(self.field_order.get("expense", ["id", "date", "amount", "category", "description"]))

                for item in expenses:
                    if not isinstance(item, dict):
                        raise StructureError("Each expense must be a mapping/dict for serialization.")
                    od = OrderedDict()
                    for k in expense_keys:
                        if k == "description":
                            # Omit description when missing or None to match store conventions
                            if "description" in item and item.get("description") is not None:
                                od["description"] = item.get("description")
                        else:
                            if k not in item:
                                raise StructureError(f"Expense missing required key '{k}' during serialization.")
                            value = item[k]
                            # Convert Decimal to float for numeric JSON output
                            if isinstance(value, Decimal):
                                value = float(value)
                            od[k] = value
                    ordered_expenses.append(od)
                out_store["expenses"] = ordered_expenses

            elif key == "settings":
                settings = store.get("settings", {})
                if not isinstance(settings, dict):
                    raise StructureError("'settings' must be an object/dict for serialization.")
                settings_keys = list(self.field_order.get("settings", ["currency"]))
                od_set = OrderedDict()
                for k in settings_keys:
                    if k not in settings:
                        raise StructureError(f"Settings missing required key '{k}' during serialization.")
                    od_set[k] = settings[k]
                out_store["settings"] = od_set

            else:
                # Unknown top-level key in field_order; include it if present in store
                out_store[key] = store.get(key)

        # Use a deterministic JSON dump. Since we used OrderedDict, insertion order is preserved.
        def _default_encoder(obj: Any) -> Any:
            if isinstance(obj, Decimal):
                return float(obj)
            # For any unknown types, fall back to their string representation to avoid dump errors.
            return str(obj)

        # Use separators to keep deterministic spacing: comma+space and colon+space
        text = json.dumps(out_store, indent=self.indent, ensure_ascii=False, default=_default_encoder)
        return text
