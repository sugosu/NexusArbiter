# core/ai_client/ai_response_parser.py
import json
from typing import Any, Dict


class AIResponseParser:
    """
    Extracts structured data (like 'agent' and 'actions') from AI responses.

    Expected OpenAI response shape (chat/completions):

    {
      "choices": [
        {
          "message": {
            "role": "assistant",
            "content": <string or dict or list>
          }
        }
      ],
      ...
    }

    When using response_format = { "type": "json_object" }, the content may be:
    - a JSON string ("{ ... }")
    - or already a dict ({ ... })
    """

    # ------------------------------------------------------------------ #
    # Core parsing helper
    # ------------------------------------------------------------------ #
    @staticmethod
    def _content_dict(response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Safely parse message content into a dict. Returns {} on failure.

        Handles:
        - content as JSON string
        - content as already-parsed dict
        - content as list with a single JSON string or dict
        """
        try:
            message = response["choices"][0]["message"]
            content = message.get("content")
        except (KeyError, TypeError):
            return {}

        # Case 1: already a dict
        if isinstance(content, dict):
            return content

        # Case 2: JSON string
        if isinstance(content, str):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Not valid JSON, give up
                return {}

        # Case 3: list of parts (future-proofing; try first element)
        if isinstance(content, list) and content:
            first = content[0]

            # If first is dict and already looks like the JSON envelope
            if isinstance(first, dict) and "agent" in first:
                return first

            # If first has 'text' or 'value', try to JSON-load that
            if isinstance(first, dict):
                text_val = first.get("text") or first.get("value")
                if isinstance(text_val, str):
                    try:
                        return json.loads(text_val)
                    except json.JSONDecodeError:
                        return {}

        # Anything else we don't recognize
        return {}

    # ------------------------------------------------------------------ #
    # Agent/actions helpers
    # ------------------------------------------------------------------ #
    @classmethod
    def extract_agent(cls, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract the 'agent' object from the response JSON.

        Expected shape in the model output:

        {
          "agent": {
            "name": "code_pipeline",
            "version": "v1",
            "actions": [ ... ]
          }
        }

        Returns {} if the 'agent' key is missing or invalid.
        """
        data = cls._content_dict(response)
        agent = data.get("agent", {})
        return agent if isinstance(agent, dict) else {}

    @classmethod
    def extract_actions(cls, response: Dict[str, Any]) -> list[dict]:
        """
        Convenience helper: return agent.actions[] as a list.
        Empty list if agent or actions is missing/invalid.
        """
        agent = cls.extract_agent(response)
        actions = agent.get("actions", [])
        return actions if isinstance(actions, list) else []
