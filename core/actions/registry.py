from __future__ import annotations
from typing import Dict, Type

from core.actions.base_action import BaseAction
from core.actions.file_write_action import FileWriteAction
from core.actions.continue_action import ContinueAction
from core.actions.break_action import BreakAction
from core.actions.rerun_action import RerunAction


class ActionRegistry:
    """
    Central registry for all action types in aiAgency.
    Model output actions are matched by their "type" field.
    """

    _registry: Dict[str, Type[BaseAction]] = {}

    @classmethod
    def register_defaults(cls) -> None:
        """
        Register all core built-in actions.
        This should be called once at AppRunner init.
        """
        cls.register(FileWriteAction)
        cls.register(ContinueAction)
        cls.register(BreakAction)
        cls.register(RerunAction)

    @classmethod
    def register(cls, action_cls: Type[BaseAction]) -> None:
        """
        Register a new action class.
        """
        action_type = getattr(action_cls, "action_type", None)
        if not isinstance(action_type, str) or not action_type:
            raise ValueError(
                f"Cannot register action {action_cls}: missing or invalid action_type"
            )

        cls._registry[action_type] = action_cls

    @classmethod
    def create(cls, action_type: str) -> BaseAction:
        """
        Instantiate a previously registered action class.
        """
        if action_type not in cls._registry:
            raise ValueError(
                f"Action type '{action_type}' is not registered. "
                f"Available: {list(cls._registry.keys())}"
            )

        return cls._registry[action_type]()
