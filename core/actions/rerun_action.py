from __future__ import annotations

from typing import Dict, Any, Optional

from core.actions.base_action import BaseAction, ActionContext


class RerunAction(BaseAction):
    """
    Action that requests rerunning a target run using the next
    strategy attempt defined in a rerun strategy file.

    Externally used with: type = "rerun".
    Internally it still uses the existing change_strategy_* flags,
    so the rest of the pipeline code does not need to change yet.
    """

    # This is what ActionRegistry looks for
    action_type = "rerun"

    def execute(self, ctx: ActionContext, params: Optional[Dict[str, Any]] = None) -> None:
        # Allow params to be None
        params = params or {}
        reason = params.get("reason", "No reason provided")

        # Re-use existing strategy-change flags so pipeline logic stays the same
        ctx.change_strategy_requested = True
        ctx.change_strategy_reason = reason

        # Rerun ends this run; pipeline decides what to do next
        ctx.should_continue = False
        ctx.should_break = False

        ctx.logger.info(f"[rerun] Rerun requested: {reason!r}")
