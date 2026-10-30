import chess

from chess_engine.evaluation.base import PositionEvaluator


class HeuristicEvaluator(PositionEvaluator):

    PIECE_VALUES = {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 0,
    }

    def evaluate(self, board: chess.Board) -> int:
        score = 0

        for piece_type, value in self.PIECE_VALUES.items():
            white_count = len(board.pieces(piece_type, chess.WHITE))
            black_count = len(board.pieces(piece_type, chess.BLACK))

            score += (white_count - black_count) * value

        return score