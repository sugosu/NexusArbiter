# core/actions/base_action.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ActionContext:

    project_root: str
    target_file: Optional[str]
    run_name: str
    run_item: Any
    logger: Any

    # Control-flow flags
    should_continue: bool = False
    should_break: bool = False

    # Strategy-change flags
    change_strategy_requested: bool = False
    change_strategy_reason: Optional[str] = None

    # Optional extended context (not required for the IO logging feature)
    attempt_number: int = 1
    log_io_settings: Optional[Dict[str, Any]] = None


class BaseAction:
    """
    Base class for all actions inside aiAgency.
    Subclasses implement `execute(self, ctx, params)`.
    """

    action_type: str = ""

    def execute(self, ctx: ActionContext, params: Dict[str, Any]) -> None:
        raise NotImplementedError(
            f"{self.__class__.__name__}.execute() not implemented"
        )
