import copy
import math
import random
from multiprocessing.queues import Queue

import numpy as np


evaluation_matrix = None


def create_evaluation_matrix(width, height, pieces):
    """Create 2D Gaussian mean distribution with regards to pieces needed (and width and height)"""

    # Source: https://www.w3resource.com/python-exercises/numpy/python-numpy-exercise-79.php
    # Modified and filled with magic variables to reflect amount of pieces

    # Initializing value of x-axis and y-axis in the range -2 to +2
    x, y = np.meshgrid(np.linspace(-2, 2, width), np.linspace(-2, 2, height))
    dst = np.sqrt(x * x + y * y)

    # sigma = standard deviation
    sigma = 1.79
    # muu = mean
    muu = 0.004 - pieces * 0.1

    # Calculating Gaussian array (float array)
    gauss = np.exp(-((dst - muu) ** 2 / (2.0 * sigma ** 2)))

    global evaluation_matrix
    # Convert to array of ints (rough range: 3-13 to 6-40, depends on pieces)
    evaluation_matrix = ((gauss * 200 + 14) / (60 / pieces)).astype(int)


class Board:
    width = 0
    height = 0
    winner = None

    # Internal attributes
    _board = None
    _winning_pieces = 0
    _player_piece = 1
    _ai_piece = 2

    def __init__(self, width, height, pieces):
        self.width = width
        self.height = height
        self._winning_pieces = pieces

        # (0, 0) is bottom left cell, (height - 1, width - 1) is top right cell
        self._board = np.zeros((height, width), dtype=int)

        # Recalculate evaluation matrix if doesn't exist or is of wrong dimensions
        if evaluation_matrix is None or self._board.shape != evaluation_matrix.shape:
            create_evaluation_matrix(width, height, pieces)

    def __iter__(self):
        """Return generator of rows"""

        return (row for row in self._board)

    def __getitem__(self, key):
        """Overloaded [] operator (returns board row)"""

        return self._board[key]

    def to_string(self, p1: str = "", p2: str = ""):
        """"Convert board to string"""

        # If special characters not specified, return as numpy's tostring()
        if not p1 or not p2:
            return self._board.tostring()

        string = ""
        # Add each row
        for row in self[::-1]:  # Rows are upside down, iterate backwards
            string += "_" + "_".join([str(n) for n in row])
            string += "\n"

        string = string.replace("_0", "⬛")
        string = string.replace("_1", p1)
        string = string.replace("_2", p2)

        string += "".join(["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "0️⃣"][:self.width]) + "\n"

        return string

    def column_valid(self, column):
        """Check if column exists and isn't filled yet"""

        # Out of range
        if not 0 <= column < self.width:
            return False, "Invalid column"
        # Column filled
        if not self.column_not_full(column):
            return False, "This column is full"
        return True, ""

    def column_not_full(self, column):
        """Check if column isn't filled yet"""

        if not -1 < column < self.width:
            raise ValueError(f"Column {column} out of range 0-{self.width - 1}")
        # Check only top row
        return self[self.height - 1][column] == 0

    def column_bottom(self, column):
        """Get lowest empty cell in column"""

        for row in range(self.height):
            if self[row][column] == 0:
                return row
        return self.height

    def drop_piece(self, column, piece):
        """Drop a piece to column"""

        if self.column_not_full(column):
            # Find bottom
            self[self.column_bottom(column)][column] = piece

            # If a line was connected -> set winner
            if self.was_winning_move(column, piece):
                self.winner = piece
        else:
            raise OverflowError(f"Column {column} is full")

    def game_over(self):
        """Check if someone connected enough pieces or board was filled up"""

        return self.winner is not None or self.board_full()

    def board_full(self):
        """Check if board is filled"""

        # Check every cell in top row
        for i in range(self.width):
            if self[self.height - 1][i] == 0:
                return False
        return True

    def was_winning_move(self, column, piece):
        """Check if dropped piece finished a long enough line"""

        # Row where piece is dropped
        row = self.column_bottom(column) - 1

        # Count pieces connected vertically
        streak = 1
        # Count only downwards (piece is always dropped on top)
        for i in range(row - 1, -1, -1):
            if self[i][column] == piece:
                streak += 1
            else:
                break
        if streak >= self._winning_pieces:
            return True

        # Count pieces connected horizontally
        streak = -1
        # Count left
        for i in range(column, -1, -1):
            if self[row][i] == piece or i == column:
                streak += 1
            else:
                break
        # Count right
        for i in range(column, self.width):
            if self[row][i] == piece or i == column:
                streak += 1
            else:
                break
        if streak >= self._winning_pieces:
            return True

        # Count pieces connected diagonally (bottom left - top right)
        streak = -1
        # Count towards bottom left
        for i, j in zip(range(column, -1, -1), range(row, -1, -1)):
            if self[j][i] == piece or (j == row and i == column):
                streak += 1
            else:
                break
        # Count towards top right
        for i, j in zip(range(column, self.width), range(row, self.height)):
            if self[j][i] == piece or (j == row and i == column):
                streak += 1
            else:
                break
        if streak >= self._winning_pieces:
            return True

        # Count pieces connected diagonally (bottom right - top left)
        streak = -1
        # Count towards bottom right
        for i, j in zip(range(column, self.width), range(row, -1, -1)):
            if self[j][i] == piece or (j == row and i == column):
                streak += 1
            else:
                break
        # Count towards top left
        for i, j in zip(range(column, -1, -1), range(row, self.height)):
            if self[j][i] == piece or (j == row and i == column):
                streak += 1
            else:
                break
        return streak >= self._winning_pieces

    def matrix_evaluation(self):
        """Uses an evaluation matrix - a 2D Gaussian mean distribution"""

        # Basically the more of my pieces near the center - the better
        # By playing towards the center I have better chances to find a combination of moves that forces a win
        # Less effective on huge boards with small number of winning pieces needed
        value = 0
        for i in range(self.height):
            for j in range(self.width):
                if self[i][j] == self._ai_piece:
                    # Add value if spot occupied by my piece
                    value += evaluation_matrix[i][j]
                elif self[i][j] == self._player_piece:
                    # Subtract value if spot occupied by enemy piece
                    value -= evaluation_matrix[i][j]

        return value

    def count_around_center(self, cells, center, piece):
        """Counts affiliated pieces and empty spaces in a line of cells

        :keyword cells List of cells
        :keyword center Index of center cell of which to count around
        :keyword piece Friendly piece
        """

        pieces, empty_spaces = 0, 0

        right = cells[center:]
        left = cells[:center]

        for i in range(len(left) - 1, -1, -1):
            if left[i] == 0:
                empty_spaces += 1
            elif left[i] == piece:
                pieces += 1
            else:
                break

        for i in range(len(right)):
            if right[i] == 0:
                empty_spaces += 1
            elif right[i] == piece:
                pieces += 1
            else:
                break

        return pieces, empty_spaces

    def column_evaluation(self):
        """Sums up potential of every column"""

        potential = 0
        for col in range(self.width):
            if self.column_not_full(col):
                # Collect cells around column's bottom (in all 4 axes)
                row = self.column_bottom(col)

                vertical = []
                for i in range(max(row - self._winning_pieces, 0), min(row + self._winning_pieces, self.height)):
                    vertical.append(self[i][col])

                horizontal = []
                for i in range(max(col - self._winning_pieces, 0), min(col + self._winning_pieces, self.width)):
                    horizontal.append(self[row][i])

                left_diagonal = []
                for i, j in zip(range(max(row - self._winning_pieces, 0), min(row + self._winning_pieces, self.height)),
                                range(max(col - self._winning_pieces, 0), min(col + self._winning_pieces, self.width))):
                    left_diagonal.append(self[i][j])

                right_diagonal = []
                for i, j in zip(range(max(row - self._winning_pieces, 0), min(row + self._winning_pieces, self.height)),
                                range(min(col + self._winning_pieces, self.width) - 1, max(col - self._winning_pieces, 0) - 1, -1)):
                    right_diagonal.append(self[i][j])

                axes = [(vertical, row), (horizontal, col), (left_diagonal, row), (right_diagonal, row)]

                def eval_axis(piece, axis, center, length, coefficient):
                    """If there is space for pieces to finish a line, return coefficient, else 0"""

                    pieces, gaps = self.count_around_center(axis, center, piece)
                    if pieces == length and gaps >= self._winning_pieces - length:
                        return coefficient
                    else:
                        return 0

                column_potential = 0
                length_coefficient = 2

                # Only interested if pieces make at least half a line
                for i in range(self._winning_pieces // 2, self._winning_pieces):
                    for axis, center in axes:
                        # My pieces have potential = good
                        column_potential += eval_axis(self._ai_piece, axis, center, i, length_coefficient)
                        # Enemy pieces have potential = bad
                        column_potential -= eval_axis(self._player_piece, axis, center, i, length_coefficient)

                    # Increase coefficient for the next (longer) sequence
                    length_coefficient = int(length_coefficient * 1.4) + 3

                potential += column_potential

        return potential

    def evaluate_board(self):
        """Evaluate board for AI player"""

        return self.column_evaluation() + self.matrix_evaluation() * 0.5

    def valid_columns(self):
        """Returns all non-full columns"""

        columns = []
        for i in range(self.width):
            if self.column_not_full(i):
                columns.append(i)
        return columns

    def minimax(self, depth, alpha: int = -math.inf, beta: int = math.inf, maximize: bool = True):
        """Minimax algorithm - evaluate all possible moves some time into the future and choose optimal"""

        # If game finished
        if self.game_over():
            # And we won -> maximal score
            if self.winner == self._ai_piece:
                return math.inf, None
            # And we lost -> minimal score
            elif self.winner == self._player_piece:
                return -math.inf, None
            # And it's a draw -> neutral score
            else:
                return 0, None

        # If bottom depth reached -> no more branching, just get heuristic value of this board
        if depth == 0:
            return self.evaluate_board(), None

        # Never empty (if empty -> game ended, which is caught in the first if statement)
        valid_columns = self.valid_columns()
        random.shuffle(valid_columns)

        # If maximizing
        if maximize:
            value = -math.inf
            column = random.choice(valid_columns)
            # Drop our piece in every column to see how it plays out
            for i in valid_columns:
                new_board = copy.deepcopy(self)
                new_board.drop_piece(i, new_board._ai_piece)
                # Branch out -> next is enemy's turn
                new_score, _ = new_board.minimax(depth - 1, alpha, beta, maximize=False)
                # Highest score -> our best move
                if new_score > value:
                    value = new_score
                    column = i
                if new_score == math.inf:
                    return value, i
                alpha = max(alpha, value)
                if alpha >= beta:
                    break  # Beta cutoff (will never go this route)
            return value, column
        # If minimizing
        else:
            value = math.inf
            column = random.choice(valid_columns)
            # Drop enemy piece in every column to see how it plays out
            for i in valid_columns:
                new_board = copy.deepcopy(self)
                new_board.drop_piece(i, new_board._player_piece)
                # Branch out -> next is our turn
                new_score, _ = new_board.minimax(depth - 1, alpha, beta, maximize=True)
                # Lowest score -> enemy's best move
                if new_score < value:
                    value = new_score
                    column = i
                beta = min(beta, value)
                if beta <= alpha:
                    break  # Alpha cutoff (will never go this route)
            return value, column

    def get_ai_move(self, player: int = 2, depth: int = 5):
        """Calculate a move to make as an AI opponent"""

        # If going first always choose middle (proven best option)
        board_empty = True
        for n in self[0]:
            if n != 0:
                board_empty = False
                break
        if board_empty:
            return int(self.width / 2)

        # Invert pieces if calculating best move for player 1
        if player == 1:
            self._ai_piece, self._player_piece = self._player_piece, self._ai_piece

        # Run minimax algorithm (here's a great explanation https://www.youtube.com/watch?v=l-hh51ncgDI)
        _, column = self.minimax(depth=depth)

        if player == 1:
            self._ai_piece, self._player_piece = self._player_piece, self._ai_piece

        return column

    def get_ai_move_mp(self, queue: Queue, player: int, depth: int):
        """Put result in queue (for multiprocessing)"""

        queue.put(self.get_ai_move(player, depth))
