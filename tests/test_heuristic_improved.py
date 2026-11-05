
import unittest

import chess

from chess_engine.evaluation.heuristic import HeuristicEvaluator


class TestHeuristicImproved(unittest.TestCase):

    def setUp(self):
        self.evaluator = HeuristicEvaluator()

    def empty_board(self):
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

    def test_initial_position_is_balanced(self):
        self.assertEqual(
            self.evaluator.evaluate(chess.Board()),
            0,
        )

    def test_mirror_reverses_evaluation(self):
        boards = [
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

        for board in boards:
            with self.subTest(fen=board.fen()):
                score = self.evaluator.evaluate(board)
                mirrored = self.evaluator.evaluate(
                    board.mirror()
                )

                self.assertEqual(score, -mirrored)

    def test_material_advantage(self):
        board = self.empty_board()
        board.set_piece_at(
            chess.D1,
            chess.Piece(chess.QUEEN, chess.WHITE),
        )

        self.assertGreater(
            self.evaluator.evaluate(board),
            700,
        )

    def test_rook_open_file_bonus(self):
        board = self.empty_board()

        board.set_piece_at(
            chess.A1,
            chess.Piece(chess.ROOK, chess.WHITE),
        )
        board.set_piece_at(
            chess.H2,
            chess.Piece(chess.PAWN, chess.WHITE),
        )

        score_open = self.evaluator._piece_activity_score(
            board, chess.WHITE, 0
        )

        board.remove_piece_at(chess.H2)
        board.set_piece_at(
            chess.A2,
            chess.Piece(chess.PAWN, chess.WHITE),
        )

        score_closed = self.evaluator._piece_activity_score(
            board, chess.WHITE, 0
        )

        self.assertGreater(score_open, score_closed)

    def test_blocked_passed_pawn(self):
        board = self.empty_board()

        board.set_piece_at(
            chess.D5,
            chess.Piece(chess.PAWN, chess.WHITE),
        )

        free_score = self.evaluator._pawn_structure(
            board, chess.WHITE, 0
        )

        board.set_piece_at(
            chess.D6,
            chess.Piece(chess.ROOK, chess.BLACK),
        )

        blocked_score = self.evaluator._pawn_structure(
            board, chess.WHITE, 0
        )

        self.assertGreater(free_score, blocked_score)

    def test_undefended_attacked_piece_is_penalized(self):
        board = self.empty_board()

        board.set_piece_at(
            chess.D4,
            chess.Piece(chess.BISHOP, chess.WHITE),
        )

        safe_score = self.evaluator._piece_safety(
            board,
            chess.WHITE,
            chess.D4,
            chess.BISHOP,
            enemy_pawn_attacks=0,
        )

        board.set_piece_at(
            chess.D8,
            chess.Piece(chess.ROOK, chess.BLACK),
        )

        threatened_score = self.evaluator._piece_safety(
            board,
            chess.WHITE,
            chess.D4,
            chess.BISHOP,
            enemy_pawn_attacks=0,
        )

        self.assertEqual(safe_score, 0)
        self.assertLess(threatened_score, safe_score)

    def test_knight_outpost_requires_pawn_support(self):
        board = self.empty_board()

        board.set_piece_at(
            chess.D5,
            chess.Piece(chess.KNIGHT, chess.WHITE),
        )

        no_support = self.evaluator._knight_outpost(
            board,
            chess.WHITE,
            chess.D5,
            board.pieces_mask(chess.PAWN, chess.WHITE),
        )

        board.set_piece_at(
            chess.C4,
            chess.Piece(chess.PAWN, chess.WHITE),
        )

        with_support = self.evaluator._knight_outpost(
            board,
            chess.WHITE,
            chess.D5,
            board.pieces_mask(chess.PAWN, chess.WHITE),
        )

        self.assertEqual(no_support, 0)
        self.assertGreater(with_support, no_support)

    def test_enemy_pawn_can_challenge_outpost(self):
        board = self.empty_board()

        board.set_piece_at(
            chess.D5,
            chess.Piece(chess.KNIGHT, chess.WHITE),
        )
        board.set_piece_at(
            chess.C4,
            chess.Piece(chess.PAWN, chess.WHITE),
        )

        supported = self.evaluator._knight_outpost(
            board,
            chess.WHITE,
            chess.D5,
            board.pieces_mask(chess.PAWN, chess.WHITE),
        )

        board.set_piece_at(
            chess.E7,
            chess.Piece(chess.PAWN, chess.BLACK),
        )

        challenged = self.evaluator._knight_outpost(
            board,
            chess.WHITE,
            chess.D5,
            board.pieces_mask(chess.PAWN, chess.WHITE),
        )

        self.assertGreater(supported, 0)
        self.assertEqual(challenged, 0)

    def test_evaluation_does_not_modify_board(self):
        board = chess.Board()

        original_fen = board.fen()
        original_stack = list(board.move_stack)

        self.evaluator.evaluate(board)

        self.assertEqual(board.fen(), original_fen)
        self.assertEqual(board.move_stack, original_stack)

    def test_evaluation_is_deterministic(self):
        board = chess.Board(
            "r3k2r/pp3ppp/2n1p3/3pP3/"
            "3P4/2N5/PP3PPP/R3K2R "
            "w KQkq - 0 1"
        )

        scores = [
            self.evaluator.evaluate(board)
            for _ in range(5)
        ]

        self.assertEqual(len(set(scores)), 1)


if __name__ == "__main__":
    unittest.main()
