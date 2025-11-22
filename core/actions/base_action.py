from dataclasses import dataclass
from typing import Any, Dict, Mapping

@dataclass
class ActionContext:
    project_root: Any
    class_generator: Any
    git_manager: Any
    repo_config: Any
    logger: Any

class BaseAction:
    """
    Abstract base class for all actions.
    """

    action_type: str = None  # override in subclasses

    def __init__(self, params: Mapping[str, Any]):
        self.params = params

    @classmethod
    def from_raw(cls, raw: Mapping[str, Any]):
        params = raw.get("params", {})
        return cls(params)

    def validate(self):
        """Override if needed."""
        return True

    def execute(self, ctx: ActionContext):
        """Override in subclasses."""
        raise NotImplementedError
