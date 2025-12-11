from typing import Callable

from .config import Config
from .models import ExpenseStore
from .json_serializer import JsonSerializer
from .atomic_file_writer import AtomicFileWriter
from typing import Callable, Any, Optional
import os


# Local lightweight exceptions to represent errors the repository may surface.
# In a fuller implementation these would be shared/common exceptions.
class ParseError(Exception):
    pass


class StructureError(Exception):
    pass


class ValidationError(Exception):
    pass


class NotFoundError(Exception):
    pass


class ExpenseRepository:
    """
    Responsible for loading, validating structural shape, repairing a safe default store,
    and atomically saving the entire ExpenseStore.

    Note: This implementation assumes JsonSerializer.serialize/deserialize and
    AtomicFileWriter.atomic_write follow the contracts described in the manifest/story.

    Reasonable deterministic defaults are used where the manifest permits.
    """

    def __init__(self, config: Config, serializer: JsonSerializer, writer: AtomicFileWriter) -> None:
        self.path: str = config.store_path
        self._config = config
        self._serializer = serializer
        self._writer = writer

    def _make_default_store(self) -> ExpenseStore:
        """Create the canonical safe default store as described in the story/manifest.

        Default: expenses = [], settings = { currency: config.default_currency }
        """
        # Deterministically construct default Settings and ExpenseStore instances.
        default_settings = Settings(currency=self._config.default_currency)
        default_store = ExpenseStore(expenses=[], settings=default_settings)
        return default_store

    def initialize_store(self) -> ExpenseStore:
        """Load the file if present and structurally valid; otherwise create and persist a default store.

        - If file missing: create default store, persist it, and return it.
        - If file present but parse/structure invalid: replace with default store and return default.
        - On unrecoverable filesystem errors (permission, etc) an IOError is raised.
        """
        try:
            return self.load_store()
        except FileNotFoundError:
            # Missing file: create and persist default
            default_store = self._make_default_store()
            # save_store will raise IOError on filesystem problems which should propagate
            self.save_store(default_store)
            return default_store
        except (ParseError, StructureError):
            # Recoverable corruption: replace file with default
            default_store = self._make_default_store()
            try:
                self.save_store(default_store)
            except Exception:
                # Let underlying IO errors bubble up; caller (AppController) will treat as fatal
                raise
            return default_store

    def load_store(self) -> ExpenseStore:
        """Read and deserialize the current store from disk.

        Returns:
            ExpenseStore

        Raises:
            FileNotFoundError if file missing.
            IOError for other filesystem errors.
            ParseError or StructureError for invalid JSON/structure as raised by serializer.
        """
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = f.read()
        except FileNotFoundError:
            raise
        except OSError as e:
            # Propagate as IOError for callers
            raise IOError(f"Failed to read store file '{self.path}': {e}") from e

        # Delegate structural parsing to serializer (may raise ParseError/StructureError)
        try:
            store = self._serializer.deserialize(raw)
        except Exception as e:
            # Normalize known serializer exceptions or re-raise unknowns as ParseError/StructureError
            if isinstance(e, (ParseError, StructureError)):
                raise
            # If serializer raises other exception types, wrap as ParseError for clarity
            raise ParseError(f"Serializer failed to parse store: {e}") from e

        return store

    def save_store(self, store: ExpenseStore) -> None:
        """Serialize and atomically replace the persistent store file with provided store.

        Raises IOError if underlying atomic write fails.
        """
        try:
            text = self._serializer.serialize(store)
        except Exception as e:
            # Serialization problems are treated as structure/validation issues
            raise StructureError(f"Failed to serialize store: {e}") from e

        try:
            # Delegate atomic write to the injected writer
            self._writer.atomic_write(self.path, text)
        except Exception as e:
            # Normalize to IOError to match repository contract
            raise IOError(f"Atomic write failed for '{self.path}': {e}") from e

    def perform_transaction(self, modifier: Callable[[Any], Any]) -> ExpenseStore:
        """Read-modify-write primitive.

        - Loads current store, calls modifier(store) to obtain a new store.
        - Validates the structural integrity of the returned store and persists it atomically.
        - Returns the persisted store.

        Errors:
        - ValidationError if modifier returns structurally invalid store.
        - IOError for filesystem errors during load or save.
        """
        # Load current store (may raise FileNotFoundError, IO, ParseError, etc.)
        store = self.load_store()

        # Call modifier to produce new store. Modifier is expected to be a pure function.
        new_store = modifier(store)

        # Accept either a domain ExpenseStore instance or a plain mapping supporting the expected fields.
        # Normalize mapping -> ExpenseStore if necessary.
        if isinstance(new_store, dict):
            try:
                expenses = new_store.get("expenses", [])
                settings_raw = new_store.get("settings", {})
                settings = Settings(**settings_raw) if not isinstance(settings_raw, Settings) else settings_raw
                normalized = ExpenseStore(expenses=expenses, settings=settings)
                new_store = normalized
            except Exception as e:
                raise ValidationError(f"Modifier returned invalid mapping for ExpenseStore: {e}") from e

        # Basic structural checks (duck-typed) to ensure writer/serializer will accept the object.
        if not hasattr(new_store, "expenses") or not hasattr(new_store, "settings"):
            raise ValidationError("Modifier must return an ExpenseStore-like object with 'expenses' and 'settings' attributes")
        if not isinstance(new_store.expenses, list):
            raise ValidationError("'expenses' field must be a list")

        # At this layer we do not perform deep domain validation (ExpenseValidator / Service do that).
        # Persist the normalized store atomically.
        self.save_store(new_store)

        return new_store
