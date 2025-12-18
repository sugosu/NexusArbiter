from application import Application
from adapters.console import ConsolePrinter

class Main:
    def __init__(self, application: Application, console_printer: ConsolePrinter) -> None:
        self._application = application
        self._console_printer = console_printer

    def start(self, storage_path: str) -> None:
        self._console_printer.print_info(f"Starting application with storage_path={storage_path}")
        try:
            self._application.run(storage_path)
        except Exception as e:
            self._console_printer.print_error(f"Fatal error: {e}")
        return None
