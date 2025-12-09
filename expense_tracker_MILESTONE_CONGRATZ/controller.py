import logging
from enum import Enum
from typing import Any, Optional


class AppState(Enum):
    INIT = "INIT"
    READY = "READY"
    ERROR = "ERROR"
    SHUTDOWN = "SHUTDOWN"


class AppController:
    """
    AppController is responsible for startup orchestration and lifecycle management.

    It constructs core components (Config, JsonSerializer, AtomicFileWriter, ExpenseRepository,
    ExpenseService) unless they are injected for testing. It drives repository.initialize_store()
    during start() and manages the application state machine.

    Reasonable defaults and deterministic behavior are assumed per the project manifest.
    """

    def __init__(
        self,
        config: Optional[Any] = None,
        serializer: Optional[Any] = None,
        writer: Optional[Any] = None,
        repository: Optional[Any] = None,
        service: Optional[Any] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        # Components may be injected for tests; otherwise they will be created in start().
        self.config: Optional[Any] = config
        self.serializer: Optional[Any] = serializer
        self.writer: Optional[Any] = writer
        self.repository: Optional[Any] = repository
        self.service: Optional[Any] = service
        self.state: AppState = AppState.INIT
        self.logger = logger or logging.getLogger(__name__)

    def start(self) -> None:
        """
        Initialize configuration and infrastructure components, ensure the JSON store exists
        and is structurally valid (repository.initialize_store handles repair if needed),
        instantiate the service layer, and transition to READY on success.

        On unrecoverable filesystem errors this method sets state to ERROR and re-raises the
        exception so callers (adapters) can handle termination.
        """
        if self.state == AppState.SHUTDOWN:
            raise RuntimeError("Cannot start: controller is already shutdown")

        self.state = AppState.INIT
        self.logger.debug("AppController.start: beginning initialization")

        # Import and construct Config if not injected
        try:
            if self.config is None:
                # Config may be a class or module providing defaults; try to instantiate otherwise use as-is
                from src.config import Config as _Config  # type: ignore

                try:
                    self.config = _Config()
                except Exception:
                    # If Config is a simple object/module, use it directly
                    self.config = _Config
                self.logger.debug("Loaded Config: %s", getattr(self.config, "store_path", "<unknown>"))

            # Construct JsonSerializer if not provided
            if self.serializer is None:
                from src.serializer import JsonSerializer as _JsonSerializer  # type: ignore

                field_order = getattr(self.config, "serializer_field_order", None)
                indent = getattr(self.config, "json_indent", None)
                # Prefer constructor with explicit args; fallback to default ctor
                try:
                    self.serializer = _JsonSerializer(field_order=field_order, indent=indent)
                except TypeError:
                    self.serializer = _JsonSerializer()
                self.logger.debug("JsonSerializer constructed")

            # Construct AtomicFileWriter if not provided
            if self.writer is None:
                from src.atomic_writer import AtomicFileWriter as _AtomicFileWriter  # type: ignore

                temp_suffix = getattr(self.config, "temp_suffix", ".tmp")
                try:
                    self.writer = _AtomicFileWriter(fsync_after_write=True, temp_suffix=temp_suffix)
                except TypeError:
                    self.writer = _AtomicFileWriter()
                self.logger.debug("AtomicFileWriter constructed for temp suffix '%s'", temp_suffix)

            # Construct ExpenseRepository if not provided
            if self.repository is None:
                from src.repository import ExpenseRepository as _ExpenseRepository  # type: ignore

                path = getattr(self.config, "store_path", "data/expenses.json")
                try:
                    self.repository = _ExpenseRepository(path=path, serializer=self.serializer, writer=self.writer)
                except TypeError:
                    # fallback: positional
                    self.repository = _ExpenseRepository(path, self.serializer, self.writer)
                self.logger.debug("ExpenseRepository constructed for path '%s'", path)

        except Exception as exc:
            # Failure to construct critical components is unrecoverable
            self.state = AppState.ERROR
            self.logger.error("Initialization failed while constructing components: %s", exc, exc_info=True)
            raise

        # Ensure the persistent store exists and is structurally valid; repository handles repair
        try:
            store = self.repository.initialize_store()
            # initialize_store may return the store object; log summary info
            expenses_count = len(getattr(store, "expenses", []) or [])
            self.logger.info("initialize_store completed: %d expenses present", expenses_count)

        except IOError as io_exc:
            # Unrecoverable filesystem error: transition to ERROR and re-raise
            self.state = AppState.ERROR
            self.logger.error("Filesystem error during initialize_store: %s", io_exc, exc_info=True)
            raise
        except Exception as exc:
            # Any other unexpected exception is treated as fatal here
            self.state = AppState.ERROR
            self.logger.error("Unexpected error during initialize_store: %s", exc, exc_info=True)
            raise

        # Instantiate ExpenseService (business layer). Some constructors expect only repository,
        # others may require additional parameters; try common forms.
        try:
            if self.service is None:
                from src.service import ExpenseService as _ExpenseService  # type: ignore

                try:
                    self.service = _ExpenseService(repository=self.repository)
                except TypeError:
                    try:
                        self.service = _ExpenseService(self.repository)
                    except Exception:
                        # As a last resort attempt parameterless constructor
                        self.service = _ExpenseService()
                self.logger.debug("ExpenseService constructed")

        except Exception as exc:
            # If service construction fails, transition to ERROR and raise
            self.state = AppState.ERROR
            self.logger.error("Failed to construct ExpenseService: %s", exc, exc_info=True)
            raise

        # All good: set controller state to READY
        self.state = AppState.READY
        self.logger.info("AppController transitioned to READY")

    def get_service(self) -> Any:
        """
        Return the ExpenseService instance for adapters. Only available in READY state.
        """
        if self.state != AppState.READY:
            raise RuntimeError(f"Service requested while controller not READY (state={self.state})")
        return self.service

    def shutdown(self) -> None:
        """
        Transition to SHUTDOWN and attempt to cleanly close resources if they expose a close() method.
        """
        if self.state == AppState.SHUTDOWN:
            self.logger.debug("shutdown called but controller already in SHUTDOWN")
            return

        prev_state = self.state
        self.state = AppState.SHUTDOWN
        self.logger.info("AppController transitioning from %s to SHUTDOWN", prev_state)

        # Attempt best-effort cleanup of known components
        for comp_name in ("service", "repository", "writer", "serializer"):
            comp = getattr(self, comp_name, None)
            if comp is None:
                continue
            close_fn = getattr(comp, "close", None)
            try:
                if callable(close_fn):
                    close_fn()
                    self.logger.debug("Closed component: %s", comp_name)
            except Exception:
                self.logger.warning("Error while closing component %s", comp_name, exc_info=True)

        # Drop references to large objects to aid GC in long-running environments
        self.service = None
        self.repository = None
        self.writer = None
        self.serializer = None
        self.logger.info("AppController shutdown complete")
