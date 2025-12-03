# core/runtime/app_runner.py
from __future__ import annotations

import json
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


def _register_builtin_actions() -> None:
    """Import all built-in action modules so they self-register.

    Each imported module must call ``ActionRegistry.register(...)`` at import
    time. This helper is invoked once from :class:`AppRunner`'s constructor.
    """
    # Core file / IO actions
    import core.actions.file_write  # noqa: F401
    import core.actions.file_read  # noqa: F401

    # Control-flow / meta actions
    import core.actions.continue_action  # noqa: F401
    import core.actions.request_retry  # noqa: F401
    import core.actions.trigger_retry  # noqa: F401
    import core.actions.break_action  # noqa: F401


@dataclass
class RunResult:
    """Result of a single model invocation + action execution."""

    success: bool
    retry_requested: bool = False
    retry_reason: Optional[str] = None


@dataclass
class ActionRuntimeContext(ActionContext):
    """Concrete runtime context passed to actions.

    Extends :class:`ActionContext` with additional fields used by the
    orchestrator (retry flags, enforced target file, etc.).
    """

    target_file: Optional[str] = None
    retry_requested: bool = False
    retry_reason: Optional[str] = None


def execute_actions(actions_list: List[Dict[str, Any]], ctx: ActionRuntimeContext) -> None:
    """Instantiate and execute actions using :class:`ActionRegistry`.

    Behaviour:

    * Unknown or unregistered actions are skipped with a warning.
    * If ``ctx.target_file`` is set and an action is ``file_write``, its
      path is overridden by ``ctx.target_file``.
    * If ``ctx.target_file`` is empty/None and an action is ``file_write``,
      that action is skipped.
    * If an action of type ``break`` is executed, remaining actions in the
      list are not executed.
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

            # Override any model-provided path; run.target_file is the SSoT
            if hasattr(action, "params") and isinstance(action.params, dict):
                action.params["target_path"] = ctx.target_file

        logger.info("Executing action #%s: %s", index, action.action_type)
        action.execute(ctx)

        # Logical break in action sequence
        if action.action_type == "break":
            logger.info(
                "Encountered 'break' action at index %s; stopping further action execution.",
                index,
            )
            break


class AppRunner:
    """High-level orchestrator for one model call + action execution.

    Responsibilities:

    * Initialize infrastructure (logging, Git, filesystem, model client).
    * Inject task / rules / agent_input / context into the profile payload.
    * Call the selected provider (currently OpenAI only).
    * Filter and execute actions via :class:`ActionRegistry`.
    * Surface ``success`` / ``retry_requested`` flags for retry logic.
    """

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)

        self.logger = BasicLogger(self.__class__.__name__).get_logger()

        # Repo / Git setup
        repo_path = os.getenv("AIAGENCY_REPO_PATH", str(self.project_root))
        self.repo_config = RepoConfig(repo_path=repo_path)
        self.git_client = GitClient(repo_path=repo_path)
        # FIX: GitManager currently takes only git_client
        self.git_manager = GitManager(self.git_client)

        # File IO
        self.file_writer = FileWriter(project_root=self.project_root)

        # Default provider (used when runs do not specify one)
        env_default_provider = os.getenv("AIAGENCY_DEFAULT_PROVIDER", "openai")
        self.default_provider: str = (env_default_provider or "openai").strip().lower()
        if not self.default_provider:
            self.default_provider = "openai"

        # OpenAI client (currently the only fully wired provider)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in the environment.")

        self.client = OpenAIClient(api_key=api_key)

        # Ensure built-in actions are registered
        _register_builtin_actions()


    # ------------------------------------------------------------------ #
    # Core run orchestration
    # ------------------------------------------------------------------ #
    def _resolve_provider_for_run(self, run_item: RunItem) -> str:
        """
        Decide which provider to use for this run.

        Precedence (lowest -> highest):
        - self.default_provider (from env, default "openai")
        - run_item.provider (from runs.json)

        For now, only "openai" is implemented. Any other value results in a
        clear RuntimeError so misconfiguration is caught early.
        """
        provider = (run_item.provider or self.default_provider or "openai").strip().lower()
        if not provider:
            provider = "openai"

        if provider != "openai":
            # Placeholder for future multi-provider support.
            raise RuntimeError(
                f"Provider '{provider}' is not wired into AppRunner yet. "
                "Currently only 'openai' is supported."
            )

        return provider

    def run(
        self,
        run_item: RunItem,
        run_params: Dict[str, Any],
        profile_name: str,
        class_name: Optional[str],
        task_description: str,
        agent_input_overrides: Optional[Dict[str, Any]] = None,
    ) -> RunResult:
        """
        Execute one model call + follow-up actions for a single run item.

        :param run_item:             The RunItem config.
        :param run_params:           The raw profile JSON loaded from disk
                                     (or otherwise constructed).
        :param profile_name:         Logical label for logging (usually the
                                     profile file path).
        :param class_name:           Optional class/function name for context.
        :param task_description:     Human-readable description of the run.
        :param agent_input_overrides:
                                     Additional fields that will be merged into
                                     the agent_input structure for this run.
        """
        logger = self.logger

        # ------------------------------------------------------------------ #
        # 0. Provider selection
        # ------------------------------------------------------------------ #
        provider = self._resolve_provider_for_run(run_item)
        logger.info(
            "Selected provider '%s' for profile '%s' (class=%r, target_file=%r)",
            provider,
            profile_name,
            class_name,
            run_item.target_file or "<none>",
        )

        # ------------------------------------------------------------------ #
        # 1. Load + enrich profile JSON
        # ------------------------------------------------------------------ #
        from core.prompt.agent_input_builder import (
            build_agent_input,
            build_rules_block_for_run,
            inject_placeholders,
        )

        # Build agent_input based on run + overrides
        agent_input_obj = build_agent_input(
            run_item=run_item,
            profile_name=profile_name,
            class_name=class_name,
            base_agent_input=agent_input_overrides or {},
        )

        # Build rules block
        rules_block = build_rules_block_for_run(run_item)

        # Ensure run_params is a dict so we can modify in-place
        if not isinstance(run_params, dict):
            raise ValueError("run_params must be a dict loaded from profile JSON")

        # Optional: load + inject context block (based on _context_files_display)
        context_files_display = run_params.get("_context_files_display", [])
        if isinstance(context_files_display, List) and context_files_display:
            # Build a concatenated context string (for debugging/prompting)
            text_blocks: List[str] = []
            for rel in context_files_display:
                try:
                    full_path = (self.project_root / rel).resolve()
                    if full_path.is_file():
                        with full_path.open("r", encoding="utf-8") as f:
                            raw = f.read()
                    else:
                        continue
                except OSError:
                    continue

                header = f"=== CONTEXT FILE: {rel} ===\n"
                text_blocks.append(header + raw.strip() + "\n")

            if text_blocks:
                context_block = "\n\n".join(text_blocks)
                run_params["_context_block"] = context_block

        # Remove meta fields before injection
        if "_context_files_display" in run_params:
            del run_params["_context_files_display"]

        # Inject placeholders into the model payload
        inject_placeholders(
            run_params=run_params,
            agent_input_obj=agent_input_obj,
            rules_block=rules_block,
            task_description=task_description,
            target_file=run_item.target_file or "",
            context_block=run_params.get("_context_block", ""),
        )

        if "_context_block" in run_params:
            # The context block is injected into messages; no need to keep
            # it at the top level.
            del run_params["_context_block"]

        # ------------------------------------------------------------------ #
        # 2. Call provider (currently OpenAI)
        # ------------------------------------------------------------------ #
        logger.info(
            "Starting model call via provider '%s' for profile '%s'.",
            provider,
            profile_name,
        )

        # For now, provider == "openai" is guaranteed here.
        response = self.client.send_request(body=run_params)

        # ------------------------------------------------------------------ #
        # 3. Extract agent + actions
        # ------------------------------------------------------------------ #
        agent = AIResponseParser.extract_agent(response)
        logger.info("Extracted agent object: %s", json.dumps(agent, indent=2))

        actions = AIResponseParser.extract_actions(response)
        logger.info("Extracted %d actions.", len(actions))

        if not actions:
            logger.warning("No actions returned by the model.")
            return RunResult(success=False, retry_requested=False)

        # ------------------------------------------------------------------ #
        # 4. Validate agent / actions shape
        # ------------------------------------------------------------------ #
        if not isinstance(agent, dict):
            logger.warning("Agent is not a dict; raw agent: %r", agent)
        else:
            if "name" not in agent or "version" not in agent:
                logger.warning("Agent object missing 'name' or 'version': %r", agent)

        # ------------------------------------------------------------------ #
        # 5. Validate and possibly early-return if no actions are available
        # ------------------------------------------------------------------ #
        # Enforce per-run allowed_actions against registry membership
        effective_allowed: Optional[List[str]] = None
        if getattr(run_item, "allowed_actions", None):
            registered = set(ActionRegistry.allowed_types())
            effective_allowed = [
                t for t in run_item.allowed_actions if t in registered
            ]
            if not effective_allowed:
                logger.warning(
                    "Run has 'allowed_actions' but none match registered actions; "
                    "all actions from the model will be rejected.",
                )
                return RunResult(success=False, retry_requested=False)

        if effective_allowed is not None:
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
        # Special case: a single 'continue' action
        if len(filtered_actions) == 1 and filtered_actions[0].get("type") == "continue":
            logger.info(
                "Agent returned only a 'continue' action; "
                "interpreting this as a successful no-op run.",
            )
            return RunResult(success=True, retry_requested=False)


        # ------------------------------------------------------------------ #
        # 6. Execute actions with runtime context (including enforced target_file)
        # ------------------------------------------------------------------ #
        runtime_ctx = ActionRuntimeContext(
            project_root=self.project_root,
            file_writer=self.file_writer,
            git_manager=self.git_manager,
            repo_config=self.repo_config,
            logger=logger,
            target_file=run_item.target_file or None,
        )

        execute_actions(filtered_actions, runtime_ctx)
        logger.info("All actions executed.")

        # ------------------------------------------------------------------ #
        # 7. Retry semantics
        # ------------------------------------------------------------------ #
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
