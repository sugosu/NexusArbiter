import requests
from typing import Dict, Any, Optional
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
        self.logger = BasicLogger(self.__class__.__name__).get_logger()

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
                f"OpenAIClient: stripping meta keys from payload: {', '.join(removed)}"
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

        self.logger.info("Sending request to OpenAI API")
        response = requests.post(
            self.api_url,
            json=sanitized_body,
            headers=final_headers,
            timeout=timeout,
        )

        if response.status_code != 200:
            self.logger.error(f"OpenAI API error {response.status_code}: {response.text}")
            raise Exception(f"OpenAI API error {response.status_code}: {response.text}")

        return response.json()
