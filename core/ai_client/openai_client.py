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
        self.logger.info("[OpenAIClient] Sending request to OpenAI...")

        try:
            response = self.client.chat.completions.create(
                model=payload["model"],
                messages=payload["messages"],
                temperature=payload.get("temperature"),
                top_p=payload.get("top_p"),
                max_tokens=payload.get("max_tokens"),
                response_format=payload.get("response_format"),
            )

            # Convert SDK object → plain dict
            raw = json.loads(response.model_dump_json())

            self.logger.info("[OpenAIClient] Received response.")
            return raw

        except Exception as e:
            self.logger.error(f"[OpenAIClient] API error: {e}")
            raise
