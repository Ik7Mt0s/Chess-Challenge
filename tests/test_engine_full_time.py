
import unittest
from unittest.mock import patch

import chess

from chess_engine.engine import ChessEngine
from chess_engine.evaluation.heuristic import HeuristicEvaluator
from chess_engine.utils.time_manager import SearchTimeout


class TestEngineFullTime(unittest.TestCase):

    def setUp(self):
        self.board = chess.Board()
        self.evaluator = HeuristicEvaluator()

    def test_fixed_depth_stops_at_configured_limit(self):
        engine = ChessEngine(
            evaluator=self.evaluator,
            max_depth=2,
            use_full_time=False,
            use_transposition_table=False,
        )

        depths = []

        def fake_negamax(*args, **kwargs):
            depths.append(kwargs["depth"])
            return 0

        with patch(
            "chess_engine.engine.negamax",
            side_effect=fake_negamax,
        ):
            result = engine.best_move(
                self.board,
                time_limit=5.0,
            )

        self.assertEqual(result.depth, 2)
        self.assertEqual(result.status, "completed")
        self.assertEqual(set(depths), {0, 1})

    def test_full_time_continues_beyond_max_depth(self):
        engine = ChessEngine(
            evaluator=self.evaluator,
            max_depth=2,
            use_full_time=True,
            use_transposition_table=False,
        )

        depths = []

        def fake_negamax(*args, **kwargs):
            depth = kwargs["depth"]
            depths.append(depth)

            # Simula o tempo acabando ao tentar
            # iniciar a terceira profundidade.
            if depth >= 2:
                raise SearchTimeout(
                    "Tempo simulado esgotado."
                )

            return 0

        with patch(
            "chess_engine.engine.negamax",
            side_effect=fake_negamax,
        ):
            result = engine.best_move(
                self.board,
                time_limit=5.0,
            )

        self.assertEqual(result.depth, 2)
        self.assertEqual(result.status, "timeout")
        self.assertIn(2, depths)

    def test_timeout_keeps_last_completed_move(self):
        engine = ChessEngine(
            evaluator=self.evaluator,
            max_depth=1,
            use_full_time=True,
            use_transposition_table=False,
        )

        original_fen = self.board.fen()
        first_move = list(self.board.legal_moves)[0]

        def fake_negamax(*args, **kwargs):
            depth = kwargs["depth"]
            board = kwargs["board"]

            if depth >= 1:
                raise SearchTimeout(
                    "Tempo simulado esgotado."
                )

            # Na primeira iteração, atribui maior
            # pontuação ao primeiro movimento.
            return (
                -100
                if board.move_stack[-1] == first_move
                else 0
            )

        with patch(
            "chess_engine.engine.negamax",
            side_effect=fake_negamax,
        ):
            result = engine.best_move(
                self.board,
                time_limit=5.0,
            )

        self.assertEqual(result.depth, 1)
        self.assertEqual(result.move, first_move)
        self.assertEqual(result.score, 100)
        self.assertEqual(result.status, "timeout")

        # A busca não pode alterar a posição original.
        self.assertEqual(
            self.board.fen(),
            original_fen,
        )
        self.assertEqual(
            len(self.board.move_stack),
            0,
        )


if __name__ == "__main__":
    unittest.main()
