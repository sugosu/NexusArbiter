# core/actions/base_action.py
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping


@dataclass
class ActionContext:

    project_root: Any
    file_writer: Any        # FileWriter-like object
    git_manager: Any
    repo_config: Any
    logger: Any
    # Optional place for actions to push small textual results for debugging
    results: List[str] = field(default_factory=list)

    def add_result(self, value: str) -> None:
        """Append a small textual result produced by an action."""
        self.results.append(value)


class BaseAction:

    action_type: str = ""

    def __init__(self, params: Mapping[str, Any] | None = None) -> None:
        self.params: Dict[str, Any] = dict(params or {})

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any]) -> "BaseAction":
        params = raw.get("params", {}) if isinstance(raw, Mapping) else {}
        return cls(params)

    def validate(self) -> bool:
        """Basic validation hook. Subclasses override if needed."""
        return True

    def execute(self, ctx: ActionContext) -> None:
        """Perform the action. Subclasses must implement."""
        raise NotImplementedError("Subclasses must implement execute()")
