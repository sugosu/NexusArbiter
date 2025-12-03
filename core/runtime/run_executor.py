from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config.run_config import RunItem
from core.context.context_loader import load_context_params
from core.runtime.app_runner import AppRunner, RunResult


@dataclass
class RunExecutionResult:
    """High-level summary of one RunItem execution (with retries)."""

    success: bool
    attempts: int
    retried: bool
    last_retry_reason: Optional[str] = None


class RunExecutor:
    """Execute a single RunItem with agent-driven retry logic."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root).resolve()
        self.app_runner = AppRunner(project_root=self.project_root)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _resolve_context_files(self, profile_file: str, base_files: List[str]) -> List[str]:
        """
        Ensure that, if profile_file is set, it is present as the FIRST
        context file for this attempt.

        Behaviour:
        - If base_files is empty, return [profile_file].
        - If base_files already contains profile_file, move it to index 0.
        - Otherwise, prepend profile_file to base_files.
        """
        profile_file = (profile_file or "").strip()

        if not profile_file:
            # No profile file to inject, just return base_files as-is.
            return list(base_files)

        if not base_files:
            return [profile_file]

        files = [str(p) for p in base_files]

        if profile_file not in files:
            return [profile_file] + files

        if files[0] == profile_file:
            return files

        # Move profile_file to the front, preserving order for others
        return [profile_file] + [f for f in files if f != profile_file]

    def _build_run_params_for_attempt(
        self,
        run: RunItem,
        use_retry_ctx: bool,
        attempt: int,
    ) -> Dict[str, Any]:
        """
        Load context files for this attempt, and attach a display list.

        This method:
        - Picks either context_file or retry_context_files depending on
          use_retry_ctx.
        - Ensures run.profile_file is included as the first context file.
        - Calls load_context_params(project_root, context_files).
        """
        if use_retry_ctx and run.retry_context_files:
            base_files = run.retry_context_files
            ctx_type = "retry_context_files"
        else:
            base_files = run.context_file
            ctx_type = "context_file"

        context_files = self._resolve_context_files(run.profile_file, base_files)

        if not context_files:
            raise ValueError(
                "Run has no context_file / retry_context_files, "
                "and no profile_file was provided."
            )

        print(f"[RunExecutor] Attempt {attempt} using {ctx_type}: {context_files}")

        # The underlying loader is responsible for reading JSON / text etc.
        params = load_context_params(self.project_root, context_files)

        # Keep the list of context files used for this attempt for logging
        # and for including in the agent_input.
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
        """
        # How many additional logical retries we allow:
        max_extra_retries = max(0, int(run.retry))

        retries_used = 0
        attempt = 1
        last_retry_reason: Optional[str] = None

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

            # Construct an agent_input override: we want to inject the
            # current context_file list (for debugging) and anything else
            # from RunItem.agent_input.
            agent_input_overrides: Dict[str, Any] = dict(run.agent_input or {})

            # Also propagate the target_file for actions like file_write
            if run.target_file:
                agent_input_overrides["target_file"] = run.target_file

            # Propagate allowed_actions so the profile can see the limitation
            # and so the AppRunner can also filter actions:
            if run.allowed_actions:
                agent_input_overrides["allowed_actions"] = run.allowed_actions

            # For logging / debugging, use the profile_file as a logical
            # profile_name here. The profile JSON itself may also declare
            # a "name" field, but this is independent.
            profile_label = run.profile_file

            try:
                result: RunResult = self.app_runner.run(
                    run_item=run,
                    run_params=run_params,
                    profile_name=profile_label,
                    class_name=run.class_name,
                    task_description=run.task_description,
                    agent_input_overrides=agent_input_overrides,
                )
            except Exception as exc:  # noqa: BLE001
                print(
                    f"[RUN {run_index}] attempt {attempt} crashed with exception: {exc}"
                )
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
                return RunExecutionResult(
                    success=False,
                    attempts=attempt,
                    retried=retries_used > 0,
                    last_retry_reason=last_retry_reason,
                )

            retries_used += 1
            next_attempt = attempt + 1
            print(
                f"[RUN {run_index}] attempt {attempt} requested retry; "
                f"starting attempt {next_attempt} (retry {retries_used}/{max_extra_retries})."
            )
            attempt = next_attempt
