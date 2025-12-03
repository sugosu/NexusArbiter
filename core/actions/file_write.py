# core/actions/file_write.py
from __future__ import annotations

from .base_action import BaseAction, ActionContext
from .registry import ActionRegistry


class FileWriteAction(BaseAction):

    action_type = "file_write"

    def validate(self) -> bool:
        code = self.params.get("code")
        return isinstance(code, str)

    def execute(self, ctx: ActionContext) -> None:
        if not self.validate():
            ctx.logger.warning("[file_write] Invalid params: %r", self.params)
            return

        # Path suggested by the agent (may be overridden by engine)
        agent_path: str = self.params.get("target_path", "") or ""

        # Engine source of truth (ActionRuntimeContext adds target_file)
        effective_path = getattr(ctx, "target_file", None) or agent_path
        if not effective_path:
            ctx.logger.error(
                "[file_write] No effective target path: "
                "ctx.target_file and params.target_path are both empty"
            )
            return

        code: str = self.params["code"]
        # Optional, currently unused but kept for future debugging/commits
        _context_text = self.params.get("context", "")

        ctx.logger.info(
            "[file_write] Writing file '%s' "
            "(ctx.target_file=%r, agent_path=%r)",
            effective_path,
            getattr(ctx, "target_file", None),
            agent_path,
        )
        written_path = ctx.file_writer.write_file(effective_path, code)
        ctx.logger.info("[file_write] File written at: %s", written_path)


# Register with the registry
ActionRegistry.register(FileWriteAction)
