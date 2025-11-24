# === CONTEXT START ===
# This class scans a specified directory for Python files, extracts class names,
# and builds an index mapping class names to their file paths.
# === CONTEXT END ===

class GeneratePathIndexAction:
    def __init__(self, directory):
        self.directory = directory

    def build_index(self):
        import os
        index = {}
        for root, _, files in os.walk(self.directory):
            for file in files:
                if file.endswith('.py'):
                    module_path = os.path.join(root, file)
                    class_name = self.extract_class_name(module_path)
                    if class_name:
                        index[class_name] = module_path
        return index

    def extract_class_name(self, file_path):
        with open(file_path, 'r') as file:
            for line in file:
                if line.startswith('class '):
                    return line.split()[1].split('(')[0]
        return None