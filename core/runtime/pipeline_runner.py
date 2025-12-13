# core/runtime/pipeline_runner.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from core.config.run_config import RunConfig, RunItem
from core.logger import BasicLogger
from core.runtime.run_executor import RunExecutor
from core.runtime.app_runner import RunResult
from core.strategy.rerun_strategy import RerunStrategy


class PipelineRunner:
    """
    Executes a sequence of runs from a RunConfig.

    Responsibilities:
    - Maintain run index.
    - Track attempt numbers for each run (including reruns).
    - Delegate execution to RunExecutor.execute_once(...)
    - Handle rerun requests via _handle_change_strategy.
    - Inline include_run/execute_run entries (v0.1 simplest).
    """

    def __init__(
        self,
        project_root: Path,
        config: RunConfig,
        start_from: Optional[int] = 0,
    ):
        self.project_root = Path(project_root)
        self.config = config
        self.start_from = start_from

        # key = run_name -> attempt_number (starting at 1)
        self._run_attempt_counters: Dict[str, int] = {}

        # key = (validator_name, rerun_index) -> attempt_index
        self._rerun_attempts: Dict[Tuple[str, int], int] = {}

        self.executor = RunExecutor(project_root=str(self.project_root))
        self.logger = BasicLogger("PipelineRunner").get_logger()

        # Prevent accidental include cycles
        self._include_seen: Set[Path] = set()

    # ----------------------------------------------------------------------
    # Utilities
    # ----------------------------------------------------------------------
    def _increment_attempt(self, run_item: RunItem) -> int:
        name = run_item.name
        prev = self._run_attempt_counters.get(name, 0)
        curr = prev + 1
        self._run_attempt_counters[name] = curr
        return curr

    # ----------------------------------------------------------------------
    # Main run loop
    # ----------------------------------------------------------------------
    def run(self) -> None:
        self.logger.info("Warp fields stabilized")
        self.logger.info("Pipeline started")

        runs: List[Any] = list(self.config.runs)  # keep mutable local view
        index = 0

        if self.start_from is not None and self.start_from >= len(runs):
            self.logger.warning(
                "start_from=%s is beyond total runs (%s). Nothing to execute.",
                self.start_from,
                len(runs),
            )
            self.logger.info("Pipeline completed.")
            return

        while index < len(runs):
            if self.start_from is not None and index < self.start_from:
                self.logger.info("[RUN SKIPPED] index=%s < start_from=%s", index, self.start_from)
                index += 1
                continue

            step = runs[index]

            # v0.1: inline include_run / execute_run (supports both IncludeRun objects and legacy dict-like RunItem)
            if self._maybe_inline_run(runs=runs, index=index, step=step):
                continue  # newly inserted runs start at same index

            # At this point, we must have a RunItem
            if not isinstance(step, RunItem):
                raise TypeError(f"runs[{index}] is not a RunItem after include resolution: {type(step)!r}")

            run_item: RunItem = step
            attempt_number = self._increment_attempt(run_item)
            self.logger.info("[RUN] Starting '%s' attempt=%s", run_item.name, attempt_number)

            result = self._execute_run_item(run_item, attempt_number)

            if result.should_break:
                self.logger.info(
                    "[BREAK] Pipeline terminated by '%s'. Reason=%r",
                    run_item.name,
                    result.change_strategy_reason,
                )
                break

            if result.change_strategy_requested:
                self.logger.info(
                    "[RERUN] '%s' requested strategy change. Reason=%r",
                    run_item.name,
                    result.change_strategy_reason,
                )

                rerun_applied = self._handle_change_strategy(runs=runs, validator_run_item=run_item)
                if rerun_applied:
                    # Validator wants to run again, do not move index
                    continue

                self.logger.info("[RERUN] No further attempts left for '%s'. Moving on.", run_item.name)

            index += 1

        self.logger.info("Pipeline completed.")

    # ----------------------------------------------------------------------
    # Include runs (v0.1 simplest)
    # ----------------------------------------------------------------------
    def _maybe_inline_run(self, runs: List[Any], index: int, step: Any) -> bool:
        """
        If step represents include_run/execute_run, replace it with the runs
        loaded from that file. Returns True if inlining happened.
        """

        # Support new IncludeRun dataclass OR legacy include fields on RunItem-like objects
        include_path = None

        # New style: dataclass with attribute include_run
        if hasattr(step, "include_run"):
            include_path = getattr(step, "include_run")

        # Legacy style: sometimes called execute_run
        if not include_path and hasattr(step, "execute_run"):
            include_path = getattr(step, "execute_run")

        # Also support dict steps if any exist in the list (defensive)
        if not include_path and isinstance(step, dict):
            include_path = step.get("include_run") or step.get("execute_run")

        if not include_path:
            return False

        include_rel = Path(str(include_path))
        include_abs = (self.project_root / include_rel).resolve()

        if include_abs in self._include_seen:
            raise ValueError(f"Include cycle detected: {include_abs}")

        if not include_abs.exists():
            raise FileNotFoundError(f"Included run file not found: {include_abs}")

        self._include_seen.add(include_abs)

        included_cfg = RunConfig.from_file(include_abs)
        included_runs = list(included_cfg.runs)

        self.logger.info("[INCLUDE_RUN] Inlining: %s", str(include_rel).replace("/", "\\"))

        # Replace the include item with the included runs
        runs[index:index + 1] = included_runs
        return True

    # ----------------------------------------------------------------------
    # Run execution wrapper
    # ----------------------------------------------------------------------
    def _execute_run_item(self, run_item: RunItem, attempt_number: int) -> RunResult:
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
        global_cfg = self.config.log_io_settings
        merged: Dict[str, Any] = {
            "enabled": global_cfg.enabled,
            "log_dir": global_cfg.log_dir,
            "request_file_pattern": global_cfg.request_file_pattern,
            "response_file_pattern": global_cfg.response_file_pattern,
        }

        override = run_item.log_io_override or {}
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
    # Rerun handling (strategy change)
    # ----------------------------------------------------------------------
    def _handle_change_strategy(self, runs: List[Any], validator_run_item: RunItem) -> bool:
        """
        Apply rerun strategy:
        - Modify target run's profile/provider/context
        - Execute target run immediately
        - Increment rerun attempt counter
        - Return True if validator should re-run
        """
        name = validator_run_item.name

        if validator_run_item.target_run is None:
            self.logger.error("[RERUN] Validator '%s' has no target_run set.", name)
            return False
        if validator_run_item.rerun_strategy is None:
            self.logger.error("[RERUN] Validator '%s' has no rerun_strategy file.", name)
            return False
        if validator_run_item.rerun_index is None:
            self.logger.error("[RERUN] Validator '%s' has no rerun_index.", name)
            return False

        # IMPORTANT: resolve strategy path relative to project_root (consistent with include_run)
        strategy_file = (self.project_root / Path(validator_run_item.rerun_strategy)).resolve()
        if not strategy_file.exists():
            self.logger.error("[RERUN] Strategy file does not exist: %s", strategy_file)
            return False

        strategy = RerunStrategy.from_file(strategy_file)
        blocks = strategy.blocks

        idx = validator_run_item.rerun_index
        if idx < 0 or idx >= len(blocks):
            self.logger.error("[RERUN] Invalid rerun_index=%s in validator '%s'.", idx, name)
            return False

        block = blocks[idx]
        key = (validator_run_item.name, idx)
        current_attempt = self._rerun_attempts.get(key, 0)

        if current_attempt >= len(block.attempts):
            self.logger.info("[RERUN] All rerun attempts exhausted for validator '%s'.", name)
            return False

        attempt_cfg = block.attempts[current_attempt]

        # Find target run (RunItem only)
        target_name = validator_run_item.target_run
        target_run: Optional[RunItem] = next(
            (r for r in runs if isinstance(r, RunItem) and r.name == target_name),
            None,
        )
        if not target_run:
            self.logger.error("[RERUN] Target run '%s' not found in config.", target_name)
            return False

        # Apply overrides
        if attempt_cfg.profile_file:
            target_run.profile_file = attempt_cfg.profile_file
        if attempt_cfg.provider:
            target_run.provider_override = attempt_cfg.provider
        if attempt_cfg.context_files is not None:
            target_run.context_file = attempt_cfg.context_files
            self.logger.info("[RERUN] Context override applied: %s", ", ".join(attempt_cfg.context_files))

        self.logger.info(
            "[RERUN] Applying rerun attempt %s/%s for target '%s'.",
            current_attempt + 1,
            len(block.attempts),
            target_run.name,
        )

        # Consume attempt
        self._rerun_attempts[key] = current_attempt + 1

        # Execute target run immediately with a new attempt number
        attempt_number = self._increment_attempt(target_run)
        self.logger.info("[RERUN] Executing target run '%s' with attempt=%s", target_run.name, attempt_number)

        _ = self._execute_run_item(target_run, attempt_number)

        # Validator will run again
        return True
