# === CONTEXT START ===
# This module represents Tetris pieces and their behaviors.
# It includes the Tetromino class with fields for shape and position.
# The module also implements a rotate method to rotate the tetromino shape.
# === CONTEXT END ===

class Tetromino:
    def __init__(self, shape, position=(0, 0)):
        """
        Initialize a Tetromino with a given shape and position.

        :param shape: A list of lists representing the tetromino shape.
        :param position: A tuple (x, y) representing the tetromino's position on the board.
        """
        self.shape = shape
        self.position = position

    def rotate(self):
        """
        Rotate the tetromino shape 90 degrees clockwise.
        """
        # Transpose the shape matrix and then reverse each row to achieve a 90-degree rotation
        self.shape = [list(row) for row in zip(*self.shape[::-1])]

    def __str__(self):
        """
        Return a string representation of the tetromino for debugging.
        """
        return '\n'.join([''.join(row) for row in self.shape])
