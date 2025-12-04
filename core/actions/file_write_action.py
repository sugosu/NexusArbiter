from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from core.actions.base_action import BaseAction, ActionContext


class FileWriteAction(BaseAction):
    """
    Action type: 'file_write'

    Writes a full file to disk. The engine decides the final target path
    via ctx.target_file; if it's not set, we fall back to agent's target_path.
    """

    action_type = "file_write"

    def execute(self, ctx: ActionContext, params: Dict[str, Any]) -> None:
        code = params.get("code")
        if not isinstance(code, str):
            ctx.logger.error("[file_write] Missing or invalid 'code' param.")
            return

        # Engine source of truth
        effective_path: Optional[str] = ctx.target_file

        # Fallback to agent suggestion
        if not effective_path:
            effective_path = params.get("target_path")

        if not effective_path:
            ctx.logger.error(
                "[file_write] No target path: ctx.target_file and params.target_path are both empty."
            )
            return

        root = Path(ctx.project_root)
        full_path = (root / effective_path).resolve()

        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(code, encoding="utf-8")
            ctx.logger.info(f"[file_write] Wrote file: {full_path}")
        except Exception as e:
            ctx.logger.error(f"[file_write] Error writing file '{full_path}': {e}", exc_info=True)
            return

        # This action itself doesn’t change control-flow flags.
        ctx.should_continue = True
