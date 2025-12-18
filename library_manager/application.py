from services.library_service import LibraryService
from adapters.console import ConsolePrinter
from typing import Dict, Any

class Application:
    def __init__(self, library_service: LibraryService, console_printer: ConsolePrinter) -> None:
        self._library_service = library_service
        self._console_printer = console_printer

    def run(self, storage_path: str) -> None:
        summary: Dict[str, Any] = self._library_service.run_operations(storage_path)
        self._console_printer.print_summary(summary)
