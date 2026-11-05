
import unittest

import chess

from chess_engine.evaluation.base import PositionEvaluator
from chess_engine.evaluation.heuristic import HeuristicEvaluator
from chess_engine.evaluation.king_safety import (
    KingSafetyHeuristicEvaluator,
)
from chess_engine.evaluation.neural import HybridEvaluator
from chess_engine.search.metrics import SearchMetrics
from chess_engine.search.quiescence import (
    MATE_SCORE,
    quiescence,
)


class DummyTimer:
    def check(self):
        return None


class ZeroEvaluator(PositionEvaluator):
    def evaluate(self, board):
        return 0


class FixedNeuralEvaluator(PositionEvaluator):
    def __init__(self):
        self.calls = 0

    def evaluate(self, board):
        self.calls += 1
        return 100


class TestQuiescence(unittest.TestCase):
    def test_initial_position_is_balanced(self):
        board = chess.Board()

        result = quiescence(
            board=board,
            alpha=-1_000_000,
            beta=1_000_000,
            evaluator=ZeroEvaluator(),
            timer=DummyTimer(),
            max_depth=0,
        )

        self.assertEqual(result, 0)

    def test_checkmate_is_recognized(self):
        board = chess.Board()
        board.push_san("f3")
        board.push_san("e5")
        board.push_san("g4")
        board.push_san("Qh4#")

        result = quiescence(
            board=board,
            alpha=-1_000_000,
            beta=1_000_000,
            evaluator=ZeroEvaluator(),
            timer=DummyTimer(),
            max_depth=0,
        )

        self.assertEqual(result, -MATE_SCORE)

    def test_in_check_respects_extension_limit(self):
        board = chess.Board(
            "4k3/8/8/8/8/8/4r3/4K3 w - - 0 1"
        )

        self.assertTrue(board.is_check())

        before_fen = board.fen()
        before_stack = list(board.move_stack)

        metrics = SearchMetrics()

        result = quiescence(
            board=board,
            alpha=-1_000_000,
            beta=1_000_000,
            evaluator=ZeroEvaluator(),
            timer=DummyTimer(),
            max_depth=0,
            max_check_extensions=0,
            metrics=metrics,
        )

        self.assertIsInstance(result, int)
        self.assertEqual(board.fen(), before_fen)
        self.assertEqual(
            board.move_stack,
            before_stack,
        )
        self.assertEqual(
            metrics.quiescence_nodes,
            1,
        )

    def test_normal_search_does_not_modify_board(self):
        board = chess.Board()
        board.push_san("e4")
        board.push_san("d5")

        original_fen = board.fen()
        original_stack = list(board.move_stack)

        quiescence(
            board=board,
            alpha=-1_000_000,
            beta=1_000_000,
            evaluator=ZeroEvaluator(),
            timer=DummyTimer(),
            max_depth=3,
        )

        self.assertEqual(
            board.fen(),
            original_fen,
        )
        self.assertEqual(
            board.move_stack,
            original_stack,
        )


class TestKingSafety(unittest.TestCase):
    def setUp(self):
        self.original = HeuristicEvaluator()
        self.improved = KingSafetyHeuristicEvaluator()

    def test_initial_position_remains_balanced(self):
        board = chess.Board()

        self.assertEqual(
            self.improved.evaluate(board),
            0,
        )

    def test_early_g_pawn_advance_is_penalized(self):
        board = chess.Board()

        board.push_san("e4")
        board.push_san("g5")

        original_score = self.original.evaluate(board)
        improved_score = self.improved.evaluate(board)

        self.assertGreater(
            improved_score,
            original_score,
        )

    def test_evaluation_does_not_modify_position(self):
        board = chess.Board()

        board.push_san("d4")
        board.push_san("Nf6")
        board.push_san("Bf4")
        board.push_san("h6")

        fen = board.fen()
        stack = list(board.move_stack)

        self.improved.evaluate(board)

        self.assertEqual(board.fen(), fen)
        self.assertEqual(board.move_stack, stack)

    def test_repeated_evaluation_is_deterministic(self):
        board = chess.Board()

        board.push_san("e4")
        board.push_san("c5")

        first = self.improved.evaluate(board)
        second = self.improved.evaluate(board)

        self.assertEqual(first, second)


class TestNeuralCache(unittest.TestCase):
    def test_repeated_position_reuses_inference(self):
        neural = FixedNeuralEvaluator()

        hybrid = HybridEvaluator(
            heuristic=ZeroEvaluator(),
            neural=neural,
            weight_neural=0.4,
            max_neural_inferences=1,
            neural_cache_size=32,
        )

        board = chess.Board()

        first = hybrid.evaluate(board)
        second = hybrid.evaluate(board)

        self.assertEqual(first, 40)
        self.assertEqual(second, 40)
        self.assertEqual(neural.calls, 1)

        stats = hybrid.inference_stats()

        self.assertEqual(
            stats["neural_inferences"],
            1,
        )
        self.assertEqual(
            stats["neural_cache_hits"],
            1,
        )

    def test_budget_is_respected_for_new_positions(self):
        neural = FixedNeuralEvaluator()

        hybrid = HybridEvaluator(
            heuristic=ZeroEvaluator(),
            neural=neural,
            weight_neural=0.4,
            max_neural_inferences=1,
        )

        first_board = chess.Board()
        second_board = chess.Board()
        second_board.push_san("e4")

        first = hybrid.evaluate(first_board)
        second = hybrid.evaluate(second_board)

        self.assertEqual(first, 40)
        self.assertEqual(second, 0)
        self.assertEqual(neural.calls, 1)
        self.assertEqual(
            hybrid.inference_stats()[
                "neural_skipped_budget"
            ],
            1,
        )

    def test_begin_search_resets_budget_not_cache(self):
        neural = FixedNeuralEvaluator()

        hybrid = HybridEvaluator(
            heuristic=ZeroEvaluator(),
            neural=neural,
            weight_neural=0.4,
            max_neural_inferences=1,
        )

        board = chess.Board()

        hybrid.evaluate(board)
        hybrid.begin_search()
        hybrid.evaluate(board)

        self.assertEqual(neural.calls, 1)
        self.assertEqual(
            hybrid.inference_stats()[
                "neural_cache_hits"
            ],
            1,
        )


if __name__ == "__main__":
    unittest.main()
