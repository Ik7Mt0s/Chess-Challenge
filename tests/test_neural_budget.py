
import chess
import pytest

from chess_engine.engine import ChessEngine
from chess_engine.evaluation.base import PositionEvaluator
from chess_engine.evaluation.neural import HybridEvaluator


class CountingEvaluator(PositionEvaluator):
    def __init__(self, score: int):
        self.score = score
        self.calls = 0

    def evaluate(self, board: chess.Board) -> int:
        self.calls += 1
        return self.score


def test_neural_budget_limits_inferences():
    heuristic = CountingEvaluator(100)
    neural = CountingEvaluator(200)

    evaluator = HybridEvaluator(
        heuristic=heuristic,
        neural=neural,
        weight_neural=0.2,
        lazy_threshold=300,
        max_neural_inferences=2,
    )

    board_a = chess.Board()

    board_b = chess.Board()
    board_b.push_san("e4")

    board_c = chess.Board()
    board_c.push_san("d4")

    # Primeira posição: utiliza uma inferência.
    assert evaluator.evaluate(board_a) == 120

    # Repetir a mesma posição utiliza o cache.
    assert evaluator.evaluate(board_a) == 120

    # Segunda posição: utiliza a segunda inferência.
    assert evaluator.evaluate(board_b) == 120

    # Terceira posição: orçamento esgotado.
    assert evaluator.evaluate(board_c) == 100

    # Posições já armazenadas continuam disponíveis.
    assert evaluator.evaluate(board_a) == 120
    assert evaluator.evaluate(board_b) == 120

    assert neural.calls == 2
    assert heuristic.calls == 6

    stats = evaluator.inference_stats()

    assert stats["neural_inferences"] == 2
    assert stats["neural_cache_hits"] == 3
    assert stats["neural_skipped_budget"] == 1
    assert stats["neural_skipped_threshold"] == 0


def test_budget_resets_between_searches():
    neural = CountingEvaluator(200)

    evaluator = HybridEvaluator(
        heuristic=CountingEvaluator(100),
        neural=neural,
        weight_neural=0.2,
        max_neural_inferences=1,
    )

    board_a = chess.Board()

    board_b = chess.Board()
    board_b.push_san("e4")

    # Primeira busca.
    assert evaluator.evaluate(board_a) == 120
    assert evaluator.evaluate(board_a) == 120

    assert neural.calls == 1
    assert evaluator.inference_stats()["neural_inferences"] == 1

    # Nova busca: orçamento reiniciado, cache preservado.
    evaluator.begin_search()

    stats = evaluator.inference_stats()

    assert stats["neural_inferences"] == 0
    assert stats["neural_cache_hits"] == 0
    assert stats["neural_skipped_budget"] == 0

    # A posição antiga continua armazenada.
    assert evaluator.evaluate(board_a) == 120

    assert neural.calls == 1
    assert evaluator.inference_stats()["neural_cache_hits"] == 1

    # A posição nova utiliza o orçamento renovado.
    assert evaluator.evaluate(board_b) == 120

    assert neural.calls == 2
    assert evaluator.inference_stats()["neural_inferences"] == 1


def test_threshold_skips_neural():
    heuristic = CountingEvaluator(400)
    neural = CountingEvaluator(200)

    evaluator = HybridEvaluator(
        heuristic=heuristic,
        neural=neural,
        weight_neural=0.4,
        lazy_threshold=300,
        max_neural_inferences=2,
    )

    assert evaluator.evaluate(chess.Board()) == 400
    assert neural.calls == 0

    stats = evaluator.inference_stats()

    assert stats["neural_skipped_threshold"] == 1
    assert stats["neural_inferences"] == 0


def test_zero_weight_disables_neural():
    heuristic = CountingEvaluator(100)
    neural = CountingEvaluator(200)

    evaluator = HybridEvaluator(
        heuristic=heuristic,
        neural=neural,
        weight_neural=0.0,
    )

    assert evaluator.evaluate(chess.Board()) == 100
    assert neural.calls == 0
    assert evaluator.inference_stats()["neural_inferences"] == 0


def test_invalid_budget():
    with pytest.raises(ValueError):
        HybridEvaluator(
            heuristic=CountingEvaluator(100),
            neural=CountingEvaluator(200),
            max_neural_inferences=-1,
        )


def test_engine_reports_neural_metrics():
    evaluator = HybridEvaluator(
        heuristic=CountingEvaluator(100),
        neural=CountingEvaluator(200),
        weight_neural=0.4,
        max_neural_inferences=2,
    )

    engine = ChessEngine(
        evaluator=evaluator,
        max_depth=1,
    )

    board = chess.Board()

    result = engine.best_move(
        board,
        time_limit=5.0,
    )

    assert result.move in board.legal_moves

    assert "neural_inferences" in result.metrics
    assert "heuristic_evaluations" in result.metrics
    assert "neural_skipped_budget" in result.metrics
    assert "neural_cache_hits" in result.metrics

    assert result.metrics["neural_inferences"] <= 2


def test_cache_can_be_disabled():
    neural = CountingEvaluator(200)

    evaluator = HybridEvaluator(
        heuristic=CountingEvaluator(100),
        neural=neural,
        weight_neural=0.2,
        max_neural_inferences=2,
        neural_cache_size=0,
    )

    board = chess.Board()

    assert evaluator.evaluate(board) == 120
    assert evaluator.evaluate(board) == 120

    # Sem cache, a terceira chamada esgota o orçamento.
    assert evaluator.evaluate(board) == 100

    assert neural.calls == 2
    assert evaluator.inference_stats()["neural_cache_hits"] == 0


def test_clear_neural_cache():
    neural = CountingEvaluator(200)

    evaluator = HybridEvaluator(
        heuristic=CountingEvaluator(100),
        neural=neural,
        weight_neural=0.2,
        max_neural_inferences=2,
    )

    board = chess.Board()

    assert evaluator.evaluate(board) == 120
    assert evaluator.evaluate(board) == 120

    assert neural.calls == 1

    evaluator.clear_neural_cache()

    assert evaluator.evaluate(board) == 120
    assert neural.calls == 2


def test_cached_position_does_not_mutate_board():
    evaluator = HybridEvaluator(
        heuristic=CountingEvaluator(100),
        neural=CountingEvaluator(200),
        weight_neural=0.4,
    )

    board = chess.Board()
    board.push_san("e4")
    board.push_san("c5")

    original_fen = board.fen()
    original_stack = list(board.move_stack)

    evaluator.evaluate(board)
    evaluator.evaluate(board)

    assert board.fen() == original_fen
    assert board.move_stack == original_stack
