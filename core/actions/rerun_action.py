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

class RerunAction(BaseAction):
    action_type = "rerun"

    def execute(self, ctx: ActionContext, params: Optional[Dict[str, Any]] = None) -> None:
        params = params or {}

        reason = params.get("reason", "No reason provided")
        ctx.change_strategy_reason = reason

        # Existing: optional named block selection (keep if you want)
        ctx.change_strategy_name = params.get("name") or params.get("block") or params.get("label")

        # NEW: method selection (refiner/remake/etc.)
        method = params.get("method")
        if isinstance(method, str) and method.strip():
            ctx.change_strategy_method = method.strip()

        ctx.change_strategy_requested = True
        ctx.should_continue = False
        ctx.should_break = False
