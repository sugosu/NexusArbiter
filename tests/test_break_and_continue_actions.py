# tests/test_break_and_continue_actions.py
from __future__ import annotations

from typing import Dict

from core.actions.base_action import ActionContext
from core.actions.break_action import BreakAction
from core.actions.continue_action import ContinueAction
from tests.conftest import make_action_context


def _make_ctx(tmp_project_root, test_logger) -> ActionContext:
    return make_action_context(
        project_root=tmp_project_root,
        logger=test_logger,
        target_file=None,
        run_name="simple_run",
        run_item=None,
    )


def test_break_action_sets_break_flag(tmp_project_root, test_logger):
    ctx = _make_ctx(tmp_project_root, test_logger)

    params: Dict[str, str] = {"reason": "User requested stop"}
    action = BreakAction()
    action.execute(ctx, params)

    assert ctx.should_break is True
    assert ctx.should_continue is False


def test_continue_action_sets_continue_flag(tmp_project_root, test_logger):
    ctx = _make_ctx(tmp_project_root, test_logger)

    params: Dict[str, str] = {"reason": "Validation ok"}
    action = ContinueAction()
    action.execute(ctx, params)

    assert ctx.should_continue is True
    # continue should not trigger a break
    assert ctx.should_break is False
