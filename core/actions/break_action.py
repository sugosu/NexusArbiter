# core/actions/break_action.py
from __future__ import annotations

from typing import Optional

from .base_action import BaseAction, ActionContext
from .registry import ActionRegistry


class BreakAction(BaseAction):
    """
    Logical early-termination of action processing.

    Expected params:
        - reason: Optional[str]   – explanation for logs
    """

    action_type = "break"

    def validate(self) -> bool:
        reason = self.params.get("reason")
        if reason is not None and not isinstance(reason, str):
            return False
        return True

    def execute(self, ctx: ActionContext) -> None:
        reason: Optional[str] = self.params.get("reason") or "No reason provided."
        logger = getattr(ctx, "logger", None)
        if logger is not None:
            logger.info("[break] Breaking remaining actions: %s", reason)
        # The execute_actions loop handles actually stopping further actions.


# Register with the registry on import
ActionRegistry.register(BreakAction)
