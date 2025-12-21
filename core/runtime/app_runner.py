# core/runtime/app_runner.py
from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import core.runtime.response_validation as rv
from core.actions.base_action import ActionContext, BaseAction
from core.actions.registry import ActionRegistry
from core.ai_client.gemini_client import GeminiClient
from core.ai_client.openai_client import OpenAIClient
from core.logger import BasicLogger


class RunResult:
    def __init__(
        self,
        success: bool,
        should_continue: bool = False,
        should_break: bool = False,
        change_strategy_requested: bool = False,
        change_strategy_reason: Optional[str] = None,
        change_strategy_name: Optional[str] = None,
        change_strategy_method: Optional[str] = None,
        # NOTE: core/app.py expects these fields today (keep for compatibility).
        retry_requested: bool = False,
        retry_reason: Optional[str] = None,
    ):
        self.success = success
        self.should_continue = should_continue
        self.should_break = should_break
        self.change_strategy_requested = change_strategy_requested
        self.change_strategy_reason = change_strategy_reason
        self.change_strategy_name = change_strategy_name
        self.change_strategy_method = change_strategy_method
        self.retry_requested = retry_requested
        self.retry_reason = retry_reason


class AppRunner:
    """
    Executes one RunItem through the AI provider + action pipeline.

    Responsibilities (v0.1):
    - Load profile JSON
    - Build request payload (profile messages + context)
    - Send request to provider
    - Parse response into agent.actions
    - Validate response envelope + (optional) JSON Schema
    - Enforce allowed actions
    - Execute actions in order
    - Return RunResult
    """

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()
        self.logger = BasicLogger("AppRunner").get_logger()
        ActionRegistry.register_defaults()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(
        self,
        run_item: Any,
        run_params: Dict[str, Any],
        task_description: Optional[str],
        agent_input_overrides: Dict[str, Any],
    ) -> RunResult:
        profile_file = run_params["profile_file"]
        context_files = run_params["context_files"]
        target_file = run_params.get("target_file")
        provider_override = run_params.get("provider_override")
        attempt_number = int(run_params["attempt_number"])
        log_io_settings = run_params.get("log_io_settings") or {}

        profile = self._load_profile(profile_file)
        provider = provider_override or profile.get("provider", "openai")

        # Inject rerun-method vocabulary into agent_input (NO strategy file, NO block names).
        agent_input_overrides = self._inject_rerun_methods_into_agent_input(
            agent_input_overrides=agent_input_overrides,
            run_params=run_params,
        )

        request_payload = self._build_request_payload(
            profile=profile,
            context_files=context_files,
            run_item=run_item,
            task_description=task_description,
            agent_input_overrides=agent_input_overrides,
        )

        if bool(log_io_settings.get("enabled", False)):
            self._write_io_file(
                log_io_settings=log_io_settings,
                run_name=getattr(run_item, "name", "unnamed_run"),
                attempt=attempt_number,
                is_request=True,
                content=request_payload,
            )

        client = self._create_client(provider)
        raw_response = client.send(request_payload)

        if bool(log_io_settings.get("enabled", False)):
            self._write_io_file(
                log_io_settings=log_io_settings,
                run_name=getattr(run_item, "name", "unnamed_run"),
                attempt=attempt_number,
                is_request=False,
                content=raw_response,
            )

        # ----------------------------
        # Hard constraints:
        # 1) envelope validation
        # 2) optional JSON Schema validation (if schema exists)
        # 3) allowed-actions enforcement
        # ----------------------------
        try:
            content_obj = self._extract_content_object(raw_response)

            actions = rv.AgentEnvelopeValidator().validate_and_normalize(content_obj)

            schema = rv.ResponseSchemaProvider().get_schema(profile)
            if schema is not None:
                rv.JsonSchemaValidator().validate(instance=content_obj, schema=schema)

            rv.AllowedActionsPolicy(getattr(run_item, "allowed_actions", [])).enforce(actions)

        except (rv.SchemaValidationError, rv.DisallowedActionError) as e:
            self.logger.error("Response validation failed: %s", e, exc_info=True)
            return RunResult(success=False, should_break=True)
        except Exception as e:  # noqa: BLE001
            self.logger.error("Response handling failed: %s", e, exc_info=True)
            return RunResult(success=False, should_break=True)

        
        return self._execute_actions(
            actions=actions,
            run_item=run_item,
            target_file=target_file,
            attempt_number=attempt_number,
            log_io_settings=log_io_settings,
        )

    # ------------------------------------------------------------------
    # Profile / provider
    # ------------------------------------------------------------------
    def _load_profile(self, profile_file: str) -> Dict[str, Any]:
        """
        Resolve profile_file relative to project_root (unless absolute).
        """
        path = Path(profile_file)
        if not path.is_absolute():
            path = (self.project_root / path).resolve()

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Profile must be a JSON object: {path}")
        return data

    def _create_client(self, provider: str) -> Any:
        if provider == "openai":
            return OpenAIClient(self.logger)
        if provider == "gemini":
            return GeminiClient(self.logger)
        raise ValueError(f"Unsupported provider '{provider}'")

    # ------------------------------------------------------------------
    # Agent input injection (rerun method vocabulary)
    # ------------------------------------------------------------------
    def _inject_rerun_methods_into_agent_input(
        self,
        *,
        agent_input_overrides: Dict[str, Any],
        run_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Inject run-level rerun method vocabulary into agent_input so validators can pick
        a method (e.g. refiner/remake/...) without knowing any strategy block names.

        Resulting agent_input:
          {
            ...,
            "rerun": { "allowed_methods": ["refiner", "remake", ...] }
          }
        """
        overrides = dict(agent_input_overrides or {})

        rerun_methods = run_params.get("rerun_methods")
        if not isinstance(rerun_methods, list):
            return overrides

        allowed_methods = [m.strip() for m in rerun_methods if isinstance(m, str) and m.strip()]
        if not allowed_methods:
            return overrides

        rerun_obj = overrides.get("rerun")
        if not isinstance(rerun_obj, dict):
            rerun_obj = {}

        rerun_obj["allowed_methods"] = allowed_methods
        overrides["rerun"] = rerun_obj
        return overrides

    # ------------------------------------------------------------------
    # Request payload building
    # ------------------------------------------------------------------
    def _build_request_payload(
        self,
        profile: Dict[str, Any],
        context_files: List[str],
        run_item: Any,
        task_description: Optional[str],
        agent_input_overrides: Dict[str, Any],
    ) -> Dict[str, Any]:
        agent_input: Dict[str, Any] = {
            "task_description": task_description,
            "allowed_actions": getattr(run_item, "allowed_actions", []),
        }
        if isinstance(agent_input_overrides, dict) and agent_input_overrides:
            agent_input.update(agent_input_overrides)

        context_block = self._load_context_block(context_files)

        messages: List[Dict[str, str]] = []
        for msg in profile.get("messages", []) or []:
            if not isinstance(msg, dict):
                continue

            role = msg.get("role")
            content = msg.get("content")
            if not isinstance(role, str) or not isinstance(content, str):
                continue

            content = content.replace("${agent_input}", json.dumps(agent_input, ensure_ascii=False))
            content = content.replace("${rules_block}", "")
            content = content.replace("${task_description}", task_description or "")
            content = content.replace("${context_block}", context_block)

            messages.append({"role": role, "content": content})

        if not messages:
            raise ValueError(
                f"Profile '{profile.get('name', '<unnamed>')}' produced empty messages. "
                "Ensure profile.messages is a non-empty list of {{role, content}}."
            )

        return {
            "model": profile.get("model"),
            "temperature": profile.get("temperature"),
            "top_p": profile.get("top_p"),
            "max_tokens": profile.get("max_tokens"),
            "messages": messages,
            "response_format": profile.get("response_format"),
        }

    def _load_context_block(self, context_files: List[str]) -> str:
        if not context_files:
            return ""

        blocks: List[str] = []
        for rel in context_files:
            p = Path(rel)
            if not p.is_absolute():
                p = (self.project_root / p).resolve()

            if not p.exists():
                continue

            try:
                raw = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            blocks.append(f"=== CONTEXT FILE: {rel} ===\n{raw}")

        return "\n\n".join(blocks)

    # ------------------------------------------------------------------
    # Request/response logging
    # ------------------------------------------------------------------
    def _write_io_file(
        self,
        log_io_settings: Dict[str, Any],
        run_name: str,
        attempt: int,
        is_request: bool,
        content: Any,
    ) -> None:
        log_dir_cfg = str(log_io_settings.get("log_dir", "logs/io"))
        log_dir = Path(log_dir_cfg)
        if not log_dir.is_absolute():
            log_dir = (self.project_root / log_dir).resolve()

        pattern = (
            log_io_settings.get("request_file_pattern", "{run_name}__{attempt}__request.json")
            if is_request
            else log_io_settings.get("response_file_pattern", "{run_name}__{attempt}__response.json")
        )

        filename = str(pattern).format(run_name=run_name, attempt=attempt)
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / filename

        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
            self.logger.info(
                "[IO-LOG] %s saved to %s",
                "Request" if is_request else "Response",
                path,
            )
        except Exception as e:  # noqa: BLE001
            self.logger.error("Failed to write log file '%s': %s", path, e, exc_info=True)

    # ------------------------------------------------------------------
    # Response parsing (envelope extraction)
    # ------------------------------------------------------------------
    def _extract_content_object(self, raw_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns the model message content as a dict.
        Supports OpenAI/Gemini-style envelope: {"choices":[{"message":{"content": <str|dict>}}]}
        """
        content: Any = raw_response

        if isinstance(raw_response, dict) and "choices" in raw_response:
            choices = raw_response.get("choices") or []
            if not choices:
                raise ValueError("Model response contains no choices")

            first_choice = choices[0] or {}
            message = first_choice.get("message") or {}
            content = message.get("content")

        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError(f"Model response message content is not valid JSON: {e}") from e

        if not isinstance(content, dict):
            raise ValueError("Model response message content is not a JSON object")

        return content

    # ------------------------------------------------------------------
    # Action execution
    # ------------------------------------------------------------------
    def _execute_actions(
        self,
        actions: List[Dict[str, Any]],
        run_item: Any,
        target_file: Optional[str],
        attempt_number: int,
        log_io_settings: Dict[str, Any],
    ) -> RunResult:
        ctx = ActionContext(
            project_root=str(self.project_root),
            target_file=run_item.target_file,
            run_name=getattr(run_item, "name", "unnamed_run"),
            run_item=run_item,
            logger=self.logger,
            attempt_number=attempt_number,
            log_io_settings=log_io_settings,
        )

        for action_obj in actions:
            action_type = action_obj["type"]
            params = action_obj.get("params", {}) or {}

            try:
                action: BaseAction = ActionRegistry.create(action_type)
            except ValueError as e:
                self.logger.error("Unknown action type '%s': %s", action_type, e)
                return RunResult(success=False, should_break=True)

            try:
                self._call_action_execute(action, ctx, params)
            except Exception as e:  # noqa: BLE001
                self.logger.error(
                    "Action '%s' failed: %s (params=%r)",
                    action_type,
                    e,
                    params,
                    exc_info=True,
                )
                return RunResult(success=False, should_break=True)

            # ---------------------------------------------------------
            # Rerun routing normalization (name + method)
            # ---------------------------------------------------------
            if action_type == "rerun":
                if not getattr(ctx, "change_strategy_name", None):
                    n = params.get("name")
                    if isinstance(n, str) and n.strip():
                        setattr(ctx, "change_strategy_name", n.strip())

                if not getattr(ctx, "change_strategy_method", None):
                    m = params.get("method")
                    if isinstance(m, str) and m.strip():
                        m = m.strip()
                        if m not in ("refiner", "remake"):
                            raise ValueError(
                                f"Invalid rerun params.method: {m!r}. Must be 'refiner' or 'remake'."
                            )
                        setattr(ctx, "change_strategy_method", m)

            # IMPORTANT: Strategy change must short-circuit immediately.
            if getattr(ctx, "change_strategy_requested", False):
                return RunResult(
                    success=True,
                    change_strategy_requested=True,
                    change_strategy_reason=getattr(ctx, "change_strategy_reason", None),
                    change_strategy_name=getattr(ctx, "change_strategy_name", None),
                    change_strategy_method=getattr(ctx, "change_strategy_method", None),
                )

            if getattr(ctx, "should_break", False):
                return RunResult(success=True, should_break=True)

        return RunResult(success=True, should_continue=True)


    @staticmethod
    def _call_action_execute(action: BaseAction, ctx: ActionContext, params: Dict[str, Any]) -> None:
        """
        Defensive adapter for action.execute.

        Bound method signatures:
          - execute(ctx, params) -> 2 parameters (expected)
          - execute(ctx)        -> 1 parameter  (legacy only)
        """
        try:
            sig = inspect.signature(action.execute)
            param_count = len(sig.parameters)
        except (TypeError, ValueError):
            # Prefer modern contract first
            try:
                action.execute(ctx, params)
                return
            except TypeError:
                action.execute(ctx)  # type: ignore[misc]
                return

        if param_count == 2:
            action.execute(ctx, params)
            return

        if param_count == 1:
            action.execute(ctx)  # type: ignore[misc]
            return

        # Unexpected signature: try modern then legacy
        try:
            action.execute(ctx, params)
        except TypeError:
            action.execute(ctx)  # type: ignore[misc]
