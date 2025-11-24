# === CONTEXT START ===
# Class that scans a base directory and builds a universal file index for all
# files, excluding only files named .gitignore.
# === CONTEXT END ===

from pathlib import Path
from typing import Union, Dict, Any

class FileIndexGenerator:
    def __init__(self, base_directory: Union[str, Path]):
        self.base_directory = Path(base_directory)

    def build_index(self) -> Dict[str, Any]:
        if not self.base_directory.exists():
            return {"files": []}

        files = []
        for file in self.base_directory.rglob('*'):
            if file.is_file() and file.name != '.gitignore':
                try:
                    files.append({
                        "name": file.name,
                        "relative_path": str(file.relative_to(self.base_directory)),
                        "absolute_path": str(file.resolve()),
                        "extension": file.suffix,
                        "size": file.stat().st_size
                    })
                except (OSError, PermissionError):
                    continue

        files.sort(key=lambda x: x["relative_path"])
        return {"files": files}
