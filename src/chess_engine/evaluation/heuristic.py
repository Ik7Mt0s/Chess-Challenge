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

    CENTER_BONUS = {
        chess.KNIGHT: 8,
        chess.BISHOP: 4,
    }

    PAWN_ADVANCE_BONUS = 5

    def evaluate(self, board: chess.Board) -> int:
        """
        Avalia a posição do ponto de vista das brancas.

        Pontuação positiva: vantagem das brancas.
        Pontuação negativa: vantagem das pretas.
        """
        score = 0

        for piece_type, value in self.PIECE_VALUES.items():
            for color in (chess.WHITE, chess.BLACK):
                sign = 1 if color == chess.WHITE else -1

                for square in board.pieces(piece_type, color):
                    score += sign * value

                    score += sign * self._positional_score(
                        piece_type,
                        square,
                        color,
                    )

        return score

    def _positional_score(
        self,
        piece_type: chess.PieceType,
        square: chess.Square,
        color: chess.Color,
    ) -> int:
        score = 0

        file = chess.square_file(square)
        rank = chess.square_rank(square)

        if piece_type in self.CENTER_BONUS:
            distance = (
                min(abs(file - 3), abs(file - 4))
                + min(abs(rank - 3), abs(rank - 4))
            )

            centrality = 6 - distance

            score += (
                centrality * self.CENTER_BONUS[piece_type]
            )

        if piece_type == chess.PAWN:
            advancement = (
                rank - 1
                if color == chess.WHITE
                else 6 - rank
            )

            score += max(0, advancement) * self.PAWN_ADVANCE_BONUS

        return score