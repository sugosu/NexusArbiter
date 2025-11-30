# app/app.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from core.config.run_config import RunItem
from core.runtime.app_runner import AppRunner, RunResult


def main(
    profile_name: str,
    class_name: Optional[str],
    task_description: str,
    agent_input: Dict[str, Any],
    run_item: RunItem,
    run_params: Dict[str, Any],
) -> Dict[str, bool]:
    """Thin wrapper around AppRunner (kept for backward compatibility)."""
    project_root = Path(__file__).resolve().parents[1]
    runner = AppRunner(project_root=project_root)

    result: RunResult = runner.run(
        run_item=run_item,
        run_params=run_params,
        profile_name=profile_name,
        class_name=class_name,
        task_description=task_description,
        agent_input_overrides=agent_input,
    )

    return {
        "success": result.success,
        "retry_requested": result.retry_requested,
    }
