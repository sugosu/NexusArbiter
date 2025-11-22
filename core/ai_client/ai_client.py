# === CONTEXT START ===
# Added logging to the OpenAIClient class using BasicLogger. A logger instance is
# created in the __init__ method, and logging statements are added to the
# send_request method to log when a request is sent and when an error occurs.
# === CONTEXT END ===

import requests
from typing import Dict, Any, Optional
from core.logger import BasicLogger

class OpenAIClient:
    """
    Handles direct HTTP calls to the OpenAI API.
    """

    def __init__(self, api_url: str = "https://api.openai.com/v1/chat/completions", api_key: str = ""):
        """
        Initialize the client with the API endpoint and key.
        :param api_url: Endpoint URL for OpenAI API.
        :param api_key: API key (placeholder by default).
        """
        self.api_url = api_url
        self.api_key = api_key
        self.logger = BasicLogger(self.__class__.__name__).get_logger()

    def send_request(
        self,
        body: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Sends a POST request to the OpenAI API with the provided body and headers.
        :param body: JSON payload for the request.
        :param headers: Optional custom headers. If None, default headers will be used.
        :param timeout: Timeout in seconds for the request.
        :return: JSON response as a dictionary.
        """
        self.logger.info('Sending request to OpenAI API')
        final_headers = headers or {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        response = requests.post(self.api_url, json=body, headers=final_headers, timeout=timeout)

        if response.status_code != 200:
            self.logger.error(f"OpenAI API error {response.status_code}: {response.text}")
            raise Exception(f"OpenAI API error {response.status_code}: {response.text}")

        return response.json()
