from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional
import copy


class AIProfileLoader:
    """
    Loads JSON preset profiles from a directory and provides them as dictionaries.

    Features:
    - Loads all *.json files from a directory.
    - Each file may contain:
        A) a single profile object  (with keys like 'model', 'messages', etc.), or
        B) a mapping of multiple profiles, e.g. { "fast_chat": {...}, "code_generation": {...} }.
    - Uses the JSON 'name' field or filename stem (case A), or the dict key (case B) as profile name.
    - Applies simple placeholder substitution (e.g. ${default_user}).
    - Caches loaded profiles in-memory.
    """

    def __init__(
        self,
        profiles_dir: str | Path,
        default_user: str = "onat",
        extra_placeholders: Optional[Mapping[str, str]] = None,
        encoding: str = "utf-8",
    ) -> None:
        self.profiles_dir = Path(profiles_dir)
        self.encoding = encoding

        # Placeholder map, e.g. {"${default_user}": "onat"}
        placeholder_map: Dict[str, str] = {
            "${default_user}": default_user,
        }
        if extra_placeholders:
            placeholder_map.update(extra_placeholders)

        self._placeholder_map = placeholder_map

        self._profiles: Dict[str, Dict[str, Any]] = {}
        self._loaded: bool = False

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def load_profiles(self, force_reload: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Load all JSON profiles from profiles_dir into memory.

        Returns a mapping:
            { profile_name: profile_dict }
        """
        if self._loaded and not force_reload:
            return copy.deepcopy(self._profiles)

        if not self.profiles_dir.exists():
            raise FileNotFoundError(
                f"Profiles directory does not exist: {self.profiles_dir}"
            )

        loaded: Dict[str, Dict[str, Any]] = {}

        for path in sorted(self.profiles_dir.glob("*.json")):
            with path.open("r", encoding=self.encoding) as f:
                raw = json.load(f)

            # Case A: file holds a single profile dict at the top level.
            # We treat it as a profile if it looks like a payload: has 'model' or 'messages'
            # or explicitly defines 'name'.
            if isinstance(raw, dict) and (
                "model" in raw or "messages" in raw or "name" in raw
            ):
                profile_name = raw.get("name") or path.stem
                processed = self._apply_placeholders(raw)
                loaded[profile_name] = processed
                continue

            # Case B: file holds multiple profiles in a mapping:
            # { "fast_chat": {...}, "code_generation": {...} }
            if isinstance(raw, dict):
                for profile_name, profile_body in raw.items():
                    if not isinstance(profile_body, dict):
                        # Skip non-dict items silently; they are not valid profiles.
                        continue
                    processed = self._apply_placeholders(profile_body)
                    loaded[profile_name] = processed
                continue

            # Anything else is considered invalid.
            raise ValueError(
                f"Unsupported JSON structure in profile file: {path}. "
                "Expected a dict representing a single profile or a dict of profiles."
            )

        self._profiles = loaded
        self._loaded = True

        return copy.deepcopy(self._profiles)

    def get_profile(self, name: str) -> Dict[str, Any]:
        """
        Return a single profile by name.

        Raises KeyError if not found.
        """
        if not self._loaded:
            self.load_profiles()

        try:
            return copy.deepcopy(self._profiles[name])
        except KeyError as exc:
            known = ", ".join(sorted(self._profiles)) or "<none>"
            raise KeyError(
                f"Unknown profile '{name}'. Known profiles: {known}"
            ) from exc

    def get_all_profiles(self) -> Dict[str, Dict[str, Any]]:
        """
        Convenience: return all loaded profiles.
        """
        if not self._loaded:
            self.load_profiles()
        return copy.deepcopy(self._profiles)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _apply_placeholders(self, obj: Any) -> Any:
        """
        Recursively apply string placeholder substitution on a JSON-like object.
        """
        if isinstance(obj, dict):
            return {k: self._apply_placeholders(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._apply_placeholders(v) for v in obj]
        if isinstance(obj, str):
            return self._replace_in_string(obj)
        return obj

    def _replace_in_string(self, value: str) -> str:
        """
        Replace occurrences of ${...} placeholders in a string.
        """
        result = value
        for placeholder, replacement in self._placeholder_map.items():
            if placeholder in result:
                result = result.replace(placeholder, replacement)
        return result
