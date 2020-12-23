import random
import re

import numpy as np


class Minesweeper:
    board = None

    def __init__(self, width: int = 16, height: int = 16, bombs: int = 40):

        if bombs > width * height:
            raise OverflowError("More bombs than tiles")

        # Create empty board
        board = np.zeros(width * height, dtype=int)

        # Add bombs
        for i in range(bombs):
            board[i] = 1

        # Shuffle bombs around
        np.random.default_rng().shuffle(board)

        # Shape board into desired dimensions
        board = board.reshape((height, width))

        # Label tiles around bombs
        self.board = Minesweeper.explore(board)

    @classmethod
    def explore(cls, board: np.ndarray) -> np.ndarray:
        """Mark every tile with the number of bombs in 3x3 area surrounding it, bombs marked as -1"""

        height, width = board.shape
        explored = np.zeros((height, width), dtype=int)

        def mark_adjacent(x, y):
            """Increment value of 3x3 tiles around bomb by 1"""
            for i in range(max(0, x - 1), min(width, x + 2)):
                for j in range(max(0, y - 1), min(height, y + 2)):
                    explored[j][i] += 1

        for y in range(height):
            for x in range(width):
                if board[y][x] == 1:
                    mark_adjacent(x, y)
                    explored[y][x] = -10

        return explored.clip(-1, 9)

    def to_string(self, spoiler: bool = False) -> str:
        string = ""

        # Add each row
        for row in self.board[::-1]:
            string += "_" + "_".join([str(n) for n in row])
            string += "\n"

        tiles = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "💣"]

        if not spoiler:
            for i in range(-1, 10):
                string = string.replace(f"_{i}", f"{tiles[i]}")
        else:
            for i in range(-1, 10):
                string = string.replace(f"_{i}", f"||{tiles[i]}||")

            # Remove spoiler on one non-bomb tile (attempt to find tile with the lowest adjacent bombs)
            for i in range(10):
                matches = list(re.finditer(f"\\|\\|{tiles[i]}\\|\\|", string))
                if len(matches) != 0:
                    replace = random.choice(matches)
                    return string[:replace.start()] + tiles[i] + string[replace.end():]

        return string
