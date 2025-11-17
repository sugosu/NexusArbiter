# === CONTEXT START ===
# Added logging to the PythonFileReader class using BasicLogger. Logging
# statements are included to track the file reading process and handle errors.
# === CONTEXT END ===

import os
from core.logger import BasicLogger

class PythonFileReader:
    def __init__(self, file_path):
        self.file_path = file_path
        self.logger = BasicLogger(self.__class__.__name__).get_logger()

    def read_file(self):
        self.logger.info(f'Reading file: {self.file_path}')
        if not os.path.isfile(self.file_path):
            self.logger.error(f'File not found: {self.file_path}')
            raise FileNotFoundError(f"The file {self.file_path} does not exist.")
        if not self.file_path.endswith('.py'):
            self.logger.error(f'Invalid file type: {self.file_path}')
            raise ValueError("The file is not a Python (.py) file.")
        with open(self.file_path, 'r') as file:
            content = file.read()
            self.logger.info(f'Successfully read file: {self.file_path}')
            return content

# Example usage:
# reader = PythonFileReader('example.py')
# code_string = reader.read_file()
# print(code_string)
