import os
import logging
from typing import Callable

from models import ExpenseStore, Settings
import errors

# ExpenseRepository: responsible for all filesystem interactions for the ExpenseStore.
# - Loads and deserializes store using provided serializer
# - Repairs missing/corrupt stores to a safe default on initialize_store()
# - Persists stores atomically using provided writer
# Notes: If other modules are missing in the runtime, tests wiring should provide them.

logger = logging.getLogger(__name__)


class ExpenseRepository:
    """Repository that encapsulates filesystem access for the single-file ExpenseStore.

    Constructor requires a config-like object exposing `store_path` and `default_currency`,
    a serializer implementing serialize/deserialize, and an atomic writer implementing
    atomic_write(path, content).
    """

    def __init__(self, config, serializer, writer) -> None:
        self._config = config
        self._path: str = config.store_path
        self._serializer = serializer
        self._writer = writer

    def initialize_store(self) -> ExpenseStore:
        """Ensure the store file exists and is structurally valid.

        If the file is missing, create a default safe store and persist it.
        If the file exists but is syntactically invalid or structurally mismatched,
        replace it with the default safe store and return that.

        Raises IOError for unrecoverable filesystem errors.
        """
        try:
            if not os.path.exists(self._path):
                logger.info("Store file missing: creating default store at %s", self._path)
                default = self._default_store()
                self.save_store(default)
                logger.info("Default store written to %s", self._path)
                return default

            # File exists: attempt to read and deserialize
            try:
                store = self.load_store()
                return store
            except (errors.ParseError, errors.StructureError) as e:
                # Recoverable on startup: replace with default
                logger.warning("Store at %s is invalid (%s). Replacing with default store.", self._path, e)
                default = self._default_store()
                self.save_store(default)
                logger.info("Repaired store written to %s", self._path)
                return default

        except OSError as e:
            logger.error("Filesystem error during initialize_store for %s: %s", self._path, e)
            # Propagate as IO error
            raise

    def load_store(self) -> ExpenseStore:
        """Read the persistent store from disk and deserialize it.

        Returns the ExpenseStore on success.
        Raises errors.ParseError / errors.StructureError for invalid content,
        or OSError for I/O errors.
        """
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                raw = f.read()
        except OSError:
            # Propagate to caller
            logger.exception("Failed to open store file for reading: %s", self._path)
            raise

        # Delegate parsing/structure checks to serializer
        store = self._serializer.deserialize(raw)
        return store

    def save_store(self, store: ExpenseStore) -> None:
        """Serialize the provided store and atomically replace the persistent file.

        Raises OSError on filesystem failures propagated from atomic writer.
        """
        # Serialize first to ensure the store is structurally serializable
        content = self._serializer.serialize(store)

        # Ensure parent directory exists
        self._ensure_parent_dir()

        try:
            self._writer.atomic_write(self._path, content)
            logger.info("Atomic write successful to %s", self._path)
        except OSError:
            logger.exception("Atomic write failed for %s", self._path)
            raise

    def perform_transaction(self, modifier: Callable[[ExpenseStore], ExpenseStore]) -> ExpenseStore:
        """Read-modify-write primitive.

        Loads the current store, calls modifier(store) to obtain a new store,
        performs a structural check by attempting to serialize the result, then
        atomically writes it and returns the saved store.

        Errors from modifier propagate. Raises errors.ValidationError if the
        modifier result cannot be serialized/has invalid structure as detected
        by the serializer. Raises OSError for filesystem failures.
        """
        # Load current store (may raise ParseError/StructureError/OSError to caller)
        current = self.load_store()

        # Call modifier to obtain new store. Modifier is expected to be a pure function.
        new_store = modifier(current)

        # Structural validation: attempt to serialize (serializer may raise StructureError)
        try:
            # serializer.serialize may raise StructureError if shape is not as expected
            _ = self._serializer.serialize(new_store)
        except errors.StructureError as e:
            logger.warning("Transaction produced structurally invalid store: %s", e)
            # Wrap or re-raise as ValidationError per contract
            raise errors.ValidationError(f"modifier returned structurally invalid store: {e}")

        # Persist atomically
        self.save_store(new_store)
        return new_store

    def _default_store(self) -> ExpenseStore:
        """Construct the canonical default safe ExpenseStore.

        Default: expenses = [], settings = { currency: config.default_currency }
        """
        settings = Settings(currency=self._config.default_currency)
        return ExpenseStore(expenses=[], settings=settings)

    def _ensure_parent_dir(self) -> None:
        dirpath = os.path.dirname(self._path)
        if not dirpath:
            return
        try:
            os.makedirs(dirpath, exist_ok=True)
        except OSError:
            logger.exception("Failed to ensure parent directory exists: %s", dirpath)
            raise
