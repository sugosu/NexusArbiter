from __future__ import annotations

from typing import Any, Dict

from core.actions.base_action import BaseAction, ActionContext


class ContinueAction(BaseAction):
    """
    Action type: 'continue'

    Signals that the pipeline should continue. The agent may optionally
    set should_break = true, but in your validator profiles you’ll use
    should_break = false.
    """

    action_type = "continue"

    def execute(self, ctx: ActionContext, params: Dict[str, Any]) -> None:
        should_break = bool(params.get("should_break", False))
        reason = params.get("reason")

        ctx.should_continue = True
        ctx.should_break = should_break

        ctx.logger.info(
            f"[continue] should_break={should_break}, reason={reason!r}"
        )
