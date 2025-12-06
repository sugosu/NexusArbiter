# core/runtime/pipeline_runner.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

from core.logger import BasicLogger
from core.runtime.run_executor import RunExecutor, RunResult
from core.config.run_config import RunConfig, RunItem
from core.strategy.rerun_strategy import RerunStrategy


class PipelineRunner:
    """
    Orchestrates execution of the entire runs.json pipeline.

    Responsibilities:
    - Execute runs in sequence
    - Detect rerun (formerly change_strategy) requests from validator runs
    - Maintain in-memory attempt counters per (validator_run_name, rerun_index)
    - Load rerun strategy files and apply overrides
    - Re-run the target codegen run with the correct attempt settings
    - Respect break signals from actions
    """

    def __init__(self, project_root: str | Path, config: RunConfig):
        self.project_root = Path(project_root)
        self.config = config
        self.logger = BasicLogger(self.__class__.__name__).get_logger()

        # Single-step executor
        self.executor = RunExecutor(project_root=str(self.project_root))

        # (validator_run_name, rerun_index) -> attempt_index
        self._rerun_attempts: Dict[Tuple[str, int], int] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self) -> None:
        """
        Execute the pipeline according to the loaded RunConfig.
        """
        self.logger.info("Warp field stabilized")
        self.logger.info("Pipeline started")

        i = 0
        total_runs = len(self.config.runs)

        while i < total_runs:
            run_item = self.config.runs[i]
            self.logger.info(f"[RUN] Starting '{run_item.name}'")

            result = self._execute_run_item(run_item)

            # Break requested: stop whole pipeline
            if result.should_break:
                self.logger.info(f"[RUN] '{run_item.name}' requested break -> stopping pipeline.")
                break

            # Rerun requested: apply rerun strategy and stay on same index
            if result.change_strategy_requested:
                self.logger.info(
                    f"[RUN] '{run_item.name}' requested rerun: {result.change_strategy_reason}"
                )
                rerun_applied = self._handle_change_strategy(run_item)
                if rerun_applied:
                    # Stay on same run index to re-execute after overrides
                    continue
                else:
                    self.logger.warning(
                        f"[RUN] Rerun requested by '{run_item.name}' but no further attempts remain."
                    )

            # Otherwise, proceed to next run
            self.logger.info(f"[RUN] '{run_item.name}' succeeded.")
            i += 1

        self.logger.info("Pipeline finished")

    # ------------------------------------------------------------------
    # Single run execution
    # ------------------------------------------------------------------
    def _execute_run_item(self, run_item: RunItem) -> RunResult:
        """
        Execute a single run item using RunExecutor.
        """
        profile_file = run_item.profile_file
        context_files = run_item.context_file
        target_file = run_item.target_file

        # Provider override can be injected by rerun strategy
        provider_override = getattr(run_item, "provider_override", None)

        return self.executor.execute_once(
            run_item=run_item,
            context_files=context_files,
            profile_file=profile_file,
            target_file=target_file,
            provider_override=provider_override,
        )

    # ------------------------------------------------------------------
    # Handle RERUN (formerly change_strategy)
    # ------------------------------------------------------------------
    def _handle_change_strategy(self, validator_run_item: RunItem) -> bool:
        """
        Handle a rerun request coming from a validator run.

        Uses:
        - validator_run_item.rerun_index
        - validator_run_item.rerun_strategy
        - validator_run_item.target_run
        """
        # Validator must specify target_run
        if not validator_run_item.target_run:
            self.logger.error("Rerun requested but validator_run_item.target_run is missing.")
            return False

        # Find target run by name
        target_run_name = validator_run_item.target_run
        target_run: RunItem | None = None
        for r in self.config.runs:
            if r.name == target_run_name:
                target_run = r
                break

        if target_run is None:
            self.logger.error(f"Rerun requested but target run '{target_run_name}' not found.")
            return False

        # Load strategy file path
        strategy_path = validator_run_item.rerun_strategy
        if not strategy_path:
            self.logger.error("Rerun requested but no rerun_strategy file specified.")
            return False

        strategy_file = (self.project_root / strategy_path).resolve()
        if not strategy_file.exists():
            self.logger.error(f"Rerun strategy file missing: {strategy_file}")
            return False

        # Load the rerun strategy JSON
        try:
            rerun_strategy = RerunStrategy.from_file(strategy_file)
        except Exception as e:
            self.logger.error(f"Failed to load rerun strategy file '{strategy_file}': {e}")
            return False

        # Determine which block to use
        block_index = validator_run_item.rerun_index
        if block_index is None or block_index < 0:
            self.logger.error("Invalid rerun_index on validator run item.")
            return False

        if block_index >= len(rerun_strategy.blocks):
            self.logger.error(
                f"rerun_index {block_index} is out of range. "
                f"Strategy has only {len(rerun_strategy.blocks)} blocks."
            )
            return False

        block = rerun_strategy.blocks[block_index]

        # Determine current attempt index from in-memory map
        key = (validator_run_item.name, block_index)
        current_attempt = self._rerun_attempts.get(key, 0)

        if current_attempt >= len(block.attempts):
            self.logger.info(
                f"All rerun attempts exhausted for validator='{validator_run_item.name}', "
                f"block_index={block_index}."
            )
            return False

        attempt = block.attempts[current_attempt]
        total_attempts = len(block.attempts)

        self.logger.info(
            f"Applying rerun attempt {current_attempt + 1}/{total_attempts} "
            f"from block {block_index} "
            f"for target run '{target_run.name}'."
        )

        # Apply overrides to the target run
        if attempt.profile_file:
            target_run.profile_file = attempt.profile_file
            self.logger.info(f"Override: profile_file -> {attempt.profile_file}")

        if attempt.provider:
            setattr(target_run, "provider_override", attempt.provider)
            self.logger.info(f"Override: provider -> {attempt.provider}")

        if attempt.context_files is not None:
            target_run.context_file = attempt.context_files
            self.logger.info(f"Override: context_file -> {attempt.context_files}")

        # Advance attempt counter for this (validator, block) for next time
        self._rerun_attempts[key] = current_attempt + 1

        # 🔁 Actually execute the target run NOW
        self.logger.info(
            f"[RERUN] Executing target run '{target_run.name}' after applying overrides."
        )
        target_result = self._execute_run_item(target_run)

        # For now we just log break/success; the main loop still controls pipeline flow.
        if target_result.should_break:
            self.logger.info(
                f"[RERUN] Target run '{target_run.name}' requested break during rerun "
                f"(this will be handled on its own turn in the pipeline, if needed)."
            )

        return True

