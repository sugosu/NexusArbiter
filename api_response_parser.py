# === CONTEXT START ===
# Added a logger to the AIResponseParser class using BasicLogger. The logger is
# initialized in the __init__ method. No changes were made to the public behavior
# of the methods.
# === CONTEXT END ===

# core/ai_response_parser.py
import json
from core.logger import BasicLogger

class AIResponseParser:
    """
    Extracts structured data (like 'code' and 'context') from AI responses.
    """

    def __init__(self):
        self.logger = BasicLogger(self.__class__.__name__).get_logger()

    @staticmethod
    def _content_dict(response: dict) -> dict:
        """
        Safely turn message content into a dict. Returns {} on failure.
        """
        try:
            content = response["choices"][0]["message"]["content"]
            # Content is expected to be a raw JSON object (response_format=json_object).
            return json.loads(content)
        except (KeyError, json.JSONDecodeError, TypeError):
            return {}

    @classmethod
    def extract_code(cls, response: dict) -> str:
        """
        Extract the 'code' value from the model's response JSON.
        """
        data = cls._content_dict(response)
        val = data.get("code", "")
        return val if isinstance(val, str) else ""

    @classmethod
    def extract_context(cls, response: dict) -> str:
        """
        Extract the 'context' value from the model's response JSON.
        """
        data = cls._content_dict(response)
        val = data.get("context", "")
        return val if isinstance(val, str) else ""

    @classmethod
    def extract(cls, response: dict) -> dict:
        """
        Extract both 'code' and 'context'. Missing fields become empty strings.
        Returns: {"code": str, "context": str}
        """
        data = cls._content_dict(response)
        code = data.get("code", "")
        context = data.get("context", "")
        return {
            "code": code if isinstance(code, str) else "",
            "context": context if isinstance(context, str) else "",
        }
