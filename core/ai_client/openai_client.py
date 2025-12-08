# core/ai_client/openai_client.py
from __future__ import annotations

import json
from typing import Any, Dict

import openai


class OpenAIClient:
    """
    Thin wrapper around OpenAI's Chat Completions API.

    Requirements:
    - Accepts a ready-to-send request payload.
    - Returns a raw response dict.
    - AppRunner handles logging and parsing.
    """

    def __init__(self, logger):
        self.logger = logger
        self.client = openai.OpenAI()

    # ------------------------------------------------------------------
    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a chat completion request to OpenAI, handling both GPT-4 and GPT-5.x
        parameter differences transparently.

        - GPT-4 and earlier: use `max_tokens`
        - GPT-5.x: use `max_completion_tokens`
        """
        self.logger.info("[OpenAIClient] Sending request to OpenAI...")

        try:
            model_name = str(payload.get("model", "")).strip()

            # Base arguments shared across all chat models
            chat_args: Dict[str, Any] = {
                "model": model_name,
                "messages": payload["messages"],
                "temperature": payload.get("temperature"),
                "top_p": payload.get("top_p"),
                "response_format": payload.get("response_format"),
            }

            # Remove None values to avoid sending unsupported nulls
            chat_args = {k: v for k, v in chat_args.items() if v is not None}

            # Handle token limits depending on model family
            # GPT-5.x: requires max_completion_tokens
            if model_name.startswith("gpt-5"):
                max_completion_tokens = (
                    payload.get("max_completion_tokens")
                    if payload.get("max_completion_tokens") is not None
                    else payload.get("max_tokens")
                )
                if max_completion_tokens is not None:
                    chat_args["max_completion_tokens"] = max_completion_tokens
            else:
                # GPT-4.x and older: still use max_tokens
                if payload.get("max_tokens") is not None:
                    chat_args["max_tokens"] = payload["max_tokens"]

            response = self.client.chat.completions.create(**chat_args)

            # Convert SDK object → plain dict
            raw = json.loads(response.model_dump_json())

            self.logger.info("[OpenAIClient] Received response.")
            return raw

        except Exception as e:
            self.logger.error(f"[OpenAIClient] API error: {e}")
            raise
