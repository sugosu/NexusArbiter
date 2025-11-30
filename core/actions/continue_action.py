from .base_action import BaseAction
from .registry import ActionRegistry
import logging

class ContinueAction(BaseAction):
    action_type = "continue"

    def validate(self) -> bool:
        """
        Validate the parameters for the ContinueAction.

        Returns:
            bool: True if parameters are valid, False otherwise.
        """
        should_break = self.params.get("should_break")
        reason = self.params.get("reason")

        if not isinstance(should_break, bool):
            logging.error("Validation failed: 'should_break' must be a boolean.")
            return False

        if reason is not None and not isinstance(reason, str):
            logging.error("Validation failed: 'reason' must be a string or None.")
            return False

        return True

    def execute(self, ctx) -> None:
        """
        Execute the ContinueAction based on the parameters.

        Args:
            ctx: The context in which the action is executed.
        """
        should_break = self.params["should_break"]
        reason = self.params.get("reason", "No reason provided.")

        if should_break:
            logging.error(f"ContinueAction requested termination: {reason}")
            raise RuntimeError(f"ContinueAction requested termination: {reason}")
        else:
            logging.info("ContinueAction is a no-op. The script will proceed normally.")

ActionRegistry.register(ContinueAction)
