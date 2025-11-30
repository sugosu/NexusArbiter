# core/actions/file_read.py
from pathlib import Path
from .base_action import BaseAction, ActionContext
from .registry import ActionRegistry

class FileReadAction(BaseAction):
    """
    Safely reads a text file from the project.
    Returns the content so the agent can use it.
    """
    action_type = "file_read"

    def validate(self) -> bool:
        target_path = self.params.get("target_path")
        return isinstance(target_path, str) and bool(target_path)

    def execute(self, ctx: ActionContext) -> None:
        if not self.validate():
            ctx.logger.warning(f"[file_read] Invalid params: {self.params!r}")
            return

        # 1. SECURITY FIX: Prevent Directory Traversal
        raw_path = self.params["target_path"]
        # Resolve to absolute path
        safe_root = Path(ctx.project_root).resolve()
        requested_path = (safe_root / raw_path).resolve()

        # Check if the resolved path is actually inside the project root
        if not str(requested_path).startswith(str(safe_root)):
            ctx.logger.error(f"[file_read] SECURITY ALERT: Attempted path traversal to '{raw_path}'")
            # Return an error message to the agent so it learns not to do this
            ctx.add_result(f"Error: Access denied. Path '{raw_path}' is outside project root.")
            return

        if not requested_path.exists():
             ctx.logger.error(f"[file_read] File not found: {requested_path}")
             ctx.add_result(f"Error: File '{raw_path}' does not exist.")
             return

        # 2. BUG FIX: Use standard Path method (no missing 'PythonFileReader')
        try:
            content = requested_path.read_text(encoding='utf-8')
            
            # 3. FEATURE FIX: Return content to the agent
            ctx.logger.info(f"[file_read] Successfully read '{raw_path}' ({len(content)} chars)")
            
            # This is crucial for Data Engineering! 
            # The agent needs to SEE the content to generate the next SQL step.
            ctx.add_result(f"Content of {raw_path}:\n{content}")

        except Exception as e:
            ctx.logger.error(f"[file_read] Error reading file: {e}")
            ctx.add_result(f"Error reading file: {str(e)}")

# Register
ActionRegistry.register(FileReadAction)