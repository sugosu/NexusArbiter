# core/runtime/pipeline_runner.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.logger import BasicLogger
from core.runtime.run_executor import RunExecutor, RunResult
from core.config.run_config import RunConfig, RunItem
from core.config.strategy_config import StrategyFile


class PipelineRunner:
    """
    Orchestrates execution of the entire runs.json pipeline.

    Key responsibilities:
      - execute runs in sequence
      - detect change_strategy requests from validator runs
      - maintain attempt counters per (target_run, strategy_index)
      - load strategy file and apply overrides
      - re-run the target codegen run with the correct attempt settings
      - detect break / success / exhaustion
    """

    def __init__(self, project_root: str, config: RunConfig):
        self.project_root = Path(project_root)
        self.config = config
        self.logger = BasicLogger("PipelineRunner").get_logger()

        self.executor = RunExecutor(project_root=str(self.project_root))

        # Track number of attempts for each (target_run, strategy_index)
        # Key: (str, int) -> (target_run_name, strategy_block_index)
        # Value: int  -> number of change_strategy attempts already used
        self.strategy_attempt_counters: Dict[Tuple[str, int], int] = {}

        # Correlate one full pipeline execution in the logs
        self.run_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")

    # ------------------------------------------------------------------
    # Main pipeline execution entrypoint
    # ------------------------------------------------------------------
    def run(self) -> None:
        total_runs = len(self.config.runs)
        succeeded = 0

        self.logger.info(
    "Warp field stabilized",
    extra={"event": "warp_stabilized"}
)

        self.logger.info(
            "Pipeline started",
            extra={
                "event": "pipeline_start",
                "run_id": self.run_id,
                "project_root": str(self.project_root),
                "total_runs": total_runs,
            },
        )

        

        for index, run_item in enumerate(self.config.runs):
            self.logger.info(
                f"[RUN] Starting '{run_item.name}'",
                extra={
                    "event": "run_start",
                    "run_id": self.run_id,
                    "run_index": index,
                    "total_runs": total_runs,
                    "run_name": run_item.name,
                    "profile_file": run_item.profile_file,
                    "target_file": run_item.target_file,
                    "context_files": list(run_item.context_file),
                    "is_validator": run_item.is_validator(),
                },
            )

            result = self._execute_run_item(run_item)

            # Break requested by an action
            if result.should_break:
                self.logger.info(
                    f"[RUN] '{run_item.name}' requested break. Pipeline stopping.",
                    extra={
                        "event": "run_break",
                        "run_id": self.run_id,
                        "run_name": run_item.name,
                    },
                )
                break

            if not result.success:
                self.logger.error(
                    f"[RUN] '{run_item.name}' failed. Pipeline stopping.",
                    extra={
                        "event": "run_failed",
                        "run_id": self.run_id,
                        "run_name": run_item.name,
                        "change_strategy_requested": result.change_strategy_requested,
                        "change_strategy_reason": result.change_strategy_reason,
                    },
                )
                break

            self.logger.info(
                f"[RUN] '{run_item.name}' succeeded.",
                extra={
                    "event": "run_succeeded",
                    "run_id": self.run_id,
                    "run_name": run_item.name,
                },
            )
            succeeded += 1

        self.logger.info(
            "Pipeline finished",
            extra={
                "event": "pipeline_finished",
                "run_id": self.run_id,
                "succeeded_runs": succeeded,
                "total_runs": total_runs,
            },
        )

    # ------------------------------------------------------------------
    # Execute a single run item (possibly triggers strategy reruns)
    # ------------------------------------------------------------------
    def _execute_run_item(self, run_item: RunItem) -> RunResult:
        # Normal single execution for codegen or validator
        base_result = self._execute_once(run_item)

        if base_result.change_strategy_requested:
            # Must be a validator run (by design)
            self.logger.info(
                f"[RUN] '{run_item.name}' requested change_strategy.",
                extra={
                    "event": "run_change_strategy_requested",
                    "run_id": self.run_id,
                    "run_name": run_item.name,
                    "change_strategy_reason": base_result.change_strategy_reason,
                },
            )
            return self._handle_change_strategy(run_item, base_result)

        return base_result

    # ------------------------------------------------------------------
    # Actual single execution call to RunExecutor
    # ------------------------------------------------------------------
    def _execute_once(self, run_item: RunItem) -> RunResult:
        profile_file = run_item.profile_file
        context_files = run_item.context_file
        target_file = run_item.target_file

        # Provider now comes from profile (or strategy overrides),
        # so for a normal run we pass no override.
        provider_override: Optional[str] = None

        return self.executor.execute_once(
            run_item=run_item,
            context_files=context_files,
            profile_file=profile_file,
            target_file=target_file,
            provider_override=provider_override,
        )

    # ------------------------------------------------------------------
    # NOTE:
    # _handle_change_strategy(...) and _find_run_item(...) remain as you
    # currently have them. You already have detailed logs inside that
    # method; they will continue to show up with run_id included in
    # the higher-level entries above.
    # ------------------------------------------------------------------
