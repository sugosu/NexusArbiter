from typing import Dict, Type
from .base_action import BaseAction

class ActionRegistry:
    _registry: Dict[str, Type[BaseAction]] = {}

    @classmethod
    def register(cls, action_cls: Type[BaseAction]):
        cls._registry[action_cls.action_type] = action_cls

    @classmethod
    def create(cls, raw_action: dict) -> BaseAction | None:
        action_type = raw_action.get("type")
        params = raw_action.get("params", {})

        if action_type not in cls._registry:
            return None

        return cls._registry[action_type].from_raw(raw_action)

    @classmethod
    def allowed_types(cls):
        return list(cls._registry.keys())
