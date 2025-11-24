# === CONTEXT START ===
# Class that generates a path index for all files in a given directory, excluding
# files listed in .gitignore, and saves the index to a JSON file.
# === CONTEXT END ===

class PathIndexGenerator:
    def __init__(self, base_path):
        self.base_path = base_path
        self.index = {}

    def generate_index(self):
        import os
        for root, dirs, files in os.walk(self.base_path):
            for file in files:
                if file != '.gitignore':
                    file_path = os.path.join(root, file)
                    self.index[file_path] = os.path.getsize(file_path)
        return self.index

    def save_index(self, output_file):
        import json
        with open(output_file, 'w') as f:
            json.dump(self.index, f, indent=4)
