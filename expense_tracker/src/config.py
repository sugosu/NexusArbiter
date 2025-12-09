from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Config:
    """Application configuration and runtime tunables.

    This is a simple, side-effect free holder of configuration values used
    throughout the ExpenseTracker system. Defaults are chosen to match the
    manifest / implementation story. Minimal sanity checks are performed in
    __post_init__ to catch obvious misconfiguration early.

    Note: If different values are desired in runtime, construct a Config
    instance with explicit arguments (e.g., from environment variables) and
    pass it into the composition root (AppController).
    """

    store_path: str = "data/expenses.json"
    temp_suffix: str = ".tmp"
    allowed_categories: List[str] = field(default_factory=lambda: [
        "food",
        "transport",
        "utilities",
        "entertainment",
        "health",
        "other",
    ])
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
    fsync_after_write: bool = True

    def __post_init__(self) -> None:
        # Minimal deterministic sanity checks. Defaults in this module are
        # known-good; these checks guard against accidental runtime
        # construction with invalid values. These checks do not perform any
        # IO or external side effects.
        if not isinstance(self.store_path, str) or not self.store_path:
            raise ValueError("Config.store_path must be a non-empty string")
        if not isinstance(self.temp_suffix, str) or not self.temp_suffix:
            raise ValueError("Config.temp_suffix must be a non-empty string")
        if (
            not isinstance(self.default_currency, str)
            or len(self.default_currency) != 3
        ):
            raise ValueError("Config.default_currency must be a 3-letter currency code")
        if not isinstance(self.description_max_length, int) or self.description_max_length <= 0:
            raise ValueError("Config.description_max_length must be a positive integer")
        if not isinstance(self.json_indent, int) or self.json_indent < 0:
            raise ValueError("Config.json_indent must be a non-negative integer")
        # allowed_categories should be a list of lowercase strings
        if (
            not isinstance(self.allowed_categories, list)
            or not all(isinstance(c, str) and c for c in self.allowed_categories)
        ):
            raise ValueError("Config.allowed_categories must be a non-empty list of strings")
        if not isinstance(self.serializer_field_order, dict):
            raise ValueError("Config.serializer_field_order must be a dict")


__all__ = ["Config"]
