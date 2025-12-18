from typing import Dict, Any
import logging


class ConsolePrinter:
    def __init__(self) -> None:
        self._logger: logging.Logger = logging.getLogger(__name__)

    def print_info(self, message: str) -> None:
        print(message)
        try:
            self._logger.info(message)
        except Exception:
            pass

    def print_error(self, message: str) -> None:
        print(f"ERROR: {message}")
        try:
            self._logger.error(message)
        except Exception:
            pass

    def print_summary(self, summary: Dict[str, Any]) -> None:
        if isinstance(summary, dict) and "created_loans" in summary and isinstance(summary["created_loans"], list):
            print(f"Created loans: {len(summary['created_loans'])}")
        else:
            if isinstance(summary, dict):
                for key, value in summary.items():
                    if isinstance(value, list):
                        print(f"{key}: {len(value)}")
                    else:
                        print(f"{key}: {value}")
            else:
                print(summary)
        try:
            self._logger.info("Summary printed")
        except Exception:
            pass
