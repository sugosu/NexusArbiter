# core/runtime/pipeline_runner.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple, Optional, Any, List

from core.config.run_config import RunConfig, RunItem
from core.runtime.run_executor import RunExecutor, RunResult
from core.strategy.rerun_strategy import RerunStrategy
from core.logger import BasicLogger



class PipelineRunner:
    """
    Executes a sequence of RunItems from a RunConfig.

    Responsibilities:
    - Maintain run index.
    - Track attempt numbers for each run (including reruns).
    - Delegate execution to RunExecutor.
    - Handle rerun requests via _handle_change_strategy.
    """

    def __init__(self, project_root: Path, config: RunConfig, start_from: int = 0):
        self.project_root = Path(project_root)
        self.config = config
        self.start_from = start_from

        # Tracks how many times each run has been executed:
        # key = run_item.name -> attempt_number (starting at 1)
        self._run_attempt_counters: Dict[str, int] = {}

        # Tracks how many attempts were consumed within a rerun block:
        # key = (validator_name, rerun_index) -> attempt_index
        self._rerun_attempts: Dict[Tuple[str, int], int] = {}

        # Executor that performs a single run
        self.executor = RunExecutor(project_root=str(self.project_root))

        # Logger
        self.logger = BasicLogger("PipelineRunner").get_logger()

    # ----------------------------------------------------------------------
    # Utilities
    # ----------------------------------------------------------------------
    def _increment_attempt(self, run_item: RunItem) -> int:
        """
        Increment and return the attempt number for this run.
        First execution -> attempt = 1, then 2, 3...
        """
        name = run_item.name
        prev = self._run_attempt_counters.get(name, 0)
        curr = prev + 1
        self._run_attempt_counters[name] = curr
        return curr

    def _current_attempt(self, run_item: RunItem) -> int:
        """
        Return current attempt counter without incrementing.
        """
        return self._run_attempt_counters.get(run_item.name, 0)

    # ----------------------------------------------------------------------
    # Main run loop
    # ----------------------------------------------------------------------
    def run(self) -> None:
        self.logger.info("Warp fields stabilized")
        self.logger.info("Pipeline started")

        index = 0
        runs: List[RunItem] = self.config.runs

        # Optional: safety check
        if self.start_from is not None and self.start_from >= len(runs):
            self.logger.warning(
                f"start_from={self.start_from} is beyond total runs ({len(runs)}). Nothing to execute."
            )
            self.logger.info("Pipeline completed.")
            return

        while index < len(runs):
            # Skip runs before start_from (if provided)
            if self.start_from is not None and index < self.start_from:
                self.logger.info(
                    f"[RUN SKIPPED] index={index} < start_from={self.start_from}"
                )
                index += 1
                continue

            run_item = runs[index]

            # Determine attempt number before execution
            attempt_number = self._increment_attempt(run_item)

            self.logger.info(
                f"[RUN] Starting '{run_item.name}' attempt={attempt_number}"
            )

            # Execute
            result = self._execute_run_item(run_item, attempt_number)

            # Pipeline break?
            if result.should_break:
                self.logger.info(
                    f"[BREAK] Pipeline terminated by '{run_item.name}'. Reason={result.change_strategy_reason!r}"
                )
                break

            # Did the run ask for rerun / strategy change?
            if result.change_strategy_requested:
                self.logger.info(
                    f"[RERUN] '{run_item.name}' requested strategy change. "
                    f"Reason={result.change_strategy_reason!r}"
                )

                rerun_applied = self._handle_change_strategy(run_item)

                if rerun_applied:
                    # Do NOT increment the index
                    continue
                else:
                    self.logger.info(
                        f"[RERUN] No further attempts left for '{run_item.name}'. Moving on."
                    )

            # Normal case → go to next
            index += 1

        self.logger.info("Pipeline completed.")


    # ----------------------------------------------------------------------
    # Run execution wrapper
    # ----------------------------------------------------------------------
    def _execute_run_item(self, run_item: RunItem, attempt_number: int) -> RunResult:
        """
        Creates a RunResult via RunExecutor.
        """
        profile_file = run_item.profile_file
        context_files = run_item.context_file
        target_file = run_item.target_file

        provider_override = getattr(run_item, "provider_override", None)

        log_io_settings = self._merged_log_settings(run_item)

        return self.executor.execute_once(
            run_item=run_item,
            context_files=context_files,
            profile_file=profile_file,
            target_file=target_file,
            provider_override=provider_override,
            attempt_number=attempt_number,
            log_io_settings=log_io_settings,
        )

    # ----------------------------------------------------------------------
    # Merge global + per-run log settings
    # ----------------------------------------------------------------------
    def _merged_log_settings(self, run_item: RunItem) -> Dict[str, Any]:
        """
        Merge top-level log_io settings with per-run overrides.
        """
        global_cfg = self.config.log_io_settings
        merged = {
            "enabled": global_cfg.enabled,
            "log_dir": global_cfg.log_dir,
            "request_file_pattern": global_cfg.request_file_pattern,
            "response_file_pattern": global_cfg.response_file_pattern,
        }

        if run_item.log_io_override:
            override = run_item.log_io_override
            if "enabled" in override:
                merged["enabled"] = bool(override["enabled"])
            if "log_dir" in override:
                merged["log_dir"] = override["log_dir"]
            if "request_file_pattern" in override:
                merged["request_file_pattern"] = override["request_file_pattern"]
            if "response_file_pattern" in override:
                merged["response_file_pattern"] = override["response_file_pattern"]

        return merged

    # ----------------------------------------------------------------------
    # Rerun handling
    # ----------------------------------------------------------------------
    def _handle_change_strategy(self, validator_run_item: RunItem) -> bool:
        """
        Apply rerun strategy:
        - Modify target run's profile/provider/context
        - Execute target run immediately
        - Increment rerun attempt counter
        - Return True if validator should re-run
        """
        name = validator_run_item.name

        if validator_run_item.target_run is None:
            self.logger.error(f"[RERUN] Validator '{name}' has no target_run set.")
            return False

        if validator_run_item.rerun_strategy is None:
            self.logger.error(f"[RERUN] Validator '{name}' has no rerun_strategy file.")
            return False

        if validator_run_item.rerun_index is None:
            self.logger.error(f"[RERUN] Validator '{name}' has no rerun_index.")
            return False

        strategy_file = Path(validator_run_item.rerun_strategy)
        if not strategy_file.exists():
            self.logger.error(
                f"[RERUN] Strategy file does not exist: {strategy_file}"
            )
            return False

        # Load strategy
        strategy_file = Path(validator_run_item.rerun_strategy)
        if not strategy_file.exists():
            self.logger.error(
                f"[RERUN] Strategy file does not exist: {strategy_file}"
            )
            return False

        target_name = validator_run_item.target_run

        if target_name:
            # New: index-aware loading (select by target_run)
            strategy = RerunStrategy.from_file_for_target(
                strategy_file,
                target_run=target_name,
            )
        else:
            # Fallback: legacy behaviour (file has direct "blocks" or "strategy")
            strategy = RerunStrategy.from_file(strategy_file)

        blocks = strategy.blocks

        idx = validator_run_item.rerun_index
        if idx < 0 or idx >= len(blocks):
            self.logger.error(
                f"[RERUN] Invalid rerun_index={idx} in validator '{name}'."
            )
            return False

        block = blocks[idx]

        key = (validator_run_item.name, idx)
        current_attempt = self._rerun_attempts.get(key, 0)

        if current_attempt >= len(block.attempts):
            self.logger.info(
                f"[RERUN] All rerun attempts exhausted for validator '{name}'."
            )
            return False

        attempt_cfg = block.attempts[current_attempt]

        # Find target run
        target_name = validator_run_item.target_run
        target_run = None
        for r in self.config.runs:
            if r.name == target_name:
                target_run = r
                break

        if not target_run:
            self.logger.error(
                f"[RERUN] Target run '{target_name}' not found in config."
            )
            return False

        # Apply overrides
        if attempt_cfg.profile_file:
            target_run.profile_file = attempt_cfg.profile_file
        if attempt_cfg.provider:
            target_run.provider_override = attempt_cfg.provider
        if attempt_cfg.context_files is not None:
            target_run.context_file = attempt_cfg.context_files
            pretty = ", ".join(attempt_cfg.context_files)
            self.logger.info(
                f"[RERUN] Context override applied: {pretty}"
            )

        self.logger.info(
            f"[RERUN] Applying rerun attempt {current_attempt + 1}/{len(block.attempts)} "
            f"for target '{target_run.name}'."
        )

        # Update attempt counter
        self._rerun_attempts[key] = current_attempt + 1

        # Execute target run immediately with a new attempt number
        attempt_number = self._increment_attempt(target_run)

        self.logger.info(
            f"[RERUN] Executing target run '{target_run.name}' with attempt={attempt_number}"
        )

        result = self._execute_run_item(target_run, attempt_number)

        # Validator will run again
        return True
