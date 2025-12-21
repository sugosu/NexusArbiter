from typing import Any
import json

from app.application import Application
from app_logging import AppLogger


class Main:
    """Entry-point orchestrator for the expense_tracker application.

    Responsibilities:
    - Hold injected Application and AppLogger instances.
    - Parse a single JSON command string into a dict and delegate handling to Application.run.

    Per manifest: constructor receives Application and AppLogger via constructor injection.
    """

    def __init__(self, application: Application, logger: AppLogger) -> None:
        """Initialize Main with required dependencies.

        Do only trivial assignments; do not perform I/O or business logic here.
        """
        self._application = application
        self._logger = logger

    def invoke(self, json_command: str, data_dir: str) -> dict:
        """Parse a JSON command string and delegate to the Application.

        Steps (as implemented):
        - Log startup and the received command via the injected AppLogger.
        - Parse json_command into a dict called `command` using json.loads.
          If parsing fails or the parsed value is not a dict, log an error and raise.
        - Call self._application.run(command, data_dir) and return its result.
        """
        # Log startup and received command
        try:
            # Use the logger's info method; include the raw command for diagnostics.
            # The second parameter is optional structured data per AppLogger contract.
            self._logger.info("Main.invoke: received json command", {"json_command": json_command})
        except Exception:
            # Keep logging best-effort non-fatal here; do not prevent parsing below if logging fails.
            pass

        # Parse JSON input conservatively
        try:
            command = json.loads(json_command)
        except Exception as exc:
            # Log parse error and re-raise to surface the failure to the caller
            try:
                self._logger.error("Main.invoke: failed to parse json_command", {"error": str(exc), "json_command": json_command})
            except Exception:
                pass
            raise

        # Ensure the parsed command is a mapping/dict as expected by downstream components
        if not isinstance(command, dict):
            try:
                self._logger.error("Main.invoke: parsed command is not a JSON object", {"parsed_type": type(command).__name__, "command": command})
            except Exception:
                pass
            raise ValueError("Parsed json_command must be a JSON object (mapping) representing the command")

        # Delegate to Application for handling; Application.run is expected to return a dict
        result = self._application.run(command, data_dir)
        return result
