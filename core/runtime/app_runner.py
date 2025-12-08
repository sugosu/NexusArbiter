# core/runtime/app_runner.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import BasicLogger
from core.actions.registry import ActionRegistry
from core.actions.base_action import ActionContext, BaseAction
from core.ai_client.openai_client import OpenAIClient
from core.ai_client.gemini_client import GeminiClient


class RunResult:
    """
    Returned by AppRunner after a single model call + action execution.
    """

    def __init__(
        self,
        success: bool,
        should_continue: bool = False,
        should_break: bool = False,
        change_strategy_requested: bool = False,
        change_strategy_reason: Optional[str] = None,
    ):
        self.success = success
        self.should_continue = should_continue
        self.should_break = should_break
        self.change_strategy_requested = change_strategy_requested
        self.change_strategy_reason = change_strategy_reason


class AppRunner:
    """
    Executes one RunItem through the AI provider + action pipeline.

    Responsibilities:
    - Build request payloads for the model.
    - Invoke provider client.
    - Log request + response files if enabled.
    - Parse the response JSON.
    - Execute actions in order.
    - Return a RunResult with control-flow flags.
    """

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.logger = BasicLogger("AppRunner").get_logger()

        # Register all built-in actions once
        ActionRegistry.register_defaults()

    # ------------------------------------------------------------------
    def run(
        self,
        run_item: Any,
        run_params: Dict[str, Any],
        profile_name: Optional[str],
        class_name: Optional[str],
        task_description: Optional[str],
        agent_input_overrides: Dict[str, Any],
    ) -> RunResult:
        """
        Execute a single RunItem via the configured AI provider + actions.
        """

        # Extract key runtime parameters ---------------------------------
        profile_file = run_params["profile_file"]
        context_files = run_params["context_files"]
        pretty = ", ".join(context_files) if context_files else "<none>"
        self.logger.info(f"[AppRunner] Using context paths: {pretty}")
        target_file = run_params.get("target_file")
        provider_override = run_params.get("provider_override")

        attempt_number = run_params["attempt_number"]
        log_io_settings = run_params["log_io_settings"]

        # Load profile JSON ----------------------------------------------
        with open(profile_file, "r", encoding="utf-8") as f:
            profile = json.load(f)

        provider = (
            provider_override
            if provider_override
            else profile.get("provider", "openai")
        )

        # Construct request ----------------------------------------------
        request_payload = self._build_request_payload(
            profile=profile,
            context_files=context_files,
            run_item=run_item,
            task_description=task_description,
            agent_input_overrides=agent_input_overrides,
        )

        # Write request log file -----------------------------------------
        if log_io_settings.get("enabled"):
            self._write_io_file(
                log_io_settings=log_io_settings,
                run_name=run_item.name,
                attempt=attempt_number,
                is_request=True,
                content=request_payload,
            )

        # Call provider ---------------------------------------------------
        if provider == "openai":
            client = OpenAIClient(self.logger)
        elif provider == "gemini":
            client = GeminiClient(self.logger)
        else:
            raise ValueError(f"Unsupported provider '{provider}'")

        raw_response = client.send(request_payload)

        # Write response log file ----------------------------------------
        if log_io_settings.get("enabled"):
            self._write_io_file(
                log_io_settings=log_io_settings,
                run_name=run_item.name,
                attempt=attempt_number,
                is_request=False,
                content=raw_response,
            )

        # Parse provider output ------------------------------------------
        try:
            actions = self._extract_agent_actions(raw_response)
        except Exception as e:
            self.logger.error(f"Failed to parse model output: {e}")
            return RunResult(success=False, should_break=True)

        # Execute actions -------------------------------------------------
        result = self._execute_actions(
            actions=actions,
            run_item=run_item,
            target_file=target_file,
            attempt_number=attempt_number,
            log_io_settings=log_io_settings,
        )

        return result

    # ----------------------------------------------------------------------
    # Build the request JSON payload according to profile rules
    # ----------------------------------------------------------------------
    def _build_request_payload(
        self,
        profile: Dict[str, Any],
        context_files: List[str],
        run_item: Any,
        task_description: Optional[str],
        agent_input_overrides: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build the model payload using the profile template and context files.
        """

        agent_input: Dict[str, Any] = {
            "task_description": task_description,
            "allowed_actions": run_item.allowed_actions,
        }
        agent_input.update(agent_input_overrides)

        # Load context files
        context_blocks: List[str] = []
        for file_path in context_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                with open(full_path, "r", encoding="utf-8") as f:
                    context_blocks.append(
                        f"=== CONTEXT FILE: {file_path} ===\n{f.read()}"
                    )

        context_block = "\n\n".join(context_blocks)

        # Fill template messages
        messages: List[Dict[str, str]] = []
        for msg in profile.get("messages", []):
            role = msg["role"]
            content = msg["content"]

            # Replace placeholders
            content = content.replace("${agent_input}", json.dumps(agent_input))
            content = content.replace("${rules_block}", "")
            content = content.replace("${task_description}", task_description or "")
            content = content.replace("${context_block}", context_block)

            messages.append({"role": role, "content": content})

        payload: Dict[str, Any] = {
            "model": profile.get("model"),
            "temperature": profile.get("temperature"),
            "top_p": profile.get("top_p"),
            "max_tokens": profile.get("max_tokens"),
            "messages": messages,
            "response_format": profile.get("response_format"),
        }

        return payload

    # ----------------------------------------------------------------------
    # Request/response logging
    # ----------------------------------------------------------------------
    def _write_io_file(
        self,
        log_io_settings: Dict[str, Any],
        run_name: str,
        attempt: int,
        is_request: bool,
        content: Any,
    ) -> None:
        """
        Write a request or response JSON file under log_io.log_dir
        according to the configured filename patterns.
        """

        log_dir = Path(log_io_settings["log_dir"])
        pattern = (
            log_io_settings["request_file_pattern"]
            if is_request
            else log_io_settings["response_file_pattern"]
        )

        filename = pattern.format(run_name=run_name, attempt=attempt)
        log_dir.mkdir(parents=True, exist_ok=True)

        path = log_dir / filename

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
            self.logger.info(
                f"[IO-LOG] {'Request' if is_request else 'Response'} saved to {path}"
            )
        except Exception as e:
            self.logger.error(f"Failed to write log file '{path}': {e}")

    # ----------------------------------------------------------------------
    # Extract the `agent.actions` array from the provider output
    # ----------------------------------------------------------------------
    def _extract_agent_actions(self, raw_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Unwrap provider-specific envelopes and return agent.actions list.

        Supported shapes:

        1) OpenAI / Gemini-style chat completion:
           {
             "choices": [
               {
                 "message": {
                   "content": <JSON object OR JSON string>
                 }
               }
             ]
           }

        2) Direct JSON with 'agent':
           {
             "agent": { "actions": [...] }
           }
        """
        content: Any = raw_response

        # 1) If it's a chat-completions style envelope, unwrap choices[0].message.content
        if isinstance(raw_response, dict) and "choices" in raw_response:
            choices = raw_response.get("choices") or []
            if not choices:
                raise ValueError("Model response contains no choices")

            first_choice = choices[0] or {}
            message = first_choice.get("message") or {}
            content = message.get("content")

        # 2) If content is a JSON string, parse it
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Model response message content is not valid JSON: {e}"
                ) from e

        # 3) If content is still not a dict, this is an error
        if not isinstance(content, dict):
            raise ValueError("Model response message content is not a JSON object")

        # 4) Now expect the NexusArbiter contract: content["agent"]["actions"]
        agent = content.get("agent")
        if not isinstance(agent, dict):
            raise ValueError("Model response missing 'agent' object")

        actions = agent.get("actions")
        if not isinstance(actions, list):
            raise ValueError("Model response 'agent.actions' must be a list")

        return actions

    # ----------------------------------------------------------------------
    # Action execution pipeline
    # ----------------------------------------------------------------------
    def _execute_actions(
        self,
        actions: List[Dict[str, Any]],
        run_item: Any,
        target_file: Optional[str],
        attempt_number: int,
        log_io_settings: Dict[str, Any],
    ) -> RunResult:
        """
        Execute the list of actions returned by the model.
        """

        ctx = ActionContext(
            project_root=str(self.project_root),
            target_file=target_file,
            run_name=run_item.name,
            run_item=run_item,
            logger=self.logger,
            attempt_number=attempt_number,
            log_io_settings=log_io_settings,
        )

        for action_obj in actions:
            action_type = action_obj["type"]
            params = action_obj.get("params", {})

            try:
                action: BaseAction = ActionRegistry.create(action_type)
            except ValueError as e:
                self.logger.error(f"Unknown action type '{action_type}': {e}")
                return RunResult(success=False, should_break=True)

            action.execute(ctx, params)

            # Control-flow checks after each action
            if ctx.should_break:
                return RunResult(success=True, should_break=True)

            if ctx.change_strategy_requested:
                return RunResult(
                    success=True,
                    change_strategy_requested=True,
                    change_strategy_reason=ctx.change_strategy_reason,
                )

        # Completed all actions without break/strategy-change
        return RunResult(success=True, should_continue=True)
