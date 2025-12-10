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

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Settings:
    """Domain model for global settings.

    Notes:
    - This class is a simple data holder. Validation of values (e.g. 3-letter
      currency codes) is the responsibility of ExpenseValidator.
    - from_dict will tolerate missing keys and provide a best-effort construction
      to aid deserialization; callers should validate afterwards if needed.
    """

    currency: str

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain mapping representation suitable for serialization.

        The serializer component is responsible for stable key ordering, so a
        normal dict is returned here.
        """
        return {"currency": self.currency}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        """Create Settings from a mapping.

        If the currency key is missing or None, an empty string is used. Higher
        level components (Config / Validator / Repository) are responsible for
        supplying defaults and enforcing invariants.
        """
        currency = data.get("currency") if isinstance(data, dict) else None
        if currency is None:
            currency = ""
        return cls(currency=str(currency))
