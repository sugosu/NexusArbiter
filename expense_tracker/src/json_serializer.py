from app_controller import AppController
from atomic_file_writer import AtomicFileWriter
from config import Config
from expense_repository import ExpenseRepository
from expense_service import ExpenseService
from expense_validator import ExpenseValidator
from json_serializer import JsonSerializer
from models import Expense
from models import ExpenseStore
from models import ServiceState
from models import Settings

from typing import Mapping, List, Any
from collections import OrderedDict
from decimal import Decimal
import json


# Local exceptions used by the serializer. These are minimal helpers to match
# the error semantics described in the system story (ParseError / StructureError).
class ParseError(Exception):
    pass


class StructureError(Exception):
    pass


class JsonSerializer:
    """Deterministic JSON serializer/deserializer with stable field ordering.

    Responsibilities:
    - serialize(ExpenseStore) -> str: produce pretty-printed JSON with stable
      ordering determined by provided field_order and indent.
    - deserialize(str) -> ExpenseStore: parse JSON text and perform structural
      checks (top-level shape, types). Does not perform domain value validation.

    Note: If field_order keys are missing, reasonable defaults from the
    story are used.
    """

    def __init__(self, field_order: Mapping[str, List[str]], indent: int = 2) -> None:
        # field_order is expected to be a mapping like:
        # { 'store': ['expenses','settings'], 'expense': [...], 'settings': [...] }
        self.field_order = dict(field_order) if field_order is not None else {}
        self.indent = int(indent)

    def deserialize(self, raw_text: str) -> ExpenseStore:
        """Parse raw JSON text into an ExpenseStore dataclass instance.

        Raises:
            ParseError: if the JSON is syntactically invalid.
            StructureError: if the JSON structure (types/required keys) is wrong.
        """
        try:
            # parse_float=Decimal to keep numeric precision for amounts when
            # JSON numbers have fractional parts
            data = json.loads(raw_text, parse_float=Decimal)
        except json.JSONDecodeError as exc:
            raise ParseError(f"JSON parse error: {exc}")

        if not isinstance(data, dict):
            raise StructureError("Top-level JSON must be an object")

        # Expected top-level keys
        store_keys = self.field_order.get("store", ["expenses", "settings"])
        # Ensure required keys exist
        if "expenses" not in data or "settings" not in data:
            raise StructureError("Top-level object must contain 'expenses' and 'settings' keys")

        expenses_raw = data.get("expenses")
        settings_raw = data.get("settings")

        if not isinstance(expenses_raw, list):
            raise StructureError("'expenses' must be an array")
        if not isinstance(settings_raw, dict):
            raise StructureError("'settings' must be an object")

        expenses_list: List[Expense] = []
        expense_order = self.field_order.get("expense", ["id", "date", "amount", "category", "description"]) 

        for idx, item in enumerate(expenses_raw):
            if not isinstance(item, dict):
                raise StructureError(f"Each expense must be an object (index {idx})")

            # Required fields check (structural only)
            for required in ("id", "date", "amount", "category"):
                if required not in item:
                    raise StructureError(f"Expense at index {idx} missing required field '{required}'")

            raw_id = item.get("id")
            # Accept int values; also accept Decimal values that are integral
            if isinstance(raw_id, int):
                eid = raw_id
            elif isinstance(raw_id, Decimal):
                if raw_id == raw_id.to_integral_value():
                    eid = int(raw_id)
                else:
                    raise StructureError(f"Expense.id at index {idx} must be an integer")
            else:
                raise StructureError(f"Expense.id at index {idx} must be an integer")

            raw_date = item.get("date")
            if not isinstance(raw_date, str):
                raise StructureError(f"Expense.date at index {idx} must be a string")

            raw_amount = item.get("amount")
            # amount may be Decimal (from parse_float), int, or float (unlikely with parse_float)
            if isinstance(raw_amount, (int, Decimal)) or isinstance(raw_amount, float):
                # Convert to Decimal for internal representation
                try:
                    amount = Decimal(str(raw_amount))
                except Exception:
                    # fallback to Decimal constructor
                    amount = Decimal(raw_amount)
            else:
                raise StructureError(f"Expense.amount at index {idx} must be numeric")

            raw_category = item.get("category")
            if not isinstance(raw_category, str):
                raise StructureError(f"Expense.category at index {idx} must be a string")

            raw_description = item.get("description") if "description" in item else None
            if raw_description is not None and not isinstance(raw_description, str):
                # allow explicit null -> None, or string; other types are structural error
                raise StructureError(f"Expense.description at index {idx} must be a string or null")

            # Construct domain Expense object. We assume models.Expense accepts these fields.
            expense_obj = Expense(id=eid, date=raw_date, amount=amount, category=raw_category, description=raw_description)
            expenses_list.append(expense_obj)

        # Settings parsing (structural only)
        if "currency" not in settings_raw:
            raise StructureError("settings must contain 'currency' key")
        currency_val = settings_raw.get("currency")
        if not isinstance(currency_val, str):
            raise StructureError("settings.currency must be a string")

        settings_obj = Settings(currency=currency_val)

        store_obj = ExpenseStore(expenses=expenses_list, settings=settings_obj)
        return store_obj

    def serialize(self, store: ExpenseStore) -> str:
        """Serialize an ExpenseStore to deterministic pretty-printed JSON text.

        Rules applied:
        - Top-level keys appear in the order given by field_order['store'].
        - Expense object keys appear in the order given by field_order['expense'].
        - Settings keys appear in the order given by field_order['settings'].
        - If an expense.description is None or empty string, the 'description' key is omitted.
        - Decimal amounts are rendered as JSON numbers (converted to float).
        """
        expense_order = self.field_order.get("expense", ["id", "date", "amount", "category", "description"]) 
        settings_order = self.field_order.get("settings", ["currency"]) 
        store_order = self.field_order.get("store", ["expenses", "settings"]) 

        top = OrderedDict()

        # Build expenses array preserving stable ordering of fields
        expenses_out: List[OrderedDict] = []
        for e in getattr(store, "expenses", []):
            obj = OrderedDict()
            for key in expense_order:
                if key == "id":
                    obj["id"] = int(getattr(e, "id"))
                elif key == "date":
                    obj["date"] = getattr(e, "date")
                elif key == "amount":
                    amt = getattr(e, "amount")
                    # Support Decimal and numeric types; output as number
                    if isinstance(amt, Decimal):
                        # convert to float for JSON numeric literal
                        out_amt = float(amt)
                    else:
                        out_amt = amt
                    obj["amount"] = out_amt
                elif key == "category":
                    obj["category"] = getattr(e, "category")
                elif key == "description":
                    desc = getattr(e, "description", None)
                    # Omit description when absent/None/empty string
                    if desc is None or (isinstance(desc, str) and desc == ""):
                        continue
                    obj["description"] = desc
                else:
                    # Unknown keys are ignored to maintain strict stable ordering
                    continue
            expenses_out.append(obj)

        # Ensure top-level ordering: we iterate store_order and fill known keys
        for key in store_order:
            if key == "expenses":
                top["expenses"] = expenses_out
            elif key == "settings":
                settings_obj = OrderedDict()
                for s_key in settings_order:
                    if s_key == "currency":
                        settings_obj["currency"] = getattr(store.settings, "currency")
                top["settings"] = settings_obj
            else:
                # Unknown top-level keys from field_order are ignored
                continue

        # Custom default to handle Decimal just in case any slipped through
        def _default(o: Any):
            if isinstance(o, Decimal):
                return float(o)
            raise TypeError(f"Object of type {type(o)} is not JSON serializable")

        text = json.dumps(top, indent=self.indent, ensure_ascii=False, default=_default)
        return text
