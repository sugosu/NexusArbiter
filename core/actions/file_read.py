# core/actions/file_read.py
from pathlib import Path
from .base_action import BaseAction, ActionContext
from .registry import ActionRegistry


class FileReadAction(BaseAction):
    """
    Action that reads a file under project_root and logs that it was read.

    Expected params:
      - target_path: str (relative to project root)

    NOTE: At the moment this only logs; the pipeline doesn't surface
    the file content back to the model in the same run.
    """

    action_type = "file_read"

    def validate(self) -> bool:
        target_path = self.params.get("target_path")
        return isinstance(target_path, str) and bool(target_path)

    def execute(self, ctx: ActionContext) -> None:
        if not self.validate():
            ctx.logger.warning(f"[file_read] Invalid params: {self.params!r}")
            return

        target_path: str = self.params["target_path"]
        full_path = Path(ctx.project_root) / target_path

        reader = PythonFileReader(str(full_path))
        content = reader.read_file()

        ctx.logger.info(
            f"[file_read] Read file '{full_path}' "
            f"({len(content)} characters)"
        )

# Register
ActionRegistry.register(FileReadAction)
