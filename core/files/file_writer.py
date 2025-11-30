# core/files/file_writer.py

from pathlib import Path
from core.logger import BasicLogger


class FileWriter:
    """
    Minimal primitive for writing text files under the project root.
    It takes a target_path (relative to project_root) and the full file content.
    """

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.logger = BasicLogger(self.__class__.__name__).get_logger()

    def write_file(self, target_path: str, content: str) -> Path:
        rel_path = Path(target_path)
        full_path = (self.project_root / rel_path).resolve()
        
        if not full_path.is_relative_to(self.project_root.resolve()):
            raise ValueError(f"Security Alert: Attempted to write outside project root: {full_path}")

        full_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"[FileWriter] Writing file: {full_path}")

        with full_path.open("w", encoding="utf-8") as f:
            f.write(content)

        return full_path
