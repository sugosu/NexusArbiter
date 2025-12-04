from __future__ import annotations

import json
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
        # Key: (str, int)
        # Value: int  -> number of change_strategy attempts already used
        self.strategy_attempt_counters: Dict[Tuple[str, int], int] = {}

    # ------------------------------------------------------------------
    # Main pipeline execution entrypoint
    # ------------------------------------------------------------------
    def run(self) -> None:

        total_runs = len(self.config.runs)
        succeeded = 0

        for run_item in self.config.runs:
            self.logger.info(f"[RUN] Starting '{run_item.name}'")

            result = self._execute_run_item(run_item)

            if result.should_break:
                self.logger.info(f"[RUN] '{run_item.name}' requested break. Pipeline stopping.")
                break

            if not result.success:
                self.logger.error(f"[RUN] '{run_item.name}' failed. Pipeline stopping.")
                break

            succeeded += 1

        self.logger.info(
            f"Pipeline finished: {succeeded}/{total_runs} succeeded."
        )

    # ------------------------------------------------------------------
    # Execute a single run item (possibly triggers strategy reruns)
    # ------------------------------------------------------------------
    def _execute_run_item(self, run_item: RunItem) -> RunResult:

        # Normal single execution for codegen or validator
        base_result = self._execute_once(run_item)

        if base_result.change_strategy_requested:
            # Must be a validator run (by design)
            return self._handle_change_strategy(run_item, base_result)

        return base_result

    # ------------------------------------------------------------------
    # Actual single execution call to RunExecutor
    # ------------------------------------------------------------------
    def _execute_once(self, run_item: RunItem) -> RunResult:

        profile_file = run_item.profile_file
        context_files = run_item.context_file
        target_file = run_item.target_file
        provider_override = run_item.provider or self.config.provider

        return self.executor.execute_once(
            run_item=run_item,
            context_files=context_files,
            profile_file=profile_file,
            target_file=target_file,
            provider_override=provider_override,
        )

    # ------------------------------------------------------------------
    # Handle change_strategy from validator
    # ------------------------------------------------------------------
    def _handle_change_strategy(self, validator_run: RunItem, validator_result: RunResult) -> RunResult:

        if not validator_run.is_validator():
            self.logger.error(
                f"Validator run '{validator_run.name}' triggered change_strategy but has no "
                f"strategy_index / target_run / strategy_file defined."
            )
            return RunResult(success=False)

        strategy_file_path = validator_run.strategy_file
        block_index = validator_run.strategy_index
        target_run_name = validator_run.target_run

        # Load strategy file
        try:
            strategy = StrategyFile.from_file(self.project_root / strategy_file_path)
        except Exception as e:
            self.logger.error(f"Error loading strategy file '{strategy_file_path}': {e}")
            return RunResult(success=False)

        # Find target run item (codegen)
        target_run = self._find_run_item(target_run_name)
        if target_run is None:
            self.logger.error(
                f"Validator '{validator_run.name}' refers to unknown target_run '{target_run_name}'."
            )
            return RunResult(success=False)

        # Get current attempt count
        key = (target_run_name, block_index)
        attempt_number = self.strategy_attempt_counters.get(key, 0)

        # Fetch current attempt override
        attempt = strategy.get_attempt(block_index, attempt_number)

        if attempt is None:
            self.logger.info(
                f"Strategy exhausted for target_run='{target_run_name}', block={block_index}. "
                f"No more attempts available."
            )
            return RunResult(success=False)

        # Apply overrides
        overridden_profile = attempt.profile or target_run.profile_file
        overridden_provider = attempt.provider or target_run.provider or self.config.provider
        overridden_context = attempt.retry_context_files or target_run.context_file

        self.logger.info(
            f"[change_strategy] Applying strategy attempt #{attempt_number} for "
            f"run '{target_run_name}' (block={block_index}). "
            f"Overrides: profile='{overridden_profile}', provider='{overridden_provider}', "
            f"context={overridden_context}"
        )

        # Execute target run with overrides
        rerun_result = self.executor.execute_once(
            run_item=target_run,
            context_files=overridden_context,
            profile_file=overridden_profile,
            target_file=target_run.target_file,
            provider_override=overridden_provider,
        )

        # If rerun requests break, stop immediately
        if rerun_result.should_break:
            self.logger.info(
                f"[change_strategy] Target run '{target_run_name}' requested break during strategy attempt."
            )
            return rerun_result

        # Decide next action
        if rerun_result.change_strategy_requested:
            # Validator re-executed itself and again requested another strategy change:
            # We MUST increment attempt counter and process again.
            self.logger.info(
                f"[change_strategy] Strategy attempt #{attempt_number} resulted in another change_strategy request."
            )
            self.strategy_attempt_counters[key] = attempt_number + 1
            return self._handle_change_strategy(validator_run, rerun_result)

        if not rerun_result.success:
            # Failed without triggering another change_strategy
            self.logger.error(
                f"[change_strategy] Strategy attempt #{attempt_number} failed without further instructions."
            )
            self.strategy_attempt_counters[key] = attempt_number + 1
            return rerun_result

        # Successful rerun → return success back to validator
        self.logger.info(
            f"[change_strategy] Strategy attempt #{attempt_number} succeeded for '{target_run_name}'."
        )
        self.strategy_attempt_counters[key] = attempt_number + 1

        # FIX: After successful codegen rerun, rerun validator itself again.
        # Validator must validate the new output before pipeline continues.
        self.logger.info(f"[change_strategy] Re-running validator '{validator_run.name}' after successful codegen fix.")
        return self._execute_once(validator_run)

    # ------------------------------------------------------------------
    # Utility: find a run item by name
    # ------------------------------------------------------------------
    def _find_run_item(self, name: str) -> Optional[RunItem]:
        for r in self.config.runs:
            if r.name == name:
                return r
        return None
