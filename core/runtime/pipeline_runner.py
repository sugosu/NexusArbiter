# core/runtime/pipeline_runner.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.config.run_config import RunConfig, RunItem
from core.runtime.run_executor import RunExecutor


@dataclass
class PipelineResult:
    """Optional container for aggregated pipeline status."""
    total_runs: int
    succeeded: int
    failed: int
    pipeline_retried: bool


class PipelineRunner:
    """
    Orchestrates execution of a RunConfig through RunExecutor.

    Responsibilities:
    - Iterate over all runs
    - Handle pipeline-level retry_from logic
    - Decide when to restart and from which index
    - Report basic status to stdout
    """

    def __init__(self, project_root: Path, config: RunConfig) -> None:
        self.project_root = project_root
        self.config = config
        self.executor = RunExecutor(project_root=project_root)

        self.total_runs = len(config.runs)

        retry_from: Optional[int] = getattr(config, "retry_from", None)
        if retry_from is not None:
            # clamp into [1, total_runs]
            retry_from = max(1, min(retry_from, self.total_runs))
        self.retry_from: Optional[int] = retry_from

    def run(self) -> PipelineResult:
        idx = 1  # 1-based index for human-readable logs
        pipeline_retried = False
        restart_from_index: Optional[int] = None

        succeeded = 0
        failed = 0

        while idx <= self.total_runs:
            run: RunItem = self.config.runs[idx - 1]

            # If we just restarted from a specific index, the *first* run
            # after restart should use retry_context_files instead of the
            # original context_file.
            use_retry_ctx_first = restart_from_index is not None and idx == restart_from_index

            # Consume the flag so it applies only once.
            if use_retry_ctx_first:
                restart_from_index = None

            result = self.executor.execute(
                run=run,
                run_index=idx,
                use_retry_context_on_first_attempt=use_retry_ctx_first,
            )

            status = "OK" if result.success else "FAILED"
            if result.retried:
                print(
                    f"[RUN {idx}] finished with status {status} "
                    f"after {result.attempts} attempts. "
                    f"Retry reason (last): {result.last_retry_reason or '<none>'}."
                )
            else:
                print(
                    f"[RUN {idx}] finished with status {status} "
                    f"after {result.attempts} attempts."
                )

            if result.success:
                succeeded += 1
            else:
                failed += 1

            # Pipeline-level retry_from logic:
            #
            # If:
            #   - this run did NOT succeed,
            #   - the RunExecutor reports that the agent requested retry
            #     at some point (result.retried == True), and
            #   - the config defines retry_from,
            #   - and we have not yet used the pipeline-level restart,
            # then:
            #   - restart the pipeline from retry_from,
            #   - and for that first restarted run, force use of retry_context_files.
            if (
                not result.success
                and result.retried
                and self.retry_from is not None
                and not pipeline_retried
            ):
                print(
                    f"[RUN {idx}] pipeline-level retry_from triggered; "
                    f"restarting from run index {self.retry_from} "
                    f"using retry_context_files for that run (if configured)."
                )
                pipeline_retried = True
                restart_from_index = self.retry_from
                idx = self.retry_from
                continue

            idx += 1

        return PipelineResult(
            total_runs=self.total_runs,
            succeeded=succeeded,
            failed=failed,
            pipeline_retried=pipeline_retried,
        )
