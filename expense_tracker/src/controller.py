import logging
from typing import Optional

# Import application components described in the manifest.
# These modules are expected to exist in the project and provide the
# concrete implementations described in the manifest/implementation story.
from config import Config
from serializer import JsonSerializer
from atomic_writer import AtomicFileWriter
from repository import ExpenseRepository
from validator import ExpenseValidator
from service import ExpenseService
from models import AppState


class AppController:
    """Composition root and lifecycle controller for the ExpenseTracker application.

    Responsibilities:
    - Construct configuration and concrete components (serializer, writer, repository,
      validator, service) following the composition order in the manifest.
    - Initialize the persistent store via repository.initialize_store().
    - Own application lifecycle state and transitions: INIT -> READY | ERROR, READY -> SHUTDOWN.

    Design notes / extension points:
    - Optional constructor injection of components is supported to allow test doubles
      or alternate implementations to be provided by adapters/plugins. When a component
      is not provided, AppController will construct the default from Config and manifest rules.
    - start() performs repository initialization and sets state accordingly.
    - shutdown() transitions to SHUTDOWN. This implementation assumes single-threaded
      execution (no background writes) as per system assumptions.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        serializer: Optional[JsonSerializer] = None,
        writer: Optional[AtomicFileWriter] = None,
        repository: Optional[ExpenseRepository] = None,
        validator: Optional[ExpenseValidator] = None,
        service: Optional[ExpenseService] = None,
    ) -> None:
        # Use module-level logger for structured logging.
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initial (pre-start) state is INIT.
        # AppState enum is expected to provide INIT, READY, ERROR, SHUTDOWN.
        self.state: AppState = AppState.INIT

        # Allow injection for testing/extensibility. Construct missing components
        # following the manifest's instantiation order.
        self.config: Config = config or Config()

        # Serializer: deterministic field order + indent
        self.serializer: JsonSerializer = (
            serializer or JsonSerializer(field_order=self.config.serializer_field_order, indent=self.config.json_indent)
        )

        # Atomic writer: ensures atomic writes with fsync option
        self.writer: AtomicFileWriter = (
            writer or AtomicFileWriter(temp_suffix=self.config.temp_suffix, fsync_after_write=self.config.fsync_after_write)
        )

        # Repository: single place for filesystem IO
        self.repository: ExpenseRepository = repository or ExpenseRepository(self.config, self.serializer, self.writer)

        # Validator: domain input validation
        self.validator: ExpenseValidator = (
            validator or ExpenseValidator(self.config.allowed_categories, self.config.description_max_length)
        )

        # Service: business operations that use repository + validator
        self.service: ExpenseService = service or ExpenseService(self.repository, self.validator)

    def start(self) -> None:
        """Perform startup composition and repository initialization.

        On success transitions state to READY. On unrecoverable filesystem errors
        transitions state to ERROR and raises InitializationError.
        Recoverable parse/structure errors are expected to be handled by
        ExpenseRepository.initialize_store() (it may repair and write a default store).
        """
        self.logger.debug("Starting AppController: entering INIT state")
        self.state = AppState.INIT

        try:
            self.logger.info("Initializing persistent store at path: %s", self.config.store_path)
            store = self.repository.initialize_store()
            # repository.initialize_store is expected to return the ExpenseStore object
            # and to perform repairs when appropriate. We don't inspect store here.
            self.state = AppState.READY
            self.logger.info("Initialization successful; application state set to READY")
        except Exception as exc:
            # Any other unexpected exception: transition to ERROR and propagate
            self.state = AppState.ERROR
            self.logger.exception("Unexpected error during initialization: %s", exc)
            raise

    def shutdown(self) -> None:
        """Perform a graceful shutdown transition.

        This implementation assumes synchronous single-threaded operations.
        If extension points introduce asynchronous writes, callers should ensure
        those complete before invoking shutdown.
        """
        if self.state == AppState.SHUTDOWN:
            self.logger.debug("shutdown() called but application already in SHUTDOWN state")
            return

        prev = self.state
        self.state = AppState.SHUTDOWN
        self.logger.info("Application state transition: %s -> SHUTDOWN", prev)
        # No extra resource cleanup required here; concrete components are
        # expected to manage their own resources. Keep shutdown idempotent.
        return
