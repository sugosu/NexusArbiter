# === CONTEXT START ===
# Action that writes arbitrary text (typically JSON) into a file under the project
# root. Ensures the directory exists and writes the content exactly as provided.
# === CONTEXT END ===

import logging
from pathlib import Path
from .base_action import BaseAction
from .registry import ActionRegistry

logger = logging.getLogger(__name__)

class GenerateProfileFileAction(BaseAction):
    action_type = "generate_profile_file"

    def validate(self) -> bool:
        target_path = self.params.get('target_path')
        content = self.params.get('content')
        if not isinstance(target_path, str) or not target_path:
            logger.error("Validation failed: 'target_path' must be a non-empty string.")
            return False
        if not isinstance(content, str) or not content:
            logger.error("Validation failed: 'content' must be a non-empty string.")
            return False
        return True

    def execute(self, ctx) -> None:
        target_path = self.params['target_path']
        content = self.params['content']
        context = self.params.get('context', '')

        full_path = Path(ctx.project_root) / target_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with full_path.open('w', encoding='utf-8') as file:
            file.write(content)

        logger.info(f"Generated file at {full_path.absolute()}. {context}")

ActionRegistry.register(GenerateProfileFileAction)
