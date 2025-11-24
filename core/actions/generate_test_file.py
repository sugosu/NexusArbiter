# === CONTEXT START ===
# This action generates a test file at the specified target path with the provided
# code. It validates the presence of 'code' and 'target_path' in the parameters
# before execution. The action is registered with the ActionRegistry under the
# action type 'generate_test_file'.
# === CONTEXT END ===

from core.actions.base_action import BaseAction
from core.actions.registry import ActionRegistry

class GenerateTestFileAction(BaseAction):
    action_type = 'generate_test_file'

    def validate(self, params):
        if 'code' not in params or 'target_path' not in params:
            raise ValueError("Parameters must include 'code' and 'target_path'.")

    def execute(self, params):
        self.validate(params)
        code = params['code']
        target_path = params['target_path']
        with open(target_path, 'w') as file:
            file.write(code)
        return {'status': 'success', 'message': f'Test file generated at {target_path}'}

ActionRegistry.register(GenerateTestFileAction)