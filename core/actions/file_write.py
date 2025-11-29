# core/actions/file_write.py
from pathlib import Path
from .base_action import BaseAction, ActionContext
from .registry import ActionRegistry


class FileWriteAction(BaseAction):
    action_type = "file_write"

    def validate(self) -> bool:
        code = self.params.get("code")
        return isinstance(code, str)

    def execute(self, ctx: ActionContext) -> None:
        if not self.validate():
            ctx.logger.warning(f"[file_write] Invalid params: {self.params!r}")
            return

        agent_path: str = self.params.get("target_path", "") or ""

        # Engine source of truth
        effective_path = getattr(ctx, "target_file", None) or agent_path
        if not effective_path:
            ctx.logger.error(
                "[file_write] No effective target path: "
                "ctx.target_file and params.target_path are both empty"
            )
            return

        code: str = self.params["code"]
        _context_text = self.params.get("context", "")

        ctx.logger.info(
            f"[file_write] Writing file '{effective_path}' "
            f"(ctx.target_file={getattr(ctx, 'target_file', None)!r}, "
            f"agent_path={agent_path!r})"
        )
        written_path = ctx.file_writer.write_file(effective_path, code)
        ctx.logger.info(f"[file_write] File written at: {written_path}")


# Register with the registry
ActionRegistry.register(FileWriteAction)
