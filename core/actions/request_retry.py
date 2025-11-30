# core/actions/request_retry.py
from typing import Optional

from .base_action import BaseAction, ActionContext
from .registry import ActionRegistry


class RequestRetryAction(BaseAction):
    """Action used by agents to request that the current run be retried.

    Expected params:
        - reason: Optional[str]  (short explanation logged by the engine)
    """

    action_type = "request_retry"

    def validate(self) -> bool:
        reason = self.params.get("reason")
        if reason is not None and not isinstance(reason, str):
            return False
        return True

    def execute(self, ctx: ActionContext) -> None:
        # The concrete runtime context (ActionRuntimeContext) has
        # retry_requested / retry_reason fields.
        setattr(ctx, "retry_requested", True)
        reason: Optional[str] = self.params.get("reason")
        setattr(ctx, "retry_reason", reason)

        logger = getattr(ctx, "logger", None)
        if logger is not None:
            if reason:
                logger.info(
                    "[request_retry] Agent requested retry for this run: %s",
                    reason,
                )
            else:
                logger.info(
                    "[request_retry] Agent requested retry for this run (no reason provided)."
                )


# Register
ActionRegistry.register(RequestRetryAction)
