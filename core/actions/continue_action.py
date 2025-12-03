# core/actions/continue_action.py
from __future__ import annotations

from .base_action import BaseAction, ActionContext
from .registry import ActionRegistry


class ContinueAction(BaseAction):
    """
    A no-op action indicating that the agent wants to keep iterating
    without final side effects.

    In the orchestration layer, a *single* 'continue' action is already
    treated specially and short-circuits without executing any actions.
    This class exists for completeness and future-proofing in case
    'continue' ever appears in a mixed action list.
    """

    action_type = "continue"

    def validate(self) -> bool:
        # We deliberately do NOT require any params. If the agent sends
        # something, we just ignore it.
        return True

    def execute(self, ctx: ActionContext) -> None:
        logger = getattr(ctx, "logger", None)
        if logger is not None:
            logger.info("[continue] No-op action executed; nothing to do.")


# Register
ActionRegistry.register(ContinueAction)
