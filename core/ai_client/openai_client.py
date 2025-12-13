# core/ai_client/openai_client.py
from __future__ import annotations

import json
from typing import Any, Dict, List

import openai


class OpenAIClient:
    """Thin wrapper around OpenAI Chat Completions. AppRunner owns parsing + IO logging."""

    def __init__(self, logger):
        self.logger = logger
        self.client = openai.OpenAI()

    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("[OpenAIClient] Sending request to OpenAI...")

        model_name = str(payload.get("model", "")).strip()
        messages = payload.get("messages")

        # Defensive: OpenAI rejects empty messages arrays.
        if not isinstance(messages, list) or len(messages) == 0:
            raise ValueError("Invalid payload: 'messages' must be a non-empty list.")

        # Basic validation to catch bad shapes early.
        if not self._looks_like_messages(messages):
            raise ValueError("Invalid payload: 'messages' must be a list of {role, content} objects.")

        chat_args: Dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": payload.get("temperature"),
            "top_p": payload.get("top_p"),
            "response_format": payload.get("response_format"),
        }

        # Remove None values to avoid sending unsupported nulls.
        chat_args = {k: v for k, v in chat_args.items() if v is not None}

        # Token limit handling:
        # - GPT-5.x prefers max_completion_tokens
        # - older models use max_tokens
        if model_name.startswith("gpt-5"):
            max_completion_tokens = payload.get("max_completion_tokens")
            if max_completion_tokens is None:
                max_completion_tokens = payload.get("max_tokens")
            if max_completion_tokens is not None:
                chat_args["max_completion_tokens"] = max_completion_tokens
        else:
            max_tokens = payload.get("max_tokens")
            if max_tokens is not None:
                chat_args["max_tokens"] = max_tokens

        try:
            response = self.client.chat.completions.create(**chat_args)
        except Exception as e:
            self.logger.error("[OpenAIClient] API error: %s", e)
            raise

        raw = json.loads(response.model_dump_json())
        self.logger.info("[OpenAIClient] Received response.")
        return raw

    @staticmethod
    def _looks_like_messages(messages: List[Any]) -> bool:
        for m in messages:
            if not isinstance(m, dict):
                return False
            if "role" not in m or "content" not in m:
                return False
        return True
