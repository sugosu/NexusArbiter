import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


def _normalize_key(name: str) -> str:
    """
    Normalize JSON keys so we can accept variations like:
    profile_name, Profile_Name, profileName, etc.
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
    - Treat 'Profile_Name', 'profile_name', 'profilename' as the same.
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
    # OLD fields (now optional / defaulted)
    profile_name: str = ""                     # optional in new mode
    class_name: Optional[str] = None           # optional in new mode
    task_description: str = ""                 # still required logically

    refactor_class: str = ""                   # used by main.py / app.main
    rules: List[str] = field(default_factory=list)
    extra_params: Dict[str, Any] = field(default_factory=dict)
    agent_input: Dict[str, Any] = field(default_factory=dict)

    # NEW fields
    context_file: List[str] = field(default_factory=list)
    target_file: str = ""

    # full raw dict for future use
    raw: Dict[str, Any] = field(default_factory=dict)



class RunConfig:
    """
    Parses a JSON config file describing one or more runs.

    Supported root structures:

    1) { "runs": [ { ... }, { ... } ] }
    2) [ { ... }, { ... } ]
    """

    def __init__(self, runs: List[RunItem]) -> None:
        self.runs = runs

    @staticmethod
    def from_file(path: str) -> "RunConfig":
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return RunConfig._parse(data)

    @staticmethod
    def _parse(data: Any) -> "RunConfig":
        if isinstance(data, dict):
            if "runs" in data and isinstance(data["runs"], list):
                items = data["runs"]
            else:
                # Single run as object
                items = [data]
        elif isinstance(data, list):
            items = data
        else:
            raise ValueError("Config root must be an object or an array.")

        runs: List[RunItem] = []

        for idx, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"Run #{idx} must be an object, got: {type(item)}")

            # Detect "new style" runs: driven by context_file/target_file
            has_context = "context_file" in item or "context_files" in item

            if has_context:
                # NEW MODE: context_file + target_file + task_description
                # profile_name/class_name become optional/logging-only.
                profile_name = _get_field(item, "profile_name", required=False, default="")
                class_name = _get_field(item, "class_name", required=False, default=None)
                task_description = _get_field(item, "task_description", required=True)

                # Normalize context_file to a list[str]
                context_file_raw = item.get("context_file") or item.get("context_files") or []
                if isinstance(context_file_raw, str):
                    context_file = [context_file_raw]
                elif isinstance(context_file_raw, list):
                    context_file = [str(x) for x in context_file_raw]
                else:
                    raise ValueError(
                        f"Run #{idx}: 'context_file' must be string or list of strings."
                    )

                target_file = str(item.get("target_file", ""))

                refactor_class = _get_field(
                    item, "refactor_class", required=False, default=""
                )

            else:
                # OLD MODE: profile_name/class_name/task_description required
                profile_name = _get_field(item, "profile_name", required=True)
                class_name = _get_field(item, "class_name", required=True)
                task_description = _get_field(item, "task_description", required=True)
                refactor_class = _get_field(
                    item, "refactor_class", required=False, default=""
                )

                # Heuristic: for refactor-type profiles, if no explicit refactor_class is
                # provided, assume we refactor the same file as class_name.
                if not refactor_class and "refactor" in str(profile_name).lower():
                    refactor_class = class_name

                context_file = []   # none in old mode
                target_file = ""    # none in old mode

            # Optional fields from the run JSON
            rules = item.get("rules", [])
            extra_params = item.get("extra_params", {})
            agent_input = item.get("agent_input", {})

            runs.append(
                RunItem(
                    profile_name=str(profile_name),
                    class_name=str(class_name) if class_name is not None else None,
                    task_description=str(task_description),
                    refactor_class=str(refactor_class) if refactor_class is not None else "",
                    rules=list(rules) if isinstance(rules, list) else [],
                    extra_params=dict(extra_params) if isinstance(extra_params, dict) else {},
                    agent_input=dict(agent_input) if isinstance(agent_input, dict) else {},
                    context_file=context_file,
                    target_file=target_file,
                    raw=dict(item),
                )
            )


        return RunConfig(runs)
