# === CONTEXT START ===
# Added logging to the ClassGenerator class using BasicLogger. A logger instance
# is created in the __init__ method, and an info log is added in the generate
# method to log when a file is being generated.
# === CONTEXT END ===

# === CONTEXT START ===
# The ClassGenerator class is responsible for writing Python source code to disk
# and ensuring that generated files are saved in a clean, structured, and
# predictable way. It serves as the main output layer of the AI-driven
# code-generation pipeline, receiving raw code strings from the model and
# converting them into .py files located within the configured project
# directory.
#
# The class provides two modes of operation: a basic file-generation method that
# writes code exactly as received, and an enhanced method that automatically
# prefixes the file with a formatted CONTEXT block. This comment block embeds
# human-readable metadata or explanation produced by the AI, wrapped to 80
# characters for readability and delimited with START and END markers. This
# allows each generated file to carry its own reasoning, intent, or description,
# which becomes valuable for future maintenance, refactoring, and tracing logic.
#
# To maintain portability and prevent unexpected filesystem errors, the class
# guarantees that the target output directory is created on initialization. It
# performs no interpretation of the code itself; its sole responsibility is to
# accurately persist the given content to the filesystem in a clean and
# repeatable manner, forming the foundation for downstream processes such as Git
# commits or subsequent model iterations.
# === CONTEXT END ===

import os
import textwrap
from typing import Optional
from core.logger import BasicLogger

class ClassGenerator:
    """
    Generates a .py file from a provided string at the specified path.
    """

    def __init__(self, base_path: str):
        """
        Initialize the file generator with the base path for output.
        :param base_path: Directory where the .py file will be created.
        """
        self.logger = BasicLogger(self.__class__.__name__).get_logger()
        self.base_path = os.path.abspath(base_path)
        os.makedirs(self.base_path, exist_ok=True)

    def _build_comment_block(self, comments: str) -> str:
        """
        Build a readable, wrapped, multi-line Python comment block.
        Long lines are wrapped at ~80 characters for readability.
        """
        if not comments or not comments.strip():
            return ""

        # Wrap long text into multiple lines (80 chars per line)
        wrapped = textwrap.fill(comments.strip(), width=80)
        lines = wrapped.split("\n")

        header = ["# === CONTEXT START ==="]
        header.extend(f"# {line}" for line in lines)
        header.append("# === CONTEXT END ===")
        header.append("")  # blank line after the block

        return "\n".join(header)

    def generate(self, filename: str, content: str) -> str:
        """
        Writes the given string content to a .py file in the base path.
        :param filename: Name of the file (without .py extension).
        :param content: Python source code to write.
        :return: Full path of the generated file.
        """
        self.logger.info(f"Generating file: {filename}")
        if not filename.endswith(".py"):
            filename = f"{filename}.py"

        full_path = os.path.join(self.base_path, filename)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        return full_path

    def generate_with_comments(self, filename: str, content: str, comments: Optional[str] = None) -> str:
        """
        Writes the given content to a .py file, optionally prefixed with a
        formatted comment block built from the provided comments string.
        """
        if comments:
            comment_block = self._build_comment_block(comments)
            content = f"{comment_block}\n{content}"

        return self.generate(filename, content)
