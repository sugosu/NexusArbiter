import json
from dataclasses import dataclass
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
    """
    A single run/task configuration.
    """
    profile_name: str
    class_name: str
    task_description: str
    refactor_class: str = ""
    raw: Dict[str, Any] = None  # full raw dict for future use


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

            profile_name = _get_field(item, "profile_name", required=True)
            class_name = _get_field(item, "class_name", required=True)
            task_description = _get_field(item, "task_description", required=True)
            refactor_class = _get_field(item, "refactor_class", required=False, default="")

            # Heuristic: for refactor-type profiles, if no explicit refactor_class is
            # provided, assume we refactor the same file as class_name.
            if not refactor_class and "refactor" in str(profile_name).lower():
                refactor_class = class_name

            runs.append(
                RunItem(
                    profile_name=str(profile_name),
                    class_name=str(class_name),
                    task_description=str(task_description),
                    refactor_class=str(refactor_class),
                    raw=dict(item),
                )
            )

        return RunConfig(runs)
