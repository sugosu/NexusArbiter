# core/actions/registry.py
from __future__ import annotations

from typing import Dict, Type, Optional

from core.actions.base_action import BaseAction
from core.actions.file_write_action import FileWriteAction
from core.actions.continue_action import ContinueAction
from core.actions.break_action import BreakAction
from core.actions.rerun_action import RerunAction


class ActionRegistry:
    """
    Central registry for all action types in aiAgency.

    - Actions are identified by their `action_type` string.
    - Models emit actions with a `"type"` field that must match a registered
      action_type.
    """

    _registry: Dict[str, Type[BaseAction]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    @classmethod
    def register_defaults(cls) -> None:
        """
        Register all core built-in actions.

        This should be called once at AppRunner initialization.
        """
        cls.register(FileWriteAction)
        cls.register(ContinueAction)
        cls.register(BreakAction)
        cls.register(RerunAction)

    @classmethod
    def register(cls, action_cls: Type[BaseAction]) -> None:
        """
        Register a new action class.

        The class must define a non-empty string attribute `action_type`.
        """
        action_type = getattr(action_cls, "action_type", None)

        if not isinstance(action_type, str) or not action_type:
            raise ValueError(
                f"Cannot register action {action_cls!r}: "
                f"missing or invalid 'action_type' attribute."
            )

        cls._registry[action_type] = action_cls

    # ------------------------------------------------------------------
    # Lookup / creation
    # ------------------------------------------------------------------
    @classmethod
    def get(cls, action_type: str) -> Optional[Type[BaseAction]]:
        """
        Return the registered action class for the given type, or None
        if it is not registered.
        """
        return cls._registry.get(action_type)

    @classmethod
    def create(cls, action_type: str) -> BaseAction:
        """
        Instantiate a previously registered action class.

        Raises:
            ValueError if the action type is not registered.
        """
        action_cls = cls._registry.get(action_type)
        if action_cls is None:
            raise ValueError(
                f"Action type '{action_type}' is not registered. "
                f"Available types: {list(cls._registry.keys())}"
            )

        return action_cls()
