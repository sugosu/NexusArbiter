# core/actions/generate_class_file.py
from pathlib import Path
from .base_action import BaseAction, ActionContext
from .registry import ActionRegistry


class GenerateClassFileAction(BaseAction):
    action_type = "generate_class_file"

    def validate(self) -> bool:
        if not isinstance(self.params.get("target_path"), str):
            return False
        if not isinstance(self.params.get("code"), str):
            return False
        return True

    def execute(self, ctx: ActionContext) -> None:
        logger = ctx.logger

        target_path = self.params["target_path"]
        code = self.params["code"]
        context_text = self.params.get("context", "")

        target_rel_path = Path(target_path)
        abs_target_dir = (ctx.project_root / target_rel_path).parent
        abs_target_dir.mkdir(parents=True, exist_ok=True)

        gen = ctx.class_generator
        original_base = gen.base_path
        try:
            gen.base_path = str(abs_target_dir)
            generated_path = gen.generate_with_comments(
                filename=target_rel_path.name,
                content=code,
                comments=context_text,
            )
        finally:
            gen.base_path = original_base

        logger.info(f"Generated class file at: {generated_path}")


# 👇 THIS LINE IS CRITICAL
ActionRegistry.register(GenerateClassFileAction)
