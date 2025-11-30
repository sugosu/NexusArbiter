# core/runtime/app_runner.py
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import BasicLogger
from core.ai_client.openai_client import OpenAIClient
from core.ai_client.ai_response_parser import AIResponseParser
from core.files.file_writer import FileWriter
from core.actions.registry import ActionRegistry
from core.actions.base_action import ActionContext
from core.git.repo_config import RepoConfig
from core.git.git_client import GitClient
from core.git.git_manager import GitManager
from core.config.run_config import RunItem
from core.prompt.agent_input_builder import (
    build_agent_input,
    build_rules_block_for_run,
    inject_placeholders,
)


@dataclass
class RunResult:
    """Result of a single model invocation / action execution cycle."""

    success: bool
    retry_requested: bool = False
    retry_reason: Optional[str] = None


@dataclass
class ActionRuntimeContext(ActionContext):
    """Concrete runtime context passed to actions.

    Extends ActionContext with additional fields used by specific actions and
    by the orchestrator (e.g. retry flags, enforced target file).
    """

    target_file: Optional[str] = None
    retry_requested: bool = False
    retry_reason: Optional[str] = None


def execute_actions(actions_list: List[Dict[str, Any]], ctx: ActionRuntimeContext) -> None:
    """Instantiate and execute actions using the registry.

    Enforces the invariant:
    - If ctx.target_file is set and an action is 'file_write', its path is overridden by ctx.target_file.
    - If ctx.target_file is empty/None and an action is 'file_write', that action is skipped.
    """
    logger = ctx.logger

    for index, raw in enumerate(actions_list, start=1):
        action = ActionRegistry.create(raw)
        if action is None:
            logger.warning(
                "Unknown or unregistered action '%s'. Allowed: %s",
                raw.get("type"),
                ActionRegistry.allowed_types(),
            )
            continue

        if not action.validate():
            logger.warning(
                "Invalid params for action '%s': %r", action.action_type, raw
            )
            continue

        # Enforce target_file contract for file_write actions
        if action.action_type == "file_write":
            if not ctx.target_file:
                logger.warning(
                    "Skipping file_write action #%s: run has no target_file set.",
                    index,
                )
                continue

            # Override any model-provided path; run.target_file is the single source of truth
            if hasattr(action, "params") and isinstance(action.params, dict):
                action.params["target_path"] = ctx.target_file

        logger.info("Executing action #%s: %s", index, action.action_type)
        action.execute(ctx)


class AppRunner:
    """High-level orchestrator for one OpenAI call + action execution.

    Responsibilities:
    - Initialize infrastructure (logging, Git, file system, OpenAI client).
    - Build agent_input and inject it + rules/context into the payload.
    - Call OpenAI and parse an 'agent' response.
    - Filter and execute actions via the registry.
    - Surface success / retry_requested flags to the outer orchestration layer.
    """

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root

        self.logger = BasicLogger(__name__).get_logger()

        # Git / repo configuration
        repo_config = RepoConfig(
            repo_path=str(project_root),
            default_branch="master",
            remote_name="origin",
            author_name="Onat Agent",
            author_email="onat@gegeoglu.com",
        )
        self.repo_config = repo_config
        self.git_client = GitClient(repo_path=repo_config.repo_path)
        self.git_manager = GitManager(git_client=self.git_client)

        # File writer for side effects
        self.file_writer = FileWriter(project_root=project_root)

        # OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in environment")

        self.client = OpenAIClient(api_key=api_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        run_item: RunItem,
        run_params: Dict[str, Any],
        profile_name: str,
        class_name: Optional[str],
        task_description: str,
        agent_input_overrides: Dict[str, Any],
    ) -> RunResult:
        """Execute a single model call + actions for the given run.

        `run_params` must already be a valid OpenAI payload (model, messages, ...).
        Any meta key `_context_block` is consumed and injected into prompts.
        """
        logger = self.logger
        logger.info("Starting AppRunner for profile '%s'", profile_name)

        # For logging: which context files were actually used for this run
        context_files_display = run_params.pop("_context_files_display", None)
        if context_files_display:
            logger.info("Using context files: %s", context_files_display)

        # Build agent_input, rules, and inject placeholders into messages
        agent_input_obj = build_agent_input(
            run_item=run_item,
            profile_name=profile_name,
            class_name=class_name,
            base_agent_input=agent_input_overrides,
        )

        rules_block = build_rules_block_for_run(run_item)
        context_block = run_params.pop("_context_block", "")

        inject_placeholders(
            run_params=run_params,
            agent_input_obj=agent_input_obj,
            rules_block=rules_block,
            task_description=task_description,
            target_file=run_item.target_file,
            context_block=context_block,
        )

        # Call OpenAI
        logger.info("Calling OpenAI for profile '%s'", profile_name)
        response = self.client.send_request(body=run_params)

        # Parse agent + actions
        agent_obj = AIResponseParser.extract_agent(response)
        if not agent_obj:
            logger.error("Model did not return a valid 'agent' object. Aborting.")
            return RunResult(success=False, retry_requested=False)

        actions = agent_obj.get("actions", [])
        if not isinstance(actions, list) or not actions:
            logger.warning("No actions returned by the model.")
            return RunResult(success=False, retry_requested=False)

        # Per-run allowed_actions (from config)
        effective_allowed: Optional[List[str]] = None
        if run_item and run_item.allowed_actions:
            registered = set(ActionRegistry.allowed_types())
            effective_allowed = [
                t for t in run_item.allowed_actions if t in registered
            ]
            if not effective_allowed:
                logger.warning(
                    "Run has 'allowed_actions' but none match registered actions; "
                    "all actions from the model will be rejected."
                )

        if effective_allowed:
            filtered_actions = [
                a for a in actions if a.get("type") in effective_allowed
            ]
        else:
            # No per-run restriction: accept anything the registry knows
            filtered_actions = [
                a for a in actions if a.get("type") in ActionRegistry.allowed_types()
            ]

        if not filtered_actions:
            logger.warning(
                "No actions left after allowed_actions / registry filtering. "
                "Original actions: %r",
                actions,
            )
            return RunResult(success=False, retry_requested=False)

        # Special case: a single 'continue' action means "no final side effects yet"
        if len(filtered_actions) == 1 and filtered_actions[0].get("type") == "continue":
            logger.info(
                "Agent returned only a 'continue' action; "
                "no side effects will be executed for this attempt."
            )
            return RunResult(success=False, retry_requested=False)

        # Execute actions with runtime context including enforced target_file
        runtime_ctx = ActionRuntimeContext(
            project_root=self.project_root,
            file_writer=self.file_writer,
            git_manager=self.git_manager,
            repo_config=self.repo_config,
            logger=logger,
            target_file=run_item.target_file,
        )

        execute_actions(filtered_actions, runtime_ctx)
        logger.info("All actions executed.")

        if runtime_ctx.retry_requested:
            logger.info(
                "Run requested retry. Reason: %s",
                runtime_ctx.retry_reason or "<no reason>",
            )
            return RunResult(
                success=False,
                retry_requested=True,
                retry_reason=runtime_ctx.retry_reason,
            )

        return RunResult(success=True, retry_requested=False)
