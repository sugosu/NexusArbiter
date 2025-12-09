from dataclasses import dataclass, field
from typing import List, Dict


@dataclass(frozen=True)
class Config:
    """Immutable runtime configuration object for the ExpenseTracker application.

    This class is a simple data holder for tunable parameters used across the
    system. Minimal sanity checks are performed in __post_init__ but no IO or
    domain-level validation occurs here.
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
    serializer_field_order: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "store": ["expenses", "settings"],
            "expense": ["id", "date", "amount", "category", "description"],
            "settings": ["currency"],
        }
    )

    def __post_init__(self) -> None:
        # Basic sanity checks. These are intentionally simple and deterministic.
        if not isinstance(self.store_path, str) or not self.store_path:
            raise ValueError("store_path must be a non-empty string")

        if not isinstance(self.temp_suffix, str) or not self.temp_suffix:
            raise ValueError("temp_suffix must be a non-empty string")

        if not isinstance(self.allowed_categories, list) or not self.allowed_categories:
            raise ValueError("allowed_categories must be a non-empty list of strings")
        for c in self.allowed_categories:
            if not isinstance(c, str) or not c:
                raise ValueError("each allowed_categories entry must be a non-empty string")

        if not isinstance(self.default_currency, str) or len(self.default_currency) != 3:
            raise ValueError("default_currency must be a 3-letter string")

        if not isinstance(self.description_max_length, int) or self.description_max_length <= 0:
            raise ValueError("description_max_length must be a positive integer")

        if not isinstance(self.json_indent, int) or self.json_indent < 0:
            raise ValueError("json_indent must be a non-negative integer")

        if not isinstance(self.serializer_field_order, dict):
            raise ValueError("serializer_field_order must be a dict mapping section->ordered list of keys")

        # Ensure required serializer field ordering keys exist and contain required items.
        required = {
            "store": ["expenses", "settings"],
            "expense": ["id", "date", "amount", "category", "description"],
            "settings": ["currency"],
        }
        for section, expected_keys in required.items():
            value = self.serializer_field_order.get(section)
            if not isinstance(value, list):
                raise ValueError(f"serializer_field_order['{section}'] must be a list of keys")
            # Ensure the expected keys are present; do not enforce exact match to allow harmless extensions.
            missing = [k for k in expected_keys if k not in value]
            if missing:
                raise ValueError(
                    f"serializer_field_order['{section}'] is missing required keys: {missing}"
                )
