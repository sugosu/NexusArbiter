# tests/test_rerun_action.py
from __future__ import annotations

from typing import Dict

from core.actions.base_action import ActionContext
from core.actions.rerun_action import RerunAction
from tests.conftest import make_action_context


def _make_ctx(tmp_project_root, test_logger) -> ActionContext:
    return make_action_context(
        project_root=tmp_project_root,
        logger=test_logger,
        target_file=None,
        run_name="validator_test",
        run_item=None,
    )


def test_rerun_action_sets_flags_with_reason(tmp_project_root, test_logger):
    ctx = _make_ctx(tmp_project_root, test_logger)
    params: Dict[str, str] = {"reason": "Validator rejected code"}

    action = RerunAction()
    action.execute(ctx, params)

    assert ctx.change_strategy_requested is True
    assert ctx.change_strategy_reason == "Validator rejected code"
    # It should end the current run, but not break the whole pipeline
    assert ctx.should_continue is False
    assert ctx.should_break is False


def test_rerun_action_default_reason(tmp_project_root, test_logger):
    ctx = _make_ctx(tmp_project_root, test_logger)

    action = RerunAction()
    # No params provided
    action.execute(ctx, None)

    assert ctx.change_strategy_requested is True
    assert ctx.change_strategy_reason is not None
    assert "No reason" in ctx.change_strategy_reason
    assert ctx.should_continue is False
    assert ctx.should_break is False
