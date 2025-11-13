# === CONTEXT START ===
# The PythonFileReader class provides a simple and reliable utility for loading
# Python source files from disk and returning their contents as a raw string.
# It ensures that the requested file actually exists and validates that the
# target is a .py file before attempting to read it.
#
# This class is used by the AI-driven development framework when existing Python
# files need to be ingested, analyzed, or passed back to the model for
# refactoring. By centralizing file reading logic, the codebase avoids repetitive
# I/O operations throughout different components and maintains consistent error
# handling for missing or invalid file paths.
#
# The implementation intentionally avoids any post-processing or parsing of the
# file's content. It returns the exact text of the file as-is, preserving
# formatting, comments, and structure so that downstream processes — such as
# code generation, diffing, or context injection — receive the full and accurate
# representation of the original source.
# === CONTEXT END ===


import os

class PythonFileReader:
    def __init__(self, file_path):
        self.file_path = file_path

    def read_file(self):
        if not os.path.isfile(self.file_path):
            raise FileNotFoundError(f"The file {self.file_path} does not exist.")
        if not self.file_path.endswith('.py'):
            raise ValueError("The file is not a Python (.py) file.")
        with open(self.file_path, 'r') as file:
            return file.read()

# Example usage:
# reader = PythonFileReader('example.py')
# code_string = reader.read_file()
# print(code_string)
