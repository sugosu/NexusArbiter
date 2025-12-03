# core/actions/file_read.py
from __future__ import annotations

from pathlib import Path

from .base_action import BaseAction, ActionContext
from .registry import ActionRegistry


class FileReadAction(BaseAction):
    """
    Safely reads a text file from the project root and pushes the content
    into the ActionContext's results.

    Expected params:
        - path: str            (preferred)
          or
        - target_path: str     (fallback; same semantics)

    This is primarily useful for higher-level agents that need to inspect
    existing files without re-sending them as context from the host.
    """

    action_type = "file_read"

    def _get_relative_path(self) -> str | None:
        path = self.params.get("path") or self.params.get("target_path")
        if not isinstance(path, str) or not path.strip():
            return None
        return path.strip()

    def validate(self) -> bool:
        rel = self._get_relative_path()
        return rel is not None

    def execute(self, ctx: ActionContext) -> None:
        rel = self._get_relative_path()
        if not rel:
            ctx.logger.warning("[file_read] Missing or invalid 'path'/'target_path'.")
            return

        project_root = Path(ctx.project_root).resolve()
        full_path = (project_root / rel).resolve()

        try:
            # Security: do not allow escaping the project root
            if not full_path.is_relative_to(project_root):
                ctx.logger.error(
                    "[file_read] Refusing to read outside project root: %s", full_path
                )
                return
        except AttributeError:
            # For very old Python, fall back to a manual check (should not be needed in 3.10+)
            if project_root not in full_path.parents and full_path != project_root:
                ctx.logger.error(
                    "[file_read] Refusing to read outside project root: %s", full_path
                )
                return

        if not full_path.exists() or not full_path.is_file():
            ctx.logger.warning("[file_read] File not found or not a file: %s", full_path)
            return

        try:
            content = full_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            ctx.logger.warning("[file_read] File is not valid UTF-8 text: %s", full_path)
            return

        ctx.logger.info("[file_read] Read file: %s", full_path)
        # Make the content available to callers that inspect ctx.results
        ctx.add_result(content)


# Register
ActionRegistry.register(FileReadAction)
