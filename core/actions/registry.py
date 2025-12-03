# core/actions/registry.py
from typing import Dict, List, Optional, Type

from .base_action import BaseAction


class ActionRegistry:

    _registry: Dict[str, Type[BaseAction]] = {}

    @classmethod
    def register(cls, action_cls: Type[BaseAction]) -> None:
        if not action_cls.action_type:
            raise ValueError(f"Action {action_cls} must define action_type")
        cls._registry[action_cls.action_type] = action_cls

    @classmethod
    def create(cls, raw_action: dict) -> Optional[BaseAction]:
        action_type = raw_action.get("type")
        if not action_type:
            return None

        action_cls = cls._registry.get(action_type)
        if action_cls is None:
            return None

        return action_cls.from_raw(raw_action)

    @classmethod
    def allowed_types(cls) -> List[str]:
        """Return the list of registered action type strings."""
        return list(cls._registry.keys())
