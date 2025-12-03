# core/actions/trigger_retry.py
from __future__ import annotations

from typing import Optional

from .base_action import BaseAction, ActionContext
from .registry import ActionRegistry


class TriggerRetryAction(BaseAction):
    """
    Higher-level action to request retrying *previous* steps with extra context.

    This is intended for coordinator / planner agents that want to tell the
    pipeline: "go back and rerun from step X, here is why and with what note".

    Expected params:
        - reason: Optional[str]         – human-readable reason
        - from_run_index: Optional[int] – 1-based index of run to restart from
        - note: Optional[str]           – additional free-form guidance

    Current behaviour:
        - Sets ctx.retry_requested = True so the RunExecutor treats this like
          a normal retry request for the current run.
        - Packs the details into ctx.retry_reason for logging.
        - Attaches richer metadata on the context for future pipeline-level
          handling (trigger_retry_from_run_index, trigger_retry_note).

    The pipeline-level code can later be extended to inspect those additional
    fields and override retry_from dynamically.
    """

    action_type = "trigger_retry"

    def validate(self) -> bool:
        reason = self.params.get("reason")
        from_run_index = self.params.get("from_run_index")
        note = self.params.get("note")

        if reason is not None and not isinstance(reason, str):
            return False
        if note is not None and not isinstance(note, str):
            return False
        if from_run_index is not None and not isinstance(from_run_index, int):
            return False

        return True

    def execute(self, ctx: ActionContext) -> None:
        reason: Optional[str] = self.params.get("reason")
        note: Optional[str] = self.params.get("note")
        from_run_index: Optional[int] = self.params.get("from_run_index")

        # For now, align with run-level retry semantics so the executor
        # still behaves correctly even before pipeline-level wiring.
        setattr(ctx, "retry_requested", True)

        parts = []
        if reason:
            parts.append(reason)
        if note:
            parts.append(f"note={note}")
        if from_run_index is not None:
            parts.append(f"from_run_index={from_run_index}")

        combined_reason = " | ".join(parts) if parts else None
        setattr(ctx, "retry_reason", combined_reason)

        # Store richer metadata for future pipeline-level logic
        setattr(ctx, "trigger_retry_from_run_index", from_run_index)
        setattr(ctx, "trigger_retry_note", note)

        logger = getattr(ctx, "logger", None)
        if logger is not None:
            logger.info(
                "[trigger_retry] Higher-level agent requested pipeline retry: %s",
                combined_reason or "<no reason>",
            )


# Register
ActionRegistry.register(TriggerRetryAction)
