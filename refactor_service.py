# === CONTEXT START ===
# Added logging to the RefactorService class using BasicLogger. A logger instance
# is created in the __init__ method, and an info log is added in the
# build_messages method to indicate when message building starts.
# === CONTEXT END ===

from core.files.class_reader import PythonFileReader
from core.logger import BasicLogger

class RefactorService:
    """
    Prepares refactor messages for the model by injecting file content
    and optional class name hints into a clean, deterministic message structure.
    """

    def __init__(self, file_path: str, class_name: str | None = None):
        self.logger = BasicLogger(self.__class__.__name__).get_logger()
        self.file_path = file_path
        self.class_name = class_name

    def build_messages(self) -> list[dict]:
        self.logger.info('Building messages for refactoring')
        reader = PythonFileReader(self.file_path)
        content = reader.read_file()

        class_hint = (
            f"\nFocus on improving the class named `{self.class_name}`.\n"
            if self.class_name else ""
        )

        system_msg = {
            "role": "system",
            "content": (
                "You are a senior Python engineer. Refactor the provided code into a "
                "clean, maintainable, readable, idiomatic form. Preserve external "
                "behavior and public API. Do not add comments explaining changes."
            )
        }

        user_msg = {
            "role": "user",
            "content": (
                f"Refactor the following file.{class_hint}\n"
                "Return ONLY the final refactored Python code.\n\n"
                "```python\n"
                f"{content}\n"
                "```"
            )
        }

        return [system_msg, user_msg]
