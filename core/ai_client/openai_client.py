import json
from typing import Dict, Any, Optional

import requests

from core.logger import BasicLogger


class OpenAIClient:
    """
    Handles direct HTTP calls to the OpenAI API.
    """

    # Whitelist of top-level keys allowed by /v1/chat/completions
    _ALLOWED_TOP_LEVEL_KEYS = {
        "model",
        "messages",
        "temperature",
        "top_p",
        "max_tokens",
        "n",
        "stop",
        "presence_penalty",
        "frequency_penalty",
        "logit_bias",
        "user",
        "response_format",
        "seed",
        "tools",
        "tool_choice",
        "metadata",
    }

    def __init__(
        self,
        api_url: str = "https://api.openai.com/v1/chat/completions",
        api_key: str = "",
    ):
        self.api_url = api_url
        self.api_key = api_key
        # JSON logs will go to logs/openai_client.jsonl if you configured BasicLogger that way
        self.logger = BasicLogger(
            self.__class__.__name__,
            log_file="openai_client.jsonl",
        ).get_logger()

    def _sanitize_body(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove any keys that the OpenAI chat.completions API does not recognize.
        This lets profile JSON contain meta fields like 'name', 'task_description', etc.
        """
        sanitized = {
            k: v for k, v in body.items() if k in self._ALLOWED_TOP_LEVEL_KEYS
        }

        removed = [k for k in body.keys() if k not in self._ALLOWED_TOP_LEVEL_KEYS]
        if removed:
            self.logger.info(
                "Stripping meta keys from payload",
                extra={
                    "event": "openai_strip_meta_keys",
                    "removed_keys": removed,
                },
            )

        return sanitized

    def send_request(
        self,
        body: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 120,
    ) -> Dict[str, Any]:
        """
        Sends a POST request to the OpenAI API with the provided body and headers.
        """
        final_headers = headers or {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        sanitized_body = self._sanitize_body(body)

        # JSON log (to file) for outgoing request payload
        self.logger.info(
            "Outgoing OpenAI API request",
            extra={
                "event": "openai_request",
                "model": sanitized_body.get("model"),
                "payload": sanitized_body,
            },
        )

        # Optional: pretty dump for console
        self.logger.info(
            "FULL REQUEST PAYLOAD:\n%s",
            json.dumps(sanitized_body, indent=2),
        )

        response = requests.post(
            self.api_url,
            json=sanitized_body,
            headers=final_headers,
            timeout=timeout,
        )

        # Try to parse JSON once so we can both log and return it
        try:
            resp_json = response.json()
        except ValueError:
            resp_json = {"raw_text": response.text}

        # JSON log (to file) for response
        self.logger.info(
            "Received OpenAI API response",
            extra={
                "event": "openai_response",
                "status_code": response.status_code,
                "ok": response.ok,
                "response_body": resp_json,
            },
        )

        # If not ok, make it visible and raise a generic exception
        if not response.ok:
            self.logger.error(
                "OpenAI API error",
                extra={
                    "event": "openai_error",
                    "status_code": response.status_code,
                    "response_body": resp_json,
                },
            )
            raise Exception(
                f"OpenAI API error {response.status_code}: {response.text}"
            )

        return resp_json
