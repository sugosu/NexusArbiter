# === CONTEXT START ===
# This module handles game configuration settings for a Tetris game.
# It includes the GameConfig class with fields for board_width, board_height, and tick_rate.
# The module provides a method to load these settings from a file.
# === CONTEXT END ===

import json

class GameConfig:
    def __init__(self, board_width=10, board_height=20, tick_rate=1.0):
        self.board_width = board_width
        self.board_height = board_height
        self.tick_rate = tick_rate

    @classmethod
    def load_from_file(cls, file_path):
        """
        Load game configuration from a JSON file.

        :param file_path: Path to the configuration file.
        :return: An instance of GameConfig with settings loaded from the file.
        """
        with open(file_path, 'r') as file:
            config_data = json.load(file)
            return cls(
                board_width=config_data.get('board_width', 10),
                board_height=config_data.get('board_height', 20),
                tick_rate=config_data.get('tick_rate', 1.0)
            )
