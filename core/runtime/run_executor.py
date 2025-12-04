from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.logger import BasicLogger
from core.runtime.app_runner import AppRunner
from core.config.run_config import RunItem


# ---------------------------------------------------------------------------
# Result returned to PipelineRunner after a single run execution
# ---------------------------------------------------------------------------

@dataclass
class RunResult:
    success: bool
    change_strategy_requested: bool = False
    change_strategy_reason: Optional[str] = None
    should_break: bool = False


# ---------------------------------------------------------------------------
# RunExecutor — runs a single step by invoking AppRunner
# ---------------------------------------------------------------------------

class RunExecutor:
    """
    Executes individual run steps.

    Responsibilities:
    - Invoke AppRunner.run_single()
    - Convert its ActionContext into a RunResult
    - NO RETRY LOGIC HERE. That belongs to PipelineRunner.
    """

    def __init__(self, project_root: str | None):
        self.project_root = project_root
        self.app_runner = AppRunner(project_root)
        self.logger = BasicLogger("RunExecutor")

    # ------------------------------------------------------------------
    # Executes a single run step once (no retry loops here)
    # ------------------------------------------------------------------
    def execute_once(
        self,
        run_item: RunItem,
        context_files: list[str],
        profile_file: str,
        target_file: str | None,
        provider_override: str | None
    ) -> RunResult:

        ctx = self.app_runner.run_single(
            run_item=run_item,
            profile_file=profile_file,
            context_files=context_files,
            target_file=target_file,
            provider_override=provider_override,
        )

        # Convert ctx flags → RunResult
        result = RunResult(
            success=not ctx.change_strategy_requested and not ctx.should_break,
            change_strategy_requested=ctx.change_strategy_requested,
            change_strategy_reason=ctx.change_strategy_reason,
            should_break=ctx.should_break,
        )

        return result
