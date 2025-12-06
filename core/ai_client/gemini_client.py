import os
import json
from typing import Dict, Any, Optional, List
from google import genai
from google.genai import types
from core.logger import BasicLogger


class GeminiClient:
    """
    Wrapper for the Google Gen AI SDK (Gemini).
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        self.logger = BasicLogger(self.__class__.__name__).get_logger()
        self.model = model

        # Initialize the official client
        self.client = genai.Client(api_key=self.api_key)

    def generate_content(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Generates content using Gemini.
        Supports structured JSON output if response_schema is provided.

        Additionally, even when response_schema is not provided, this method
        attempts to parse the response as JSON first. If parsing fails, it
        falls back to returning a simple text wrapper.
        """
        self.logger.info(f"Sending request to Gemini ({self.model})...")

        config_args: Dict[str, Any] = {
            "temperature": temperature,
        }

        # Handle Structured Outputs (JSON mode)
        if response_schema:
            config_args["response_mime_type"] = "application/json"
            config_args["response_schema"] = response_schema

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    **config_args,
                ),
            )

            # Extract text
            text_content = response.text

            # If we expected JSON, try to parse it to ensure it's valid
            if response_schema:
                try:
                    return json.loads(text_content)
                except json.JSONDecodeError:
                    self.logger.error("Failed to parse JSON from Gemini response.")
                    return {"error": "Invalid JSON", "raw": text_content}

            # Even when no explicit response_schema is passed, profiles may
            # instruct Gemini to return a full JSON agent object. Try JSON first.
            try:
                parsed = json.loads(text_content)
                return parsed
            except json.JSONDecodeError:
                self.logger.info(
                    "Gemini response is not valid JSON; returning raw text wrapper."
                )
                return {"content": text_content}

        except Exception as e:
            self.logger.error(f"Gemini API error: {str(e)}")
            raise e
