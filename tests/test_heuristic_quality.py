
import unittest

import chess

from chess_engine.evaluation.heuristic import (
    HeuristicEvaluator,
    OUTPOST_CHALLENGE_MASKS,
)


class TestHeuristicQuality(unittest.TestCase):

    def setUp(self):
        self.evaluator = HeuristicEvaluator()

    @staticmethod
    def empty_board():
        board = chess.Board(None)

        board.set_piece_at(
            chess.E1,
            chess.Piece(chess.KING, chess.WHITE),
        )

        board.set_piece_at(
            chess.E8,
            chess.Piece(chess.KING, chess.BLACK),
        )

        return board

    def test_initial_position_is_equal(self):
        self.assertEqual(
            self.evaluator.evaluate(chess.Board()),
            0,
        )

    def test_symmetry(self):
        positions = [
            chess.Board(),
            chess.Board(
                "r3k2r/pp3ppp/2n1p3/3pP3/"
                "3P4/2N5/PP3PPP/R3K2R "
                "w KQkq - 0 1"
            ),
            chess.Board(
                "8/3k4/8/3P4/4K3/8/8/8 "
                "w - - 0 1"
            ),
        ]

        for board in positions:
            with self.subTest(fen=board.fen()):
                score = self.evaluator.evaluate(board)
                mirror_score = self.evaluator.evaluate(
                    board.mirror()
                )

                self.assertEqual(
                    score,
                    -mirror_score,
                )

    def test_more_material_is_better(self):
        board = self.empty_board()

        board.set_piece_at(
            chess.D1,
            chess.Piece(chess.QUEEN, chess.WHITE),
        )

        self.assertGreater(
            self.evaluator.evaluate(board),
            700,
        )

    def test_insufficient_material_is_draw(self):
        board = chess.Board(
            "4k3/8/8/8/8/8/8/4K3 "
            "w - - 0 1"
        )

        self.assertEqual(
            self.evaluator.evaluate(board),
            0,
        )

    def test_supported_knight_outpost(self):
        board = self.empty_board()

        board.set_piece_at(
            chess.D5,
            chess.Piece(chess.KNIGHT, chess.WHITE),
        )

        board.set_piece_at(
            chess.C4,
            chess.Piece(chess.PAWN, chess.WHITE),
        )

        result = self.evaluator._knight_outpost(
            board,
            chess.WHITE,
            chess.D5,
            board.pieces_mask(
                chess.PAWN,
                chess.WHITE,
            ),
        )

        self.assertEqual(
            result,
            self.evaluator.KNIGHT_OUTPOST_BONUS,
        )

    def test_enemy_pawn_challenges_outpost(self):
        board = self.empty_board()

        board.set_piece_at(
            chess.D5,
            chess.Piece(chess.KNIGHT, chess.WHITE),
        )

        board.set_piece_at(
            chess.C4,
            chess.Piece(chess.PAWN, chess.WHITE),
        )

        board.set_piece_at(
            chess.E7,
            chess.Piece(chess.PAWN, chess.BLACK),
        )

        self.assertTrue(
            OUTPOST_CHALLENGE_MASKS[
                chess.WHITE
            ][chess.D5]
            & chess.BB_SQUARES[chess.E7]
        )

        result = self.evaluator._knight_outpost(
            board,
            chess.WHITE,
            chess.D5,
            board.pieces_mask(
                chess.PAWN,
                chess.WHITE,
            ),
        )

        self.assertEqual(result, 0)

    def test_blocked_passed_pawn_loses_value(self):
        board = self.empty_board()

        board.set_piece_at(
            chess.D5,
            chess.Piece(chess.PAWN, chess.WHITE),
        )

        free_score = self.evaluator._pawn_structure(
            board,
            chess.WHITE,
            phase=0,
        )

        board.set_piece_at(
            chess.D6,
            chess.Piece(chess.ROOK, chess.BLACK),
        )

        blocked_score = self.evaluator._pawn_structure(
            board,
            chess.WHITE,
            phase=0,
        )

        self.assertGreater(
            free_score,
            blocked_score,
        )

    def test_hanging_piece_is_penalized(self):
        board = self.empty_board()

        board.set_piece_at(
            chess.D4,
            chess.Piece(chess.BISHOP, chess.WHITE),
        )

        safe = self.evaluator._piece_safety(
            board,
            chess.WHITE,
            chess.D4,
            chess.BISHOP,
            0,
        )

        board.set_piece_at(
            chess.D8,
            chess.Piece(chess.ROOK, chess.BLACK),
        )

        attacked = self.evaluator._piece_safety(
            board,
            chess.WHITE,
            chess.D4,
            chess.BISHOP,
            0,
        )

        self.assertEqual(safe, 0)
        self.assertLess(attacked, safe)

    def test_board_is_not_modified(self):
        board = chess.Board()

        original_fen = board.fen()
        original_history = list(board.move_stack)

        self.evaluator.evaluate(board)

        self.assertEqual(
            board.fen(),
            original_fen,
        )

        self.assertEqual(
            board.move_stack,
            original_history,
        )

    def test_deterministic_evaluation(self):
        board = chess.Board(
            "r3k2r/pp3ppp/2n1p3/3pP3/"
            "3P4/2N5/PP3PPP/R3K2R "
            "w KQkq - 0 1"
        )

        results = {
            self.evaluator.evaluate(board)
            for _ in range(10)
        }

        self.assertEqual(len(results), 1)


if __name__ == "__main__":
    unittest.main()
