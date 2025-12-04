from __future__ import annotations
from typing import Any, Dict

from core.actions.base_action import BaseAction, ActionContext


class ChangeStrategyAction(BaseAction):
    """
    Signals the engine to switch to the next strategy attempt for a specific
    code generation block.

    The validator profile triggers this action. The engine then:
        - reads validator.run_item.strategy_file
        - reads validator.run_item.strategy_index
        - reads validator.run_item.target_run
        - increments internal retry counters
        - re-runs the target code generation run with the next attempt
    """

    action_type = "change_strategy"

    def execute(self, ctx: ActionContext, params: Dict[str, Any]) -> None:
        reason = params.get("reason")

        ctx.change_strategy_requested = True
        ctx.change_strategy_reason = reason
        ctx.should_continue = False
        ctx.should_break = False

        ctx.logger.info(
            f"[change_strategy] Validator requested strategy change "
            f"(run='{ctx.run_name}', reason={reason!r})"
        )
