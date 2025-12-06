from __future__ import annotations

from pathlib import Path
from typing import Dict

from core.actions.base_action import ActionContext
from core.actions.file_write_action import FileWriteAction
from tests.conftest import make_action_context


def _make_ctx(tmp_project_root, test_logger, target_file: str) -> ActionContext:
    return make_action_context(
        project_root=tmp_project_root,
        logger=test_logger,
        target_file=target_file,
        run_name="file_write_run",
        run_item=None,
    )


def test_file_write_action_writes_to_target(tmp_project_root, test_logger):
    target_rel = "out/test_file.txt"
    target_path = tmp_project_root / target_rel

    ctx = _make_ctx(tmp_project_root, test_logger, target_rel)

    params: Dict[str, str] = {
        "target_path": target_rel,  # or let your action default to ctx.target_file
        "code": "Hello from test",
    }

    action = FileWriteAction()
    action.execute(ctx, params)

    assert target_path.exists()
    assert target_path.read_text(encoding="utf-8") == "Hello from test"
