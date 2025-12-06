# core/runtime/run_executor.py
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Dict, Any

from core.config.run_config import RunItem
from core.runtime.app_runner import AppRunner, RunResult
from core.logger import BasicLogger



class RunExecutor:
    """
    Executes a single run (one RunItem) and returns a RunResult.

    Responsibilities:
    - Prepare parameters for AppRunner.
    - Pass attempt_number and log_io_settings down.
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.logger = BasicLogger("RunExecutor").get_logger()

        # One AppRunner instance is reused, as before
        self.app_runner = AppRunner(project_root=self.project_root)

    # ------------------------------------------------------------------
    def execute_once(
        self,
        run_item: RunItem,
        context_files: List[str],
        profile_file: str,
        target_file: Optional[str],
        provider_override: Optional[str],
        attempt_number: int,
        log_io_settings: Dict[str, Any],
    ) -> RunResult:
        """
        Execute a run once with the given parameters.

        run_item: the configuration block describing this run
        attempt_number: an integer representing the N-th attempt of this run
        log_io_settings: merged global + per-run logging rules
        """

        self.logger.info(
            f"[RunExecutor] Starting run '{run_item.name}' "
            f"(attempt={attempt_number}) using profile '{profile_file}'"
        )

        # Various metadata that AppRunner may use
        run_params: Dict[str, Any] = {
            "context_files": context_files,
            "profile_file": profile_file,
            "target_file": target_file,
            "provider_override": provider_override,
            "attempt_number": attempt_number,
            "log_io_settings": log_io_settings,
        }

        # AppRunner.execute() returns a RunResult
        result: RunResult = self.app_runner.run(
            run_item=run_item,
            run_params=run_params,
            profile_name=run_item.profile_name,
            class_name=None,  # legacy field, unused for modern runs
            task_description=run_item.task_description,
            agent_input_overrides={},  # modern flows rely on run_params instead
        )

        return result
