# core/runtime/response_validation.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence


# ----------------------------
# Exceptions
# ----------------------------

@dataclass
class SchemaValidationError(Exception):
    message: str
    details: Optional[Any] = None

    def __str__(self) -> str:
        if self.details is None:
            return self.message
        return f"{self.message} | details={self.details!r}"


@dataclass
class DisallowedActionError(Exception):
    action_type: str
    allowed: Sequence[str]

    def __str__(self) -> str:
        return f"Action '{self.action_type}' is not allowed. Allowed={list(self.allowed)!r}"


# ----------------------------
# Allowed actions enforcement
# ----------------------------

class AllowedActionsPolicy:
    """
    Enforces that agent-emitted actions are limited to run_item.allowed_actions.
    If allowed_actions is empty, enforcement is disabled (no restrictions).
    """

    def __init__(self, allowed_actions: Optional[List[str]]):
        allowed_actions = allowed_actions or []
        self._allowed = {a.strip() for a in allowed_actions if isinstance(a, str) and a.strip()}

    def enforce(self, actions: List[Dict[str, Any]]) -> None:
        if not self._allowed:
            return

        for a in actions:
            t = a.get("type")
            if not isinstance(t, str) or not t.strip():
                raise SchemaValidationError("Action is missing a valid 'type' field.", details=a)

            if t not in self._allowed:
                raise DisallowedActionError(action_type=t, allowed=sorted(self._allowed))


# ----------------------------
# Envelope validator
# ----------------------------

class AgentEnvelopeValidator:
    """
    Validates and normalizes the model output to the canonical envelope:

    {
      "agent": {
        "actions": [
          { "type": "...", "params": { ... } }
        ]
      }
    }

    Returns normalized actions list: [{"type": str, "params": dict}, ...]
    """

    def validate_and_normalize(self, content: Any) -> List[Dict[str, Any]]:
        if not isinstance(content, dict):
            raise SchemaValidationError("Model content must be a JSON object.")

        agent = content.get("agent")
        if not isinstance(agent, dict):
            raise SchemaValidationError("Model content missing required object: 'agent'.")

        actions = agent.get("actions")
        if not isinstance(actions, list) or len(actions) == 0:
            raise SchemaValidationError("'agent.actions' must be a non-empty list.")

        normalized: List[Dict[str, Any]] = []
        for i, a in enumerate(actions):
            if not isinstance(a, dict):
                raise SchemaValidationError(f"agent.actions[{i}] must be an object.", details=a)

            t = a.get("type")
            if not isinstance(t, str) or not t.strip():
                raise SchemaValidationError(f"agent.actions[{i}].type must be a non-empty string.", details=a)

            p = a.get("params", {})
            if p is None:
                p = {}
            if not isinstance(p, dict):
                raise SchemaValidationError(f"agent.actions[{i}].params must be an object.", details=a)

            normalized.append({"type": t, "params": p})

        return normalized


# ----------------------------
# JSON Schema validation (hard constraint when schema provided)
# ----------------------------

class JsonSchemaValidator:
    """
    Validates the entire content dict against a JSON Schema.

    Hard constraint: if a schema is supplied and jsonschema is unavailable,
    we fail deterministically.
    """

    def validate(self, instance: Dict[str, Any], schema: Dict[str, Any]) -> None:
        try:
            import jsonschema  # type: ignore
        except Exception as e:  # noqa: BLE001
            raise SchemaValidationError(
                "jsonschema package is required for response schema validation but is not installed.",
                details=str(e),
            ) from e

        try:
            jsonschema.validate(instance=instance, schema=schema)
        except jsonschema.ValidationError as e:  # type: ignore[attr-defined]
            raise SchemaValidationError("Response JSON failed schema validation.", details=str(e)) from e
        except jsonschema.SchemaError as e:  # type: ignore[attr-defined]
            raise SchemaValidationError("Provided JSON Schema is invalid.", details=str(e)) from e


class ResponseSchemaProvider:
    """
    Determines which schema (if any) should be used to validate the model output.

    Supported profile shapes:
      - profile["response_format"] == {"type":"json_schema", "json_schema":{"schema":{...}}}
      - profile["response_schema"] == {...}  (direct schema)
    """

    def get_schema(self, profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        direct = profile.get("response_schema")
        if isinstance(direct, dict):
            return direct

        rf = profile.get("response_format")
        if not isinstance(rf, dict):
            return None

        if rf.get("type") != "json_schema":
            return None

        js = rf.get("json_schema")
        if not isinstance(js, dict):
            return None

        schema = js.get("schema")
        return schema if isinstance(schema, dict) else None
