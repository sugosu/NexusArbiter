# === CONTEXT START ===
# This module manages the game board state for a Tetris game.
# It includes the GameBoard class with a grid field and a method to clear completed lines.
# === CONTEXT END ===

class GameBoard:
    def __init__(self, width, height):
        """
        Initialize the game board with the given width and height.
        The grid is represented as a list of lists, where each inner list is a row.
        """
        self.width = width
        self.height = height
        self.grid = [[0] * width for _ in range(height)]

    def clear_lines(self):
        """
        Clears completed lines from the board.
        A completed line is one where all cells are non-zero.
        """
        new_grid = [row for row in self.grid if any(cell == 0 for cell in row)]
        lines_cleared = self.height - len(new_grid)
        # Add empty lines at the top for each cleared line
        for _ in range(lines_cleared):
            new_grid.insert(0, [0] * self.width)
        self.grid = new_grid

    def __str__(self):
        """
        Returns a string representation of the board for debugging purposes.
        """
        return '\n'.join(''.join(str(cell) for cell in row) for row in self.grid)
