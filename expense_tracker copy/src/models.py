from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional
from decimal import Decimal


class AppState(Enum):
    """Application lifecycle states."""
    INIT = "INIT"
    READY = "READY"
    ERROR = "ERROR"
    SHUTDOWN = "SHUTDOWN"


@dataclass
class Expense:
    """A single expense record."""
    id: int
    date: str
    amount: Decimal
    category: str
    description: Optional[str] = None


@dataclass
class Settings:
    """Global settings for the store."""
    currency: str


@dataclass
class Config:
    """Runtime configuration and tunables."""
    store_path: str = "data/expenses.json"
    temp_suffix: str = ".tmp"
    allowed_categories: List[str] = field(default_factory=lambda: ["food", "transport", "utilities", "entertainment", "health", "other"])
    default_currency: str = "PLN"
    description_max_length: int = 1024
    json_indent: int = 2
    serializer_field_order: Dict[str, List[str]] = field(default_factory=lambda: {
        "store": ["expenses", "settings"],
        "expense": ["id", "date", "amount", "category", "description"],
        "settings": ["currency"]
    })


@dataclass
class ExpenseStore:
    """Top-level in-memory representation of the persisted JSON store."""
    expenses: List[Expense] = field(default_factory=list)
    settings: Settings = field()
