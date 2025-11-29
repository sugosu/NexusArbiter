from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from core.config.run_config import RunItem
from core.context.context_loader import load_context_params
from core.runtime.app_runner import AppRunner, RunResult


@dataclass
class RunExecutionResult:
    """High-level summary of one RunItem execution (with retries)."""

    success: bool
    attempts: int
    retried: bool
    last_retry_reason: str | None = None


class RunExecutor:
    """Execute a single RunItem with agent-driven retry logic."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.app_runner = AppRunner(project_root=project_root)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _build_run_params_for_attempt(
        self,
        run: RunItem,
        use_retry_ctx: bool,
        attempt: int,
    ) -> Dict[str, Any]:
        """Load context files, and print which ones are chosen for this attempt."""
        if use_retry_ctx and run.retry_context_files:
            context_files = run.retry_context_files
            ctx_type = "retry_context_files"
        else:
            context_files = run.context_file
            ctx_type = "context_file"

        if not context_files:
            raise ValueError("Run is missing context_file / retry_context_files.")

        print(f"[RunExecutor] Attempt {attempt} using {ctx_type}: {context_files}")

        params = load_context_params(self.project_root, context_files)

        # Attach the list so AppRunner can also log it
        params["_context_files_display"] = context_files

        return params

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def execute(
        self,
        run: RunItem,
        run_index: int,
        use_retry_context_on_first_attempt: bool = False,
    ) -> RunExecutionResult:
        """
        Execute the given RunItem with agent-controlled retries.

        Parameters
        ----------
        run : RunItem
            The configured run step.
        run_index : int
            1-based index for logging.
        use_retry_context_on_first_attempt : bool
            If True, the *first* attempt for this run will already use
            `retry_context_files` (if present) instead of `context_file`.

            This is used by the pipeline-level retry_from mechanism:
            when the pipeline is restarted from a given run, that run
            can immediately switch to its retry_context_files.
        """
        max_extra_retries = max(0, run.retry)
        retries_used = 0
        attempt = 1
        last_retry_reason: str | None = None

        while True:
            use_retry_ctx = (
                attempt > 1
                or (attempt == 1 and use_retry_context_on_first_attempt)
            )

            run_params = self._build_run_params_for_attempt(
                run=run,
                use_retry_ctx=use_retry_ctx,
                attempt=attempt,
            )

            agent_input_overrides = dict(run.agent_input or {})

            if run.target_file:
                agent_input_overrides["target_file"] = run.target_file

            if run.allowed_actions:
                agent_input_overrides["allowed_actions"] = run.allowed_actions

            try:
                result: RunResult = self.app_runner.run(
                    run_item=run,
                    run_params=run_params,
                    profile_name=run.profile_name,
                    class_name=run.class_name,
                    task_description=run.task_description,
                    agent_input_overrides=agent_input_overrides,
                )
            except Exception as exc:  # noqa: BLE001
                print(f"[RUN {run_index}] attempt {attempt} crashed with exception: {exc}")
                return RunExecutionResult(
                    success=False,
                    attempts=attempt,
                    retried=retries_used > 0,
                    last_retry_reason=last_retry_reason,
                )

            if result.success:
                return RunExecutionResult(
                    success=True,
                    attempts=attempt,
                    retried=retries_used > 0,
                    last_retry_reason=last_retry_reason,
                )

            # Not successful: see if retry was explicitly requested
            if not result.retry_requested:
                print(
                    f"[RUN {run_index}] attempt {attempt} failed without retry request; "
                    "stopping this run."
                )
                return RunExecutionResult(
                    success=False,
                    attempts=attempt,
                    retried=retries_used > 0,
                    last_retry_reason=last_retry_reason,
                )

            # Agent did request a retry
            last_retry_reason = result.retry_reason

            if retries_used >= max_extra_retries:
                print(
                    f"[RUN {run_index}] attempt {attempt} requested retry, "
                    f"but max retries ({max_extra_retries}) reached; stopping."
                )
                # Note: retried=True here means "agent asked for retry but
                # we had no remaining budget in this RunExecutor".
                return RunExecutionResult(
                    success=False,
                    attempts=attempt,
                    retried=True,
                    last_retry_reason=last_retry_reason,
                )

            retries_used += 1
            next_attempt = attempt + 1
            print(
                f"[RUN {run_index}] attempt {attempt} requested retry; "
                f"starting attempt {next_attempt} (retry {retries_used}/{max_extra_retries})."
            )
            attempt = next_attempt
