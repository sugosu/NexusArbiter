# core/runtime/app_runner.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import BasicLogger
from core.actions.registry import ActionRegistry
from core.actions.base_action import ActionContext, BaseAction
from core.ai_client.openai_client import OpenAIClient
from core.ai_client.ai_response_parser import AIResponseParser
from core.ai_client.gemini_client import GeminiClient


class AppRunner:
    """
    Responsible for:
        - loading the profile JSON
        - assembling model input payload
        - calling the correct provider (OpenAI, Gemini, ...)
        - parsing model output into actions
        - filtering allowed actions
        - executing actions in order
        - returning an ActionContext summarizing what happened

    No retry logic happens here.
    """

    def __init__(self, project_root: Path | str):
        self.project_root = Path(project_root).resolve()
        self.logger = BasicLogger("AppRunner").get_logger()

        # Action registry must be available
        ActionRegistry.register_defaults()

    # ----------------------------------------------------------------------
    # Public main entrypoint
    # ----------------------------------------------------------------------
    def run_single(
        self,
        run_item: Any,
        profile_file: str,
        context_files: List[str],
        target_file: Optional[str],
        provider_override: Optional[str] = None,
    ) -> ActionContext:
        """
        Execute a single run step. This is called by RunExecutor.

        Provider resolution order:
            1) provider_override   (strategy attempt)
            2) profile["provider"] (profile JSON)
            3) "openai" (default)
        """

        # Load profile JSON
        resolved_profile = self._load_profile(profile_file)

        # Resolve provider
        provider_name: Optional[str] = provider_override
        if not provider_name:
            provider_name = resolved_profile.get("provider")
        if not provider_name:
            provider_name = "openai"

        self.logger.info(
            f"Selected provider '{provider_name}' for profile '{profile_file}' "
            f"(target_file='{target_file}')"
        )

        # Build model request
        payload = self._build_model_payload(
            resolved_profile,
            run_item,
            provider_name,
            context_files,
        )

        # Call provider
        agent_obj = self._invoke_model(provider_name, payload)

        # Prepare action context
        ctx = ActionContext(
            project_root=str(self.project_root),
            target_file=target_file,
            run_name=run_item.name,
            run_item=run_item,
            logger=self.logger,
        )

        # Parse + execute actions
        actions = agent_obj.get("actions", [])
        filtered = self._filter_actions(actions, run_item.allowed_actions)
        self._execute_actions(filtered, ctx)

        return ctx

    # ----------------------------------------------------------------------
    # Internal utilities
    # ----------------------------------------------------------------------
    def _load_profile(self, profile_file: str) -> Dict[str, Any]:
        """
        Load the profile JSON from disk.
        """
        profile_path = (self.project_root / profile_file).resolve()
        with profile_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Profile '{profile_file}' must contain a JSON object.")

        return data

    def _build_model_payload(
        self,
        profile_dict: Dict[str, Any],
        run_item: Any,
        provider_name: str,
        context_files: List[str],
    ) -> Dict[str, Any]:
        """
        Merge:
            - static profile JSON
            - run_item metadata
            - context files
        """

        # Inject runtime metadata into the profile
        profile_dict = dict(profile_dict)  # shallow copy

        # Build agent_input
        agent_input = {
            "profile_name": run_item.profile_file,
            "class_name": getattr(run_item, "class_name", None),
            "allowed_actions": run_item.allowed_actions,
            "provider": provider_name,
        }

        # Construct context block
        context_blocks: List[str] = []
        for cf in context_files:
            path = self.project_root / cf
            try:
                with path.open("r", encoding="utf-8") as f:
                    ctxdata = f.read()
                context_blocks.append(
                    f"=== CONTEXT FILE: {cf} ===\n{ctxdata}"
                )
            except Exception as e:
                context_blocks.append(
                    f"=== CONTEXT FILE: {cf} ===\n!! ERROR READING FILE: {e} !!"
                )

        # agent_input is placed inside the request
        payload: Dict[str, Any] = {
            "model": profile_dict.get("model"),
            "temperature": profile_dict.get("temperature", 0),
            "top_p": profile_dict.get("top_p", 1),
            "max_tokens": profile_dict.get("max_tokens", 2000),
            "messages": self._inject_messages(
                profile_dict.get("messages", []),
                agent_input,
                context_blocks,
                getattr(run_item, "task_description", None),
            ),
            "response_format": profile_dict.get(
                "response_format", {"type": "json_object"}
            ),
            "user": profile_dict.get("user", "${default_user}"),
        }

        self.logger.info(
            "Prepared model payload",
            extra={
                "event": "model_payload_built",
                "run_name": getattr(run_item, "name", None),
                "provider": provider_name,
                "model": payload.get("model"),
                "temperature": payload.get("temperature"),
                "max_tokens": payload.get("max_tokens"),
                "num_messages": len(payload.get("messages", [])),
                "num_context_files": len(context_files),
            },
        )

        self.logger.info("Starting model call via provider '%s'.", provider_name)
        return payload

    def _inject_messages(
        self,
        messages: List[Dict[str, Any]],
        agent_input: Dict[str, Any],
        context_blocks: List[str],
        task_description: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        Replace ${agent_input}, ${context_block}, ${task_description}
        placeholders inside the profile messages.
        """
        ctx_combined = "\n\n".join(context_blocks)

        result: List[Dict[str, Any]] = []
        for msg in messages:
            content = msg.get("content", "")

            content = content.replace(
                "${agent_input}", json.dumps(agent_input, indent=2)
            )
            content = content.replace("${context_block}", ctx_combined)

            if task_description:
                content = content.replace("${task_description}", task_description)

            result.append({
                "role": msg["role"],
                "content": content,
            })
        return result

    def _invoke_model(self, provider_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatch to the correct provider client and normalize response
        into an 'agent' object understood by the action layer.
        """
        temperature = payload.get("temperature", 0.0)
        model_name = payload.get("model")

        if provider_name == "openai":
            client = OpenAIClient()
            response = client.call(payload)
            return AIResponseParser.extract_agent(response)

        elif provider_name == "gemini":
            # HANDLE MODEL NAME MISMATCH:
            # If the JSON still says "gpt-4o", we default to a gemini model
            if not model_name or "gpt" in model_name:
                model_name = "gemini-2.0-flash"

            client = GeminiClient(model=model_name)

            # Extract messages to format prompt
            messages = payload.get("messages", [])
            system_instruction = None
            user_parts: List[str] = []

            for msg in messages:
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "system" and not system_instruction:
                    system_instruction = content
                else:
                    user_parts.append(f"{role.upper()}: {content}")

            final_prompt = "\n\n".join(user_parts)

            response_dict = client.generate_content(
                prompt=final_prompt,
                system_instruction=system_instruction,
                temperature=temperature,
            )

            # Wrap result to look like an 'agent' object
            return AIResponseParser.extract_agent(
                {"choices": [{"message": {"content": response_dict}}]}
            )

        else:
            raise NotImplementedError(f"Provider '{provider_name}' not implemented.")

    def _filter_actions(
        self,
        actions: List[Dict[str, Any]],
        allowed: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Keep only actions whose type is allowed by run_item.
        """
        kept: List[Dict[str, Any]] = []
        for a in actions:
            if a.get("type") in allowed:
                kept.append(a)
            else:
                self.logger.warning(
                    f"Action '{a.get('type')}' rejected; not in allowed_actions={allowed}"
                )
        if not kept:
            self.logger.warning(
                f"No actions left after allowed_actions filter. "
                f"Original actions: {actions}"
            )
        return kept

    def _execute_actions(self, actions: List[Dict[str, Any]], ctx: ActionContext) -> None:
        """
        Execute actions in sequence.
        """
        for idx, action_dict in enumerate(actions, start=1):
            action_type = action_dict.get("type")
            params = action_dict.get("params", {})

            action_obj: BaseAction = ActionRegistry.create(action_type)

            ctx.logger.info(f"Executing action #{idx}: {action_type}")

            try:
                action_obj.execute(ctx, params)
            except Exception as e:
                ctx.logger.error(
                    f"Exception during action '{action_type}': {e}",
                    exc_info=True,
                )
                # leave ctx flags as-is; executor will stop run.
                break
