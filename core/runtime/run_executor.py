# core/runtime/run_executor.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config.run_config import RunItem
from core.logger import BasicLogger
from core.runtime.app_runner import AppRunner, RunResult


class RunExecutor:
    """Executes a single RunItem once and returns a RunResult."""

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root)
        self.logger = BasicLogger("RunExecutor").get_logger()
        self.app_runner = AppRunner(project_root=self.project_root)

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
        self.logger.info(
            "[RunExecutor] Starting run '%s' (attempt=%s) using profile '%s'",
            run_item.name,
            attempt_number,
            profile_file,
        )

        if context_files:
            self.logger.info("[RunExecutor] Context paths: %s", ", ".join(context_files))
        else:
            self.logger.info("[RunExecutor] Context paths: <none>")

        run_params: Dict[str, Any] = {
            "context_files": context_files,
            "profile_file": profile_file,
            "target_file": target_file,
            "provider_override": provider_override,
            "attempt_number": attempt_number,
            "log_io_settings": log_io_settings,
        }

        return self.app_runner.run(
            run_item=run_item,
            run_params=run_params,
            profile_name=getattr(run_item, "profile_name", None),
            class_name=None,  # legacy field, intentionally unused in modern runs
            task_description=getattr(run_item, "task_description", None),
            agent_input_overrides={},  # modern flows rely on run_params instead
        )
