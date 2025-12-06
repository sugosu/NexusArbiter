# tests/conftest.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import logging
import pytest

from core.actions.base_action import ActionContext
from core.logger import BasicLogger


@pytest.fixture
def tmp_project_root(tmp_path: Path) -> Path:
    """
    Temporary project root used for tests.
    You can point it to your real project later if needed.
    """
    return tmp_path


@pytest.fixture
def test_logger() -> logging.Logger:
    """
    Basic logger for tests – uses the same BasicLogger,
    but you could also plug a NullHandler if you want silence.
    """
    return BasicLogger("test-logger", log_to_file=False).get_logger()


def make_action_context(
    project_root: Path,
    logger: logging.Logger,
    target_file: Optional[str] = None,
    run_name: str = "test_run",
    run_item: Any = None,
) -> ActionContext:
    """
    Helper to construct a minimal ActionContext for action tests.
    """
    return ActionContext(
        project_root=str(project_root),
        target_file=target_file,
        run_name=run_name,
        run_item=run_item,
        logger=logger,
    )
