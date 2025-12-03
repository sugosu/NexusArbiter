import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union


def _normalize_key(name: str) -> str:
    """
    Normalize JSON keys so we can accept variations like:
    profile_file, Profile_File, profileFile, etc.
    """
    return name.replace("_", "").lower()


def _get_field(
    item: Mapping[str, Any],
    logical_name: str,
    required: bool = False,
    default: Optional[Any] = None,
) -> Any:
    """
    Fetch a field from a JSON object in a tolerant way:
    - Treat 'Profile_File', 'profile_file', 'profileFile' as the same.
    """
    target = _normalize_key(logical_name)

    for key, value in item.items():
        if _normalize_key(key) == target:
            return value

    if required:
        raise ValueError(f"Missing required field '{logical_name}' in run item: {item}")
    return default


@dataclass
class RunItem:
    # REQUIRED: path to the profile file relative to project_root
    profile_file: str  # e.g. "context_files/profiles/code_generation.json"

    class_name: Optional[str] = None

    # Human-readable description of *this run*. Usually a short sentence
    # describing what we expect the model to do (e.g. "Generate board.py").
    task_description: str = ""

    # Optional free-form "rules" to be injected as a block into the system
    # prompt or similar.
    rules: List[str] = field(default_factory=list)

    # Extra parameters (could be model-specific).
    extra_params: Dict[str, Any] = field(default_factory=dict)

    # Pre-structured agent input that we attach inside the profile's payload.
    agent_input: Dict[str, Any] = field(default_factory=dict)

    # List of files (relative to project_root) that the agent should see
    # as context for this run. The loader is responsible for interpreting
    # this list (e.g. JSON vs plain text).
    context_file: List[str] = field(default_factory=list)

    # If non-empty, the generated code (e.g. from a file_write action) is
    # expected to be written to this path (relative to the project root).
    target_file: str = ""

    # How many times we allow a run to be retried (in addition to the
    # initial attempt). This is logical/agent-driven retry.
    retry: int = 0

    # Optional list of alternative context files to use specifically in
    # retry attempts, instead of `context_file`.
    retry_context_files: List[str] = field(default_factory=list)

    # Optional white-list of action types the model is allowed to use.
    # If empty, any registered action type is allowed.
    allowed_actions: List[str] = field(default_factory=list)

    # Optional provider for this run ("openai", "gemini", ...).
    # If None, the engine falls back to:
    #   - config-level provider,
    #   - environment default,
    #   - or "openai".
    provider: Optional[str] = None

    # Raw JSON for debugging / logging
    raw: Dict[str, Any] = field(default_factory=dict)


class RunConfig:
    """
    Parses a JSON config file describing one or more runs.

    Supported root structures:

    1) {
         "provider": "openai",   # optional config-level default provider
         "retry_from": 2,        # optional pipeline-level restart index (1-based)
         "runs": [ { ... }, ... ]
       }

    2) { ... }                     # single run object

    3) [ { ... }, { ... } ]        # array of runs

    Notes:
    - retry_from, if present, indicates that the pipeline should start from
      that run index (1-based).
    - provider, if present, is used as a default for all runs that do not
      specify their own provider.
    """

    def __init__(
        self,
        runs: List[RunItem],
        retry_from: Optional[int] = None,
        provider: Optional[str] = None,
    ) -> None:
        self.runs = runs
        self.retry_from = retry_from
        # Optional config-level default provider (already normalised to lowercase).
        self.provider = provider

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------
    @classmethod
    def from_json(cls, raw_json: str) -> "RunConfig":
        data = json.loads(raw_json)
        return cls._parse(data)

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "RunConfig":
        """
        Load a RunConfig from a JSON file.

        Accepts either a string path or a pathlib.Path instance.
        """
        p = Path(path)
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return cls._parse(data)


    # ------------------------------------------------------------------
    # Internal parsing
    # ------------------------------------------------------------------
    @staticmethod
    def _parse(data: Any) -> "RunConfig":
        """
        Parse the top-level JSON structure into a RunConfig.
        """
        items: List[Mapping[str, Any]]
        retry_from_raw: Optional[Any] = None
        default_provider_raw: Optional[Any] = None

        if isinstance(data, dict):
            # Multi-run or object-with-runs
            if "runs" in data and isinstance(data["runs"], list):
                items = data["runs"]
            else:
                # Interpret as a single run object
                items = [data]

            retry_from_raw = data.get("retry_from")
            default_provider_raw = data.get("provider")

        elif isinstance(data, list):
            # Bare array of run-like objects
            items = data
        else:
            raise ValueError("Config root must be an object or an array.")

        # Normalise retry_from
        retry_from: Optional[int] = None
        if retry_from_raw is not None:
            try:
                rf = int(retry_from_raw)
                if rf < 1:
                    raise ValueError("retry_from must be >= 1 if provided.")
                retry_from = rf
            except (TypeError, ValueError):
                raise ValueError("retry_from must be an integer >= 1.")

        # Normalise config-level default provider (if present)
        default_provider: Optional[str] = None
        if default_provider_raw is not None:
            if not isinstance(default_provider_raw, str):
                raise ValueError("Top-level 'provider' must be a string if provided.")
            provider_name = default_provider_raw.strip().lower()
            default_provider = provider_name or None

        runs: List[RunItem] = []

        for idx, item in enumerate(items, start=1):
            if not isinstance(item, Mapping):
                raise ValueError(f"Run #{idx} must be a JSON object, got {type(item)!r}")

            profile_file = _get_field(item, "profile_file", required=True)
            class_name = _get_field(item, "class_name", required=False, default=None)

            task_desc = _get_field(item, "task_description", required=False, default="")

            rules = _get_field(item, "rules", required=False, default=[])
            if not isinstance(rules, list):
                raise ValueError(f"'rules' must be a list in run #{idx}")

            extra_params = _get_field(item, "extra_params", required=False, default={})
            if not isinstance(extra_params, dict):
                raise ValueError(f"'extra_params' must be an object in run #{idx}")

            agent_input = _get_field(item, "agent_input", required=False, default={})
            if not isinstance(agent_input, dict):
                raise ValueError(f"'agent_input' must be an object in run #{idx}")

            context_file = _get_field(item, "context_file", required=False, default=[])
            if isinstance(context_file, str):
                context_file = [context_file]
            if not isinstance(context_file, list):
                raise ValueError(f"'context_file' must be a string or list in run #{idx}")

            target_file = _get_field(item, "target_file", required=False, default="")
            if target_file is None:
                target_file = ""

            retry = _get_field(item, "retry", required=False, default=0)
            try:
                retry = int(retry)
            except (TypeError, ValueError):
                retry = 0
            if retry < 0:
                raise ValueError(f"'retry' cannot be negative in run #{idx}")

            retry_context_files = _get_field(
                item, "retry_context_files", required=False, default=[]
            )
            if isinstance(retry_context_files, str):
                retry_context_files = [retry_context_files]
            if not isinstance(retry_context_files, list):
                raise ValueError(
                    f"'retry_context_files' must be a string or list in run #{idx}"
                )

            allowed_actions = _get_field(
                item, "allowed_actions", required=False, default=[]
            )
            if isinstance(allowed_actions, str):
                allowed_actions = [allowed_actions]
            if not isinstance(allowed_actions, list):
                raise ValueError(
                    f"'allowed_actions' must be a string or list in run #{idx}"
                )

            # Run-level provider (overrides config-level default if present)
            provider_raw = _get_field(item, "provider", required=False, default=None)
            provider: Optional[str] = None
            if provider_raw is not None:
                if not isinstance(provider_raw, str):
                    raise ValueError(f"'provider' must be a string in run #{idx}")
                provider_name = provider_raw.strip().lower()
                provider = provider_name or None
            else:
                provider = default_provider

            run_item = RunItem(
                profile_file=str(profile_file),
                class_name=class_name,
                task_description=str(task_desc),
                rules=list(rules),
                extra_params=dict(extra_params),
                agent_input=dict(agent_input),
                context_file=list(context_file),
                target_file=str(target_file),
                retry=int(retry),
                retry_context_files=list(retry_context_files),
                allowed_actions=list(allowed_actions),
                provider=provider,
                raw=dict(item),
            )

            runs.append(run_item)

        return RunConfig(runs=runs, retry_from=retry_from, provider=default_provider)
