# core/actions/registry.py
from __future__ import annotations

from typing import Dict, Optional, Type

from core.actions.base_action import BaseAction
from core.actions.break_action import BreakAction
from core.actions.continue_action import ContinueAction
from core.actions.file_write_action import FileWriteAction



class ActionRegistry:
    """Maps action_type -> action class."""

    _registry: Dict[str, Type[BaseAction]] = {}
    _defaults_registered: bool = False

    @classmethod
# core/actions/registry.py
    def register_defaults(cls) -> None:
        if cls._defaults_registered:
            return

        cls.register(FileWriteAction)
        cls.register(ContinueAction)
        cls.register(BreakAction)

        cls._defaults_registered = True


    @classmethod
    def register(cls, action_cls: Type[BaseAction]) -> None:
        action_type = getattr(action_cls, "action_type", None)
        if not isinstance(action_type, str) or not action_type.strip():
            raise ValueError(f"Cannot register action {action_cls!r}: invalid action_type")

        cls._registry[action_type] = action_cls

    @classmethod
    def get(cls, action_type: str) -> Optional[Type[BaseAction]]:
        return cls._registry.get(action_type)

    @classmethod
    def create(cls, action_type: str) -> BaseAction:
        action_cls = cls._registry.get(action_type)
        if action_cls is None:
            available = ", ".join(sorted(cls._registry.keys()))
            raise ValueError(f"Action type '{action_type}' is not registered. Available: {available}")

        return action_cls()
