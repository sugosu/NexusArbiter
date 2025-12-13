# core/ai_client/gemini_client.py
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types


class GeminiClient:
    """
    Thin wrapper around Google Gen AI (Gemini).

    Accepts an OpenAI-style chat payload and returns an OpenAI-like envelope:
      {"choices":[{"message":{"content": <dict|str>}}]}
    """

    def __init__(self, logger, api_key: Optional[str] = None):
        self.logger = logger
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        self.client = genai.Client(api_key=self.api_key)

    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("[GeminiClient] Sending request to Gemini...")

        model_name = payload.get("model") or "gemini-2.0-flash"
        temperature = float(payload.get("temperature", 0.0))

        messages = payload.get("messages")
        if not isinstance(messages, list) or len(messages) == 0:
            raise ValueError("Invalid payload: 'messages' must be a non-empty list.")

        response_format = payload.get("response_format")

        system_instruction, final_prompt = self._flatten_messages(messages)
        response_schema = self._build_response_schema(response_format)

        config_args: Dict[str, Any] = {"temperature": temperature}
        if response_schema is not None:
            config_args["response_mime_type"] = "application/json"
            config_args["response_schema"] = response_schema

        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=final_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    **config_args,
                ),
            )
        except Exception as e:
            self.logger.error("[GeminiClient] API error: %s", e)
            raise

        parsed = self._parse_text_as_json(response.text)

        wrapped = {"choices": [{"message": {"content": parsed}}]}
        self.logger.info("[GeminiClient] Received response.")
        return wrapped

    @staticmethod
    def _flatten_messages(messages: List[Dict[str, Any]]) -> tuple[Optional[str], str]:
        """
        Convert OpenAI-style messages into Gemini's:
        - system_instruction (single string)
        - final_prompt (single string)
        """
        system_instruction: Optional[str] = None
        parts: List[str] = []

        for msg in messages:
            if not isinstance(msg, dict):
                continue
            role = (msg.get("role") or "").strip()
            content = msg.get("content", "")

            if role == "system" and system_instruction is None:
                system_instruction = str(content)
                continue

            role_label = role.upper() if role else "MESSAGE"
            parts.append(f"{role_label}: {content}")

        final_prompt = "\n\n".join(parts).strip()
        if not final_prompt:
            # Gemini requires some prompt; avoid sending empty contents.
            final_prompt = "USER: (empty prompt)"

        return system_instruction, final_prompt

    @staticmethod
    def _build_response_schema(response_format: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(response_format, dict):
            return None
        if response_format.get("type") != "json_object":
            return None

        # Minimal schema for:
        # {"agent": {"actions": [{"type": "...", "params": {...}}]}}
        # No additionalProperties (Gemini doesn't support it reliably).
        return {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "object",
                    "properties": {
                        "actions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string"},
                                    "params": {
                                        "type": "object",
                                        "properties": {
                                            "target_path": {"type": "string"},
                                            "code": {"type": "string"},
                                        },
                                        "required": ["code"],
                                    },
                                },
                                "required": ["type", "params"],
                            },
                        }
                    },
                    "required": ["actions"],
                }
            },
            "required": ["agent"],
        }

    def _parse_text_as_json(self, text: str) -> Any:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            self.logger.info("[GeminiClient] Response is not valid JSON; returning raw text.")
            return {"content": text}
