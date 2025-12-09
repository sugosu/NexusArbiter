from __future__ import annotations

import json
from collections import OrderedDict
from decimal import Decimal
from typing import Any, Dict, List, Optional

# Local project imports (expected to exist in the project)
from models import Expense, Settings, ExpenseStore
from errors import ParseError, StructureError


class JsonSerializer:
    """
    Deterministic JSON serializer/deserializer for ExpenseStore.

    Responsibilities:
    - Serialize ExpenseStore to pretty-printed JSON with stable field ordering.
    - Deserialize JSON text into ExpenseStore performing structural checks
      (types and required keys) but not performing domain-level validation
      such as allowed categories, date semantics, or description length.

    Notes on defaults: If field_order or indent are not provided, sensible
    defaults matching the project specification are used.
    """

    def __init__(self, field_order: Optional[Dict[str, List[str]]] = None, indent: int = 2) -> None:
        # Default field ordering per system specification.
        if field_order is None:
            field_order = {
                "store": ["expenses", "settings"],
                "expense": ["id", "date", "amount", "category", "description"],
                "settings": ["currency"],
            }
        self.field_order = field_order
        self.indent = indent

    def deserialize(self, raw_text: str) -> ExpenseStore:
        """Parse JSON text into an ExpenseStore.

        Structural checks performed:
        - Top-level must be an object with exactly the keys defined by field_order['store'].
        - 'expenses' must be an array; each expense must be an object with the
          keys described by field_order['expense'] (description may be absent or null).
        - 'settings' must be an object with exactly the keys in field_order['settings'].
        - Types for fields are checked (id -> int, date -> str, amount -> number/Decimal, category -> str,
          description -> str|null).

        Raises:
            ParseError: if JSON is syntactically invalid.
            StructureError: if top-level or nested structure does not match expectations.
        """
        try:
            # Use Decimal for parsing float numbers to preserve numeric fidelity
            parsed = json.loads(raw_text, parse_float=Decimal, parse_int=int)
        except json.JSONDecodeError as e:
            raise ParseError(f"Invalid JSON: {e.msg}") from e

        # Top-level must be a dict/object
        if not isinstance(parsed, dict):
            raise StructureError("Top-level JSON must be an object")

        expected_top_keys = list(self.field_order.get("store", ["expenses", "settings"]))
        parsed_keys = list(parsed.keys())
        # Enforce exact key set (order in file may vary; we check membership)
        if set(parsed.keys()) != set(expected_top_keys):
            raise StructureError(f"Top-level object must contain exactly keys: {expected_top_keys}")

        # Validate 'expenses'
        expenses_raw = parsed.get("expenses")
        if not isinstance(expenses_raw, list):
            raise StructureError("'expenses' must be an array")

        expenses: List[Expense] = []
        expense_keyset = set(self.field_order.get("expense", ["id", "date", "amount", "category", "description"]))

        for idx, item in enumerate(expenses_raw):
            if not isinstance(item, dict):
                raise StructureError(f"Each expense must be an object (index {idx})")

            # Allow description to be absent or null. Other keys must be present and no unknown keys allowed.
            keys_present = set(item.keys())
            allowed_keys = set(expense_keyset)
            # description is optional
            allowed_keys_optional = set(expense_keyset) - {"description"}

            if not allowed_keys_optional.issubset(keys_present):
                missing = allowed_keys_optional - keys_present
                raise StructureError(f"Expense at index {idx} missing required keys: {sorted(missing)}")

            # Disallow unknown keys
            extra = keys_present - expense_keyset
            if extra:
                raise StructureError(f"Expense at index {idx} contains unexpected keys: {sorted(extra)}")

            # id
            raw_id = item.get("id")
            if not isinstance(raw_id, int):
                raise StructureError(f"Expense.id must be integer (index {idx})")

            # date
            raw_date = item.get("date")
            if not isinstance(raw_date, str):
                raise StructureError(f"Expense.date must be string (index {idx})")

            # amount
            raw_amount = item.get("amount")
            if not (isinstance(raw_amount, (int, float, Decimal))):
                raise StructureError(f"Expense.amount must be a number (index {idx})")
            # Normalize amount to Decimal
            if isinstance(raw_amount, Decimal):
                amount_dec = raw_amount
            else:
                # Convert using Decimal(str(...)) to avoid binary float surprises
                amount_dec = Decimal(str(raw_amount))

            # category
            raw_category = item.get("category")
            if not isinstance(raw_category, str):
                raise StructureError(f"Expense.category must be string (index {idx})")

            # description (optional or null)
            raw_description = item.get("description", None)
            if raw_description is None:
                description_val = None
            else:
                if not isinstance(raw_description, str):
                    raise StructureError(f"Expense.description must be string or null (index {idx})")
                # Treat empty string as None at structural level is acceptable; keep as empty string
                description_val = raw_description if raw_description != "" else None

            # Construct domain Expense object
            expense_obj = Expense(
                id=raw_id,
                date=raw_date,
                amount=amount_dec,
                category=raw_category,
                description=description_val,
            )
            expenses.append(expense_obj)

        # Validate settings
        settings_raw = parsed.get("settings")
        if not isinstance(settings_raw, dict):
            raise StructureError("'settings' must be an object")

        expected_settings_keys = list(self.field_order.get("settings", ["currency"]))
        if set(settings_raw.keys()) != set(expected_settings_keys):
            raise StructureError(f"'settings' must contain exactly keys: {expected_settings_keys}")

        currency_raw = settings_raw.get("currency")
        if not isinstance(currency_raw, str):
            raise StructureError("settings.currency must be a string")

        settings_obj = Settings(currency=currency_raw)

        store = ExpenseStore(expenses=expenses, settings=settings_obj)
        return store

    def serialize(self, store: ExpenseStore) -> str:
        """Serialize an ExpenseStore into pretty-printed JSON string with stable field ordering.

        - Uses field_order to determine key ordering for top-level, expense objects, and settings.
        - Omits the 'description' field for expenses when it is None or an empty string to keep output concise.
        - Numeric Decimal amounts are converted to native JSON numbers (via float conversion) for readability.

        Returns:
            JSON string (unicode) with deterministic spacing and ordering.
        """
        # Build ordered top-level mapping
        store_order = self.field_order.get("store", ["expenses", "settings"]) 
        expense_order = self.field_order.get("expense", ["id", "date", "amount", "category", "description"]) 
        settings_order = self.field_order.get("settings", ["currency"]) 

        top = OrderedDict()

        # Expenses
        expenses_list: List[OrderedDict] = []
        for exp in getattr(store, "expenses", []):
            exp_od = OrderedDict()
            # id
            exp_od[expense_order[0]] = int(getattr(exp, "id"))
            # date
            exp_od[expense_order[1]] = str(getattr(exp, "date"))
            # amount -> convert Decimal/int to native JSON number
            raw_amount = getattr(exp, "amount")
            if isinstance(raw_amount, Decimal):
                try:
                    amount_num = float(raw_amount)
                except Exception:
                    # Fallback: use Decimal's string representation then float
                    amount_num = float(str(raw_amount))
            else:
                amount_num = float(raw_amount)
            exp_od[expense_order[2]] = amount_num
            # category
            exp_od[expense_order[3]] = str(getattr(exp, "category"))
            # description (optional)
            desc_val = getattr(exp, "description", None)
            if desc_val is not None and desc_val != "":
                exp_od[expense_order[4]] = str(desc_val)
            # If description is None or empty, omit the key entirely (as specified)
            expenses_list.append(exp_od)

        top[store_order[0]] = expenses_list

        # Settings
        settings_obj = getattr(store, "settings")
        settings_od = OrderedDict()
        settings_od[settings_order[0]] = str(getattr(settings_obj, "currency"))
        top[store_order[1]] = settings_od

        # Dump to JSON with stable ordering (we constructed OrderedDicts accordingly)
        try:
            text = json.dumps(top, indent=self.indent, ensure_ascii=False)
        except TypeError as e:
            # In case something non-serializable slipped through, raise StructureError
            raise StructureError(f"Failed to serialize store: {e}") from e

        return text
