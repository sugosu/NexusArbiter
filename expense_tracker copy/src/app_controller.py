from typing import Optional

from .config import Config
from .json_serializer import JsonSerializer
from .atomic_file_writer import AtomicFileWriter
from .expense_repository import ExpenseRepository
from .expense_validator import ExpenseValidator
from .expense_service import ExpenseService
from .models import ExpenseStore

import logging
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)


class AppController:
    """Startup orchestration and application state owner.

    This controller is responsible for constructing and wiring core components
    (Config, JsonSerializer, AtomicFileWriter, ExpenseRepository, ExpenseValidator,
    ExpenseService) when start() is called, initializing the persistent store,
    and managing the high-level application state transitions.

    The constructor accepts optional pre-constructed components to allow
    dependency injection for tests. If any component is missing, start() will
    construct the canonical implementation using the defaults specified in the
    system manifest.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        serializer: Optional[JsonSerializer] = None,
        writer: Optional[AtomicFileWriter] = None,
        repository: Optional[ExpenseRepository] = None,
        service: Optional[ExpenseService] = None,
    ) -> None:
        self.config: Optional[Config] = config
        self.serializer: Optional[JsonSerializer] = serializer
        self.writer: Optional[AtomicFileWriter] = writer
        self.repository: Optional[ExpenseRepository] = repository
        self.service: Optional[ExpenseService] = service
        # Initialize state to INIT; will be transitioned in start().
        self.state: ServiceState = ServiceState.INIT

    def start(self) -> None:
        """Perform wiring and initialize the persistent store.

        Wiring sequence (constructed in order):
          - Config
          - JsonSerializer
          - AtomicFileWriter
          - ExpenseRepository
          - ExpenseValidator
          - ExpenseService

        After wiring, attempt repository.initialize_store().
        On success: state -> READY. On unrecoverable IO errors: state -> ERROR and
        the exception is propagated.
        """
        logger.info("AppController.start: beginning startup sequence")
        # If a component was not injected, construct it using canonical defaults
        try:
            if self.config is None:
                # Deterministic defaults taken from manifest/runtime init params.
                self.config = Config(
                    store_path="data/expenses.json",
                    temp_suffix=".tmp",
                    allowed_categories=["food", "transport", "utilities", "entertainment", "health", "other"],
                    default_currency="PLN",
                    description_max_length=1024,
                    json_indent=2,
                    serializer_field_order={
                        "store": ["expenses", "settings"],
                        "expense": ["id", "date", "amount", "category", "description"],
                        "settings": ["currency"],
                    },
                )
                logger.debug("Config constructed with store_path=%s", self.config.store_path)

            if self.serializer is None:
                # JsonSerializer expects field_order and indent
                self.serializer = JsonSerializer(field_order=self.config.serializer_field_order, indent=self.config.json_indent)
                logger.debug("JsonSerializer constructed with indent=%s", self.config.json_indent)

            if self.writer is None:
                # AtomicFileWriter expects durability flag and temp suffix
                self.writer = AtomicFileWriter(fsync_after_write=True, temp_suffix=self.config.temp_suffix)
                logger.debug("AtomicFileWriter constructed with temp_suffix=%s", self.config.temp_suffix)

            if self.repository is None:
                # ExpenseRepository expects config, serializer, writer
                self.repository = ExpenseRepository(config=self.config, serializer=self.serializer, writer=self.writer)
                logger.debug("ExpenseRepository constructed for path=%s", self.config.store_path)

            # Validator is local to wiring; ExpenseService requires it.
            validator = ExpenseValidator(allowed_categories=self.config.allowed_categories, description_max_length=self.config.description_max_length)
            logger.debug("ExpenseValidator constructed with %d allowed categories", len(self.config.allowed_categories))

            if self.service is None:
                self.service = ExpenseService(repository=self.repository, validator=validator)
                logger.debug("ExpenseService constructed and bound to repository")

            # Try to initialize/repair the on-disk store. Repository handles recoverable parse/structure errors.
            logger.info("AppController.start: initializing persistent store at %s", self.config.store_path)
            # initialize_store may raise IOError for unrecoverable filesystem errors
            self.repository.initialize_store()

            # Successful initialization
            prev_state = self.state
            self.state = ServiceState.READY
            logger.info("State transition: %s -> %s", prev_state.name, self.state.name)

        except IOError:
            # Unrecoverable filesystem error should move application to ERROR state.
            prev_state = self.state
            self.state = ServiceState.ERROR
            logger.exception("AppController.start: unrecoverable IO error during initialization; state=%s", self.state.name)
            raise
        except Exception:
            # Any other unexpected exception: move to ERROR and re-raise after logging.
            prev_state = self.state
            self.state = ServiceState.ERROR
            logger.exception("AppController.start: unexpected error during initialization; state=%s", self.state.name)
            raise

    def shutdown(self) -> None:
        """Transition to SHUTDOWN state and perform any needed cleanup.

        There are no background writers or threads in the core design; this method
        ensures state is updated and logs the transition. If further resource
        cleanup is required by injected components, adapters or higher-level
        application code should perform it (this keeps shutdown deterministic
        and test-friendly).
        """
        prev_state = self.state
        self.state = ServiceState.SHUTDOWN
        logger.info("State transition: %s -> %s", prev_state.name, self.state.name)

    # Convenience accessors to expose constructed components to adapters/tests.
    def get_service(self) -> ExpenseService:
        if self.service is None:
            raise RuntimeError("AppController: service not initialized; call start() first")
        return self.service

    def get_repository(self) -> ExpenseRepository:
        if self.repository is None:
            raise RuntimeError("AppController: repository not initialized; call start() first")
        return self.repository

    def get_config(self) -> Config:
        if self.config is None:
            raise RuntimeError("AppController: config not initialized; call start() first")
        return self.config
