# === CONTEXT START ===
# This code defines a BasicLogger class that can be easily initialized in other
# classes to provide logging functionality. The logger is configured with a stream
# handler and a formatter, and it ensures that multiple handlers are not added to
# the logger. The example in the comment shows how to use the BasicLogger in
# another class by initializing it with the class name and using it to log
# messages.
# === CONTEXT END ===

import logging

class BasicLogger:
    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)

    def get_logger(self):
        return self.logger

# Example of how to implement the logger in another class:
#
# class MyClass:
#     def __init__(self):
#         self.logger = BasicLogger(self.__class__.__name__).get_logger()
#
#     def do_something(self):
#         self.logger.info('Doing something')
#
# my_instance = MyClass()
# my_instance.do_something()
