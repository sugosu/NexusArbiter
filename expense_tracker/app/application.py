from typing import Dict, Any

from controllers.controller import CommandController
from app_logging import AppLogger


class Application:
    """Application orchestration boundary.

    Responsibilities:
    - Hold injected controller, logger, and data_dir configuration.
    - Forward commands to the controller and return controller results.

    Constructor and public API are defined by the manifest and must not perform I/O.
    """

    def __init__(self, controller: CommandController, logger: AppLogger, data_dir: str) -> None:
        """Initialize the Application with its dependencies.

        Args:
            controller: CommandController used to handle incoming commands.
            logger: AppLogger for structured logging.
            data_dir: Path to the data directory (ownership remains with caller/application).
        """
        # Dependency injection assignments; do not perform I/O here.
        self._controller: CommandController = controller
        self._logger: AppLogger = logger
        self._data_dir: str = data_dir

    def run(self, command: Dict[str, Any], data_dir: str) -> Dict[str, Any]:
        """Run a high-level command by delegating to the controller.

        This method logs high-level dispatch information, does not mutate the
        provided data_dir, and forwards both the command and data_dir to the
        controller.handle(...) method. The controller result is returned as-is.

        Args:
            command: A command dict following the shared command contract.
            data_dir: The data directory to forward to downstream components.

        Returns:
            The result produced by the controller (dict).
        """
        # Log a concise, high-level dispatch message. Include entity/action if present
        # but do not attempt deep parsing here (controller owns validation/routing).
        try:
            entity = command.get("entity") if isinstance(command, dict) else None
            action = command.get("action") if isinstance(command, dict) else None
        except Exception:
            entity = None
            action = None

        self._logger.info("Application dispatching command", {"entity": entity, "action": action})

        # Forward to the controller and return its result. Do not mutate data_dir.
        result = self._controller.handle(command, data_dir)
        return result
