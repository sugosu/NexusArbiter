# core/runtime/pipeline_runner.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from core.config.run_config import RunConfig, RunItem, IncludeRuns
from core.logger import BasicLogger
from core.runtime.app_runner import RunResult
from core.runtime.run_executor import RunExecutor
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
        # IMPORTANT: set project_root first, then load strategies
        self.project_root = Path(project_root)
        self.config = config
        self.start_from = start_from


        # key = run_name -> attempt_number (starting at 1)
        self._run_attempt_counters: Dict[str, int] = {}

        # key = (validator_name, target_run_name, method, block_key) -> attempt_index
        # block_key kept for legacy; for method-based routing, block_key is usually (target_run_name, method)
        self._rerun_attempts: Dict[Tuple[str, str, str, Union[str, int, Tuple[Any, ...]]], int] = {}

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

    @staticmethod
    def _find_block_by_name(strategy: RerunStrategy, block_name: str) -> Optional[Any]:
        bn = (block_name or "").strip()
        if not bn:
            return None
        for b in getattr(strategy, "blocks", []) or []:
            if getattr(b, "name", None) == bn:
                return b
        return None

    @staticmethod
    def _find_block_by_name_and_method(strategy: RerunStrategy, block_name: str, method: str) -> Optional[Any]:
        bn = (block_name or "").strip()
        m = (method or "").strip()
        if not bn or not m:
            return None
        for b in getattr(strategy, "blocks", []) or []:
            if getattr(b, "name", None) == bn and getattr(b, "method", None) == m:
                return b
        return None

    @staticmethod
    def _find_block_by_method(strategy: RerunStrategy, method: str) -> Optional[Any]:
        """
        Legacy/escape hatch: Select a rerun block by strategy block.method only.

        Prefer name+method selection for determinism. Method-only selection is ambiguous
        if multiple blocks share the same method.
        """
        m = (method or "").strip()
        if not m:
            return None
        for b in getattr(strategy, "blocks", []) or []:
            if getattr(b, "method", None) == m:
                return b
        return None

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

            # v0.1: inline include_run / execute_run
            if self._maybe_inline_run(runs=runs, index=index, step=step):
                continue

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

                rerun_applied = self._handle_change_strategy(
                    runs=runs,
                    validator_run_item=run_item,
                    result=result,
                )
                if rerun_applied:
                    continue

                self.logger.info("[RERUN] No further attempts left for '%s'. Moving on.", run_item.name)

            index += 1

        self.logger.info("Pipeline completed.")

    # ----------------------------------------------------------------------
    # Include runs (v0.1 simplest)
    # ----------------------------------------------------------------------
    def _maybe_inline_run(self, runs: List[Any], index: int, step: Any) -> bool:
        include_paths: List[str] = []

        # --- New include type: IncludeRuns(include_runs=[...]) ---
        if isinstance(step, IncludeRuns):
            include_paths = list(step.include_runs)

        # --- Backward compat: object has include_run (single) ---
        if not include_paths and hasattr(step, "include_run"):
            val = getattr(step, "include_run")
            if val:
                include_paths = [str(val)]

        # --- Legacy/escape hatch: execute_run (single) ---
        if not include_paths and hasattr(step, "execute_run"):
            val = getattr(step, "execute_run")
            if val:
                include_paths = [str(val)]

        # --- Dict form support ---
        if not include_paths and isinstance(step, dict):
            if step.get("include_runs"):
                include_paths = [str(x) for x in step.get("include_runs") or []]
            else:
                single = step.get("include_run") or step.get("execute_run")
                if single:
                    include_paths = [str(single)]

        # Nothing to inline
        if not include_paths:
            return False

        # Validate
        include_paths = [p.strip() for p in include_paths if isinstance(p, str) and p.strip()]
        if not include_paths:
            raise ValueError(f"runs[{index}] include step has no valid paths.")

        # Inline each referenced runs file in order
        inlined: List[Any] = []
        for include_path in include_paths:
            include_rel = Path(include_path)
            include_abs = (self.project_root / include_rel).resolve()

            if include_abs in self._include_seen:
                raise ValueError(f"Include cycle detected: {include_abs}")

            if not include_abs.exists():
                raise FileNotFoundError(f"Included run file not found: {include_abs}")

            self._include_seen.add(include_abs)

            included_cfg = RunConfig.from_file(include_abs)
            included_runs = list(included_cfg.runs)

            self.logger.info("[INCLUDE_RUN] Inlining: %s", str(include_rel).replace("/", "\\"))
            inlined.extend(included_runs)

        # Replace the include step with the inlined runs
        runs[index : index + 1] = inlined
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
    def _handle_change_strategy(self, runs: List[Any], validator_run_item: RunItem, result: RunResult) -> bool:
        """
        Apply rerun strategy:
        - Select a rerun block deterministically using (target_run, requested_method)
          (explicit name is still supported as an escape hatch).
        - Modify target run's profile/provider/context
        - Execute target run immediately
        - Increment rerun attempt counter
        - Return True if validator should re-run
        """
        validator_name = validator_run_item.name

        if validator_run_item.target_run is None:
            self.logger.error("[RERUN] Validator '%s' has no target_run set.", validator_name)
            return False
        if validator_run_item.rerun_strategy is None:
            self.logger.error("[RERUN] Validator '%s' has no rerun_strategy file.", validator_name)
            return False

        # Resolve rerun strategy path relative to project_root
        strategy_file = (self.project_root / Path(validator_run_item.rerun_strategy)).resolve()
        if not strategy_file.exists():
            self.logger.error("[RERUN] Strategy file does not exist: %s", strategy_file)
            return False

        strategy = RerunStrategy.load(strategy_file)

        # Find target run
        target_name = validator_run_item.target_run
        target_run: Optional[RunItem] = next(
            (r for r in runs if isinstance(r, RunItem) and r.name == target_name),
            None,
        )
        if not target_run:
            self.logger.error("[RERUN] Target run '%s' not found in config.", target_name)
            return False

        # Determine requested method (from validator/model)
        requested_method = getattr(result, "change_strategy_method", None)
        if not (isinstance(requested_method, str) and requested_method.strip()):
            requested_method = "refiner"
        requested_method = requested_method.strip()

        # Authorize method via allow-list from runs.json
        allowed_methods = (
            getattr(validator_run_item, "rerun_methods", None)
            or getattr(target_run, "rerun_methods", None)
            or []
        )
        if allowed_methods and requested_method not in allowed_methods:
            self.logger.error(
                "[RERUN] Requested method '%s' is not allowed. Allowed=%s (validator=%s target=%s)",
                requested_method,
                allowed_methods,
                validator_run_item.name,
                target_run.name,
            )
            return False

        # ---- Select block (priority order) ----
        selected_block: Optional[Any] = None
        selected_key: Union[str, int, Tuple[str, str]] = ("", "")

        # 1) Explicit block name from model (escape hatch)
        explicit_name = getattr(result, "change_strategy_name", None)
        if isinstance(explicit_name, str) and explicit_name.strip():
            bn = explicit_name.strip()
            # Prefer exact match on (explicit name, requested method) if available
            selected_block = self._find_block_by_name_and_method(strategy, bn, requested_method) or self._find_block_by_name(strategy, bn)
            if selected_block is not None:
                selected_key = (getattr(selected_block, "name", None) or bn, getattr(selected_block, "method", None) or requested_method)
            else:
                self.logger.warning("[RERUN] Requested block name not found: %r", bn)

        # 2) Deterministic selection: (target_run name, requested_method)
        if selected_block is None:
            selected_block = self._find_block_by_name_and_method(strategy, target_run.name, requested_method)
            if selected_block is not None:
                selected_key = (target_run.name, requested_method)
            else:
                self.logger.warning(
                    "[RERUN] No rerun block matches (target=%r, method=%r).",
                    target_run.name,
                    requested_method,
                )

        # 3) Legacy default block name from runs.json (if present)
        if selected_block is None:
            default_bn = getattr(validator_run_item, "rerun_block_name", None)
            if isinstance(default_bn, str) and default_bn.strip():
                bn = default_bn.strip()
                selected_block = self._find_block_by_name_and_method(strategy, bn, requested_method) or self._find_block_by_name(strategy, bn)
                if selected_block is not None:
                    selected_key = (getattr(selected_block, "name", None) or bn, getattr(selected_block, "method", None) or requested_method)
                else:
                    self.logger.warning("[RERUN] rerun_block_name not found in strategy: %r", bn)

        # 4) Legacy rerun_index fallback (if present)
        if selected_block is None:
            idx = getattr(validator_run_item, "rerun_index", None)
            if isinstance(idx, int):
                blocks = getattr(strategy, "blocks", []) or []
                if 0 <= idx < len(blocks):
                    selected_block = blocks[idx]
                    selected_key = idx
                else:
                    self.logger.error("[RERUN] Invalid rerun_index=%s in validator '%s'.", idx, validator_name)
                    return False
            else:
                # As a last resort, allow method-only selection if strategy is global and unique per method.
                # This is intentionally lowest priority to avoid ambiguous routing.
                selected_block = self._find_block_by_method(strategy, requested_method)
                if selected_block is not None:
                    selected_key = (getattr(selected_block, "name", None) or "<unnamed>", requested_method)
                    self.logger.warning(
                        "[RERUN] Falling back to method-only block selection (method=%r). Consider adding name+method blocks per target.",
                        requested_method,
                    )
                else:
                    self.logger.error(
                        "[RERUN] No rerun block could be selected for validator '%s' (no explicit/target+method/default/index).",
                        validator_name,
                    )
                    return False

        block = selected_block
        assert block is not None

        # Attempt counters must distinguish refiner vs remake (and target) to avoid collisions.
        attempt_key = (validator_run_item.name, target_run.name, requested_method, selected_key)
        current_attempt = self._rerun_attempts.get(attempt_key, 0)

        attempts = getattr(block, "attempts", []) or []
        if current_attempt >= len(attempts):
            self.logger.info(
                "[RERUN] All rerun attempts exhausted for validator '%s' (target=%r method=%r block=%r).",
                validator_name,
                target_run.name,
                requested_method,
                selected_key,
            )
            return False

        attempt_cfg = attempts[current_attempt]

        # Apply overrides
        if attempt_cfg.profile_file:
            target_run.profile_file = attempt_cfg.profile_file
        if attempt_cfg.provider:
            target_run.provider_override = attempt_cfg.provider
        if attempt_cfg.context_files is not None:
            target_run.context_file = attempt_cfg.context_files
            self.logger.info("[RERUN] Context override applied: %s", ", ".join(attempt_cfg.context_files))


        # Target File Override
        if attempt_cfg.target_file:
            target_run.target_file = attempt_cfg.target_file
            self.logger.info("[RERUN] Target file override applied: %s", attempt_cfg.target_file)


        self.logger.info(
            "[RERUN] Applying rerun attempt %s/%s for target '%s' (method=%r block=%r).",
            current_attempt + 1,
            len(attempts),
            target_run.name,
            requested_method,
            selected_key,
        )

        # Consume attempt
        self._rerun_attempts[attempt_key] = current_attempt + 1

        # Execute target run immediately with a new attempt number
        attempt_number = self._increment_attempt(target_run)
        self.logger.info("[RERUN] Executing target run '%s' with attempt=%s", target_run.name, attempt_number)

        _ = self._execute_run_item(target_run, attempt_number)

        # Validator will run again
        return True
