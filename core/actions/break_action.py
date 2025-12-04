from __future__ import annotations

from typing import Any, Dict, Optional

from core.actions.base_action import BaseAction, ActionContext


class BreakAction(BaseAction):
    """
    Action type: 'break'

    Logical early termination of the pipeline.
    """

    action_type = "break"

    def execute(self, ctx: ActionContext, params: Dict[str, Any]) -> None:
        reason: Optional[str] = params.get("reason")
        ctx.should_break = True
        ctx.should_continue = False

        ctx.logger.info(f"[break] Pipeline break requested. Reason={reason!r}")
