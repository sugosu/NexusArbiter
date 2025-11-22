# === CONTEXT START ===
# Added logging to the AIParamGenerator class using BasicLogger. A logger instance
# is created in the __init__ method, and minimal logging is added to the
# build_params and send methods to log important actions.
# === CONTEXT END ===

from __future__ import annotations

from typing import Any, Dict, Mapping, MutableMapping, Optional
import copy
from core.logger import BasicLogger


class AIParamGenerator:
    """
    Builds ready-to-send payloads for OpenAI's /v1/chat/completions
    and dispatches them using an injected OpenAIClient-compatible instance.

    Presets are provided externally (e.g. from JSON via AIProfileLoader).

    Expected shape of a preset (minimal):

    {
        "model": "gpt-5-turbo",
        "temperature": 0,
        "max_output_tokens": 1200,
        "response_format": {...},   # optional
        "messages": [...],          # optional, can be overridden
        "metadata": {...},          # optional
        "user": "onat"              # optional, default_user is filled if missing
    }

    The actual keys can be any valid /v1/chat/completions payload parameters.
    """

    def __init__(
        self,
        client: Any,
        presets: Mapping[str, Mapping[str, Any]],
        default_user: str = "onat",
    ) -> None:
        self.logger = BasicLogger(self.__class__.__name__).get_logger()
        self.client = client
        self.default_user = default_user
        self._presets: Dict[str, Dict[str, Any]] = {
            name: dict(value) for name, value in presets.items()
        }

    # ------------------------------------------------------------------ #
    # Preset management
    # ------------------------------------------------------------------ #
    def set_presets(self, presets: Mapping[str, Mapping[str, Any]]) -> None:
        """
        Replace the internal preset mapping at runtime.
        """
        self._presets = {name: dict(value) for name, value in presets.items()}

    def get_preset_names(self) -> tuple[str, ...]:
        """
        Return tuple of known preset names.
        """
        return tuple(sorted(self._presets))

    def _get_base_preset(self, name: str) -> Dict[str, Any]:
        try:
            return copy.deepcopy(self._presets[name])
        except KeyError as exc:
            known = ", ".join(sorted(self._presets)) or "<none>"
            raise KeyError(
                f"Unknown preset '{name}'. Known presets: {known}"
            ) from exc

    # ------------------------------------------------------------------ #
    # Core API
    # ------------------------------------------------------------------ #
    def build_params(
        self,
        preset_name: str,
        overrides: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build a chat/completions payload from a preset, applying overrides.

        - Deep-merges overrides into the base preset.
        - Ensures 'user' key is present (using default_user) if missing.
        """
        self.logger.info(f"Building parameters for preset: {preset_name}")
        params = self._get_base_preset(preset_name)

        if overrides:
            self._deep_merge(params, overrides)

        if "user" not in params and self.default_user:
            params["user"] = self.default_user

        return params

    def send(
        self,
        preset_name: str,
        overrides: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        """
        Build params and dispatch the request via the injected client.

        The client is expected to expose a method compatible with:
            client.post_chat_completions(payload: dict) -> dict
        Adjust this call to match your real OpenAIClient interface.
        """
        self.logger.info(f"Sending request for preset: {preset_name}")
        payload = self.build_params(preset_name, overrides=overrides)

        # ðŸ”§ Adjust this to your real client API:
        # e.g. self.client.create_chat_completion(**payload)
        # or    self.client.post("chat/completions", json=payload)
        return self.client.post_chat_completions(payload)

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #
    @classmethod
    def _deep_merge(
        cls,
        target: MutableMapping[str, Any],
        updates: Mapping[str, Any],
    ) -> None:
        """
        In-place deep merge of 'updates' into 'target'.

        - Dict values are merged recursively.
        - Non-dict values overwrite.
        - Lists are overwritten by default (you can customize if needed).
        """
        for key, value in updates.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, Mapping)
            ):
                cls._deep_merge(target[key], value)
            else:
                target[key] = copy.deepcopy(value)
