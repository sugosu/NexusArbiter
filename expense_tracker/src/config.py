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

from dataclasses import dataclass, field
from typing import List, TypedDict, Dict


class SerializerFieldOrder(TypedDict):
    store: List[str]
    expense: List[str]
    settings: List[str]


@dataclass(frozen=True)
class Config:
    """Central configuration dataclass for the expense ledger.

    This is a simple immutable holder of runtime tunables used across the
    system. Performs only light sanity checks in __post_init__.

    NOTE: Defaults are taken from the project manifest. If different
    configuration is required at runtime, construct Config(...) with
    overriding values.
    """

    store_path: str = "data/expenses.json"
    temp_suffix: str = ".tmp"
    allowed_categories: List[str] = field(
        default_factory=lambda: [
            "food",
            "transport",
            "utilities",
            "entertainment",
            "health",
            "other",
        ]
    )
    default_currency: str = "PLN"
    description_max_length: int = 1024
    json_indent: int = 2
    serializer_field_order: SerializerFieldOrder = field(
        default_factory=lambda: {
            "store": ["expenses", "settings"],
            "expense": ["id", "date", "amount", "category", "description"],
            "settings": ["currency"],
        }
    )

    def __post_init__(self) -> None:
        # Lightweight sanity checks - keep these minimal and deterministic.
        if not isinstance(self.store_path, str) or not self.store_path:
            raise ValueError("store_path must be a non-empty string")
        if not isinstance(self.temp_suffix, str):
            raise ValueError("temp_suffix must be a string")
        if not isinstance(self.allowed_categories, list) or not self.allowed_categories:
            raise ValueError("allowed_categories must be a non-empty list of strings")
        if not isinstance(self.default_currency, str) or len(self.default_currency) != 3:
            raise ValueError("default_currency must be a three-letter string")
        if not isinstance(self.description_max_length, int) or self.description_max_length <= 0:
            raise ValueError("description_max_length must be a positive integer")
        if not isinstance(self.json_indent, int) or self.json_indent < 0:
            raise ValueError("json_indent must be a non-negative integer")
        # Validate serializer_field_order shape
        sfo = self.serializer_field_order
        expected_keys = ("store", "expense", "settings")
        if not isinstance(sfo, dict) or any(k not in sfo for k in expected_keys):
            raise ValueError("serializer_field_order must be a mapping with keys: store, expense, settings")
        for k in expected_keys:
            v = sfo[k]
            if not isinstance(v, list) or not all(isinstance(i, str) for i in v):
                raise ValueError(f"serializer_field_order['{k}'] must be a list of strings")
