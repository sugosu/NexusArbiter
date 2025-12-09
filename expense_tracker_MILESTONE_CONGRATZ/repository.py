from typing import Any, Callable, Dict, List, Optional
import os
import json

# Minimal local exception types used by the repository. These are simple
# placeholders to make error semantics explicit. In the full project these
# may be shared/common exception types.

class ParseError(Exception):
    pass

class StructureError(Exception):
    pass

class ValidationError(Exception):
    pass

class NotFoundError(Exception):
    pass

Expense = Dict[str, Any]
ExpenseStore = Dict[str, Any]


class ExpenseRepository:
    """
    Responsible for filesystem access for the single JSON expense store.

    Responsibilities implemented here:
    - initialize_store(): ensure the store file exists and has correct top-level
      structure, otherwise replace it with a safe default.
    - load_store(): read and deserialize the store using provided serializer.
    - save_store(): serialize and atomically persist a given in-memory store.
    - perform_transaction(modifier): read-modify-write primitive that loads,
      applies modifier, validates basic structure, and saves atomically.

    Note: For default currency we use "PLN" as a deterministic default as
    described in the manifest. In the full application this value is normally
    provided by Config and injected into the repository or used by callers.
    """

    def __init__(self, path: str, serializer: Any, writer: Any) -> None:
        self.path = path
        self.serializer = serializer
        self.writer = writer

    def initialize_store(self) -> ExpenseStore:
        """
        Ensure the JSON store exists and is structurally valid. If the file is
        missing or cannot be parsed/structured, replace it with a safe default
        store and return that default. Raises IOError for filesystem errors.
        """
        if not os.path.exists(self.path):
            default = self._default_store()
            self.save_store(default)
            return default

        try:
            store = self.load_store()
            # load_store returns a deserialized store or raises on parse/structure
            return store
        except (ParseError, StructureError, json.JSONDecodeError, ValueError):
            # Recoverable: replace corrupted file with default store.
            default = self._default_store()
            try:
                self.save_store(default)
            except OSError as exc:
                # Unrecoverable filesystem error while trying to repair
                raise
            return default
        except OSError:
            # Propagate IOErrors (permission issues, etc.)
            raise

    def load_store(self) -> ExpenseStore:
        """
        Read the current store from disk and deserialize using serializer.
        Raises ParseError/StructureError as raised by serializer or IOError for
        filesystem errors.
        """
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = f.read()
        except OSError:
            raise

        try:
            # Delegate structural parsing to the serializer. It may raise
            # ParseError/StructureError (or other exceptions) which we propagate.
            store = self.serializer.deserialize(raw)
        except json.JSONDecodeError as e:
            # Normalize JSON errors to ParseError for callers that expect it.
            raise ParseError(str(e))
        except Exception:
            # Allow serializer-specific exceptions (StructureError, etc.) to
            # propagate; wrap unknown exceptions conservatively as StructureError.
            raise

        return store

    def save_store(self, store: ExpenseStore) -> None:
        """
        Serialize the provided store and persist it atomically using the
        injected AtomicFileWriter. Raises IOError on filesystem failures.
        """
        try:
            text = self.serializer.serialize(store)
        except Exception:
            # If serialization fails it's a programming/structure issue upstream.
            raise

        try:
            self.writer.atomic_write(self.path, text)
        except OSError:
            # Propagate as IOError to callers.
            raise

    def perform_transaction(self, modifier: Callable[[ExpenseStore], ExpenseStore]) -> ExpenseStore:
        """
        Read-modify-write primitive. Loads current store, calls modifier to
        produce a new store, validates basic structural integrity, saves
        atomically, and returns the saved store.

        Errors:
        - ValidationError if resulting store violates repository-level structural
          invariants (top-level shape, expenses array, unique non-negative ids).
        - IOError (OSError) for filesystem write/read failures.
        """
        # Load current store (propagate any IO/parse errors to caller).
        store = self.load_store()

        # Apply modifier to obtain new store.
        new_store = modifier(store)

        # Basic structure validation performed by repository: ensure top-level
        # object with keys 'expenses' and 'settings', expenses is a list, and
        # settings is a dict. Also ensure ids are present, integers, non-negative
        # and unique. Domain-level validation (dates, amounts, categories) is
        # the responsibility of the service/validator.
        self._validate_structure(new_store)

        # Persist atomically.
        self.save_store(new_store)

        return new_store

    # --- Helper / validation methods ---

    def _default_store(self) -> ExpenseStore:
        # Use manifest default currency if not injected (PLN). In a complete
        # app this would come from Config; repository takes only path,
        # serializer and writer per the manifest.
        return {"expenses": [], "settings": {"currency": "PLN"}}

    def _validate_structure(self, store: Any) -> None:
        if not isinstance(store, dict):
            raise StructureError("Store must be a JSON object (dict)")

        # Required top-level keys
        if "expenses" not in store or "settings" not in store:
            raise StructureError("Store must contain 'expenses' and 'settings' keys")

        expenses = store.get("expenses")
        settings = store.get("settings")

        if not isinstance(expenses, list):
            raise StructureError("'expenses' must be an array")
        if not isinstance(settings, dict):
            raise StructureError("'settings' must be an object")

        seen_ids = set()
        for idx, item in enumerate(expenses):
            if not isinstance(item, dict):
                raise StructureError(f"expense at index {idx} is not an object")
            # id must exist and be an int
            if "id" not in item:
                raise StructureError(f"expense at index {idx} missing 'id'")
            eid = item.get("id")
            if not isinstance(eid, int):
                raise StructureError(f"expense id at index {idx} must be integer")
            if eid < 0:
                raise StructureError(f"expense id at index {idx} must be non-negative")
            if eid in seen_ids:
                raise StructureError(f"duplicate expense id found: {eid}")
            seen_ids.add(eid)

        # settings minimal check: must contain 'currency' key with string value
        if "currency" not in settings:
            raise StructureError("'settings' must contain 'currency'")
        if not isinstance(settings.get("currency"), str):
            raise StructureError("'settings.currency' must be a string")

