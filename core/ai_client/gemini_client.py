# core/ai_client/gemini_client.py
from __future__ import annotations

import os
import json
from typing import Any, Dict, Optional, List

from google import genai
from google.genai import types


class GeminiClient:
    """
    Thin wrapper around the Google Gen AI (Gemini) SDK.

    This client is designed to work like the OpenAI client in the rest
    of the framework:

    - It accepts a Chat-Completions-style `payload` dict:
        {
          "model": "...",
          "messages": [...],
          "temperature": ...,
          "top_p": ...,
          "max_tokens": ...,
          "response_format": {...}
        }

    - It returns a dict shaped like OpenAI's chat.completions JSON:
        {
          "choices": [
            {
              "message": {
                "content": <JSON or text>
              }
            }
          ]
        }

      so that `AIResponseParser.extract_agent(...)` can be reused.
    """

    def __init__(self, logger, api_key: Optional[str] = None):
        self.logger = logger
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        # Initialize the official Gemini client
        self.client = genai.Client(api_key=self.api_key)

    # ------------------------------------------------------------------
    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entrypoint used by AppRunner.

        Accepts an OpenAI-style payload and internally:
        - flattens messages into `system_instruction` + `final_prompt`
        - configures structured JSON output if response_format.type == 'json_object'
        - calls Gemini
        - parses the text into JSON (when possible)
        - wraps into a Chat-Completions-like dict for AIResponseParser
        """
        self.logger.info("[GeminiClient] Sending request to Gemini...")

        model_name: str = payload.get("model") or "gemini-2.0-flash"
        temperature: float = payload.get("temperature", 0.0)
        messages: List[Dict[str, Any]] = payload.get("messages", [])
        response_format = payload.get("response_format")

        # 1) Extract system_instruction + user prompt (mirrors previous logic)
        system_instruction: Optional[str] = None
        user_parts: List[str] = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system" and system_instruction is None:
                system_instruction = content
            else:
                # Keep it simple and robust
                user_parts.append(f"{role.upper()}: {content}")

        final_prompt = "\n\n".join(user_parts)

        # 2) Map OpenAI-style response_format → Gemini structured output schema
        response_schema: Optional[Dict[str, Any]] = None
        if isinstance(response_format, dict) and response_format.get("type") == "json_object":
            # Minimal schema for:
            # {
            #   "agent": {
            #     "actions": [
            #       { "type": "...", "params": { "target_path": "...", "code": "..." } }
            #     ]
            #   }
            # }
            # IMPORTANT: no additionalProperties – Gemini does not support it.
            response_schema = {
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

        # 3) Build generation config
        config_args: Dict[str, Any] = {
            "temperature": temperature,
        }
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

            text_content = response.text

            # 4) Try to parse JSON first (profiles normally ask for JSON)
            parsed: Any
            try:
                parsed = json.loads(text_content)
            except json.JSONDecodeError:
                self.logger.info(
                    "[GeminiClient] Response is not valid JSON; returning raw text."
                )
                parsed = {"content": text_content}

            # 5) Wrap into a Chat-Completions-like envelope so AIResponseParser
            # can treat it the same way as OpenAI responses.
            wrapped = {
                "choices": [
                    {
                        "message": {
                            "content": parsed,
                        }
                    }
                ]
            }

            self.logger.info("[GeminiClient] Received response.")
            return wrapped

        except Exception as e:
            self.logger.error(f"[GeminiClient] API error: {e}")
            raise
