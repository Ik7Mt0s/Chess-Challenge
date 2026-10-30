
import chess
import pytest

from chess_engine.engine import ChessEngine
from chess_engine.evaluation.heuristic import HeuristicEvaluator
from chess_engine.search.metrics import SearchMetrics
from chess_engine.search.negamax import INFINITY, negamax
from chess_engine.search.quiescence import quiescence
from chess_engine.utils.time_manager import TimeManager


def test_initial_metrics():
    metrics = SearchMetrics()

    assert metrics.negamax_nodes == 0
    assert metrics.quiescence_nodes == 0
    assert metrics.alpha_beta_cutoffs == 0
    assert metrics.total_nodes == 0


def test_negamax_counts_nodes():
    board = chess.Board()
    metrics = SearchMetrics()

    negamax(
        board=board,
        depth=1,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=HeuristicEvaluator(),
        timer=TimeManager(10.0),
        metrics=metrics,
    )

    assert metrics.negamax_nodes > 0
    assert metrics.quiescence_nodes > 0
    assert metrics.total_nodes == (
        metrics.negamax_nodes
        + metrics.quiescence_nodes
    )


def test_quiescence_counts_nodes():
    board = chess.Board()
    metrics = SearchMetrics()

    quiescence(
        board=board,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=HeuristicEvaluator(),
        timer=TimeManager(10.0),
        metrics=metrics,
    )

    assert metrics.quiescence_nodes >= 1
    assert metrics.negamax_nodes == 0


def test_metrics_do_not_change_evaluation():
    board = chess.Board()
    evaluator = HeuristicEvaluator()
    original_fen = board.fen()

    score_without_metrics = negamax(
        board=board,
        depth=1,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=evaluator,
        timer=TimeManager(10.0),
    )

    metrics = SearchMetrics()

    score_with_metrics = negamax(
        board=board,
        depth=1,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=evaluator,
        timer=TimeManager(10.0),
        metrics=metrics,
    )

    assert score_with_metrics == score_without_metrics
    assert board.fen() == original_fen
    assert len(board.move_stack) == 0


@pytest.mark.parametrize("use_cache", [False, True])
def test_engine_returns_metrics(use_cache):
    board = chess.Board()
    original_fen = board.fen()

    engine = ChessEngine(
        max_depth=1,
        use_transposition_table=use_cache,
    )

    result = engine.best_move(
        board,
        time_limit=10.0,
    )

    assert result.move in board.legal_moves
    assert result.depth == 1
    assert result.status == "completed"
    assert result.metrics["total_nodes"] > 0
    assert result.metrics["negamax_nodes"] > 0
    assert result.metrics["quiescence_nodes"] > 0
    assert result.cache["hits"] >= 0
    assert board.fen() == original_fen
    assert len(board.move_stack) == 0

    if not use_cache:
        assert result.cache["entries"] == 0
        assert result.cache["hits"] == 0


def test_forced_move_status():
    # Rei preto em h8 sob xeque da torre branca em h1.
    # A única saída legal é Kh8-g8.
    board = chess.Board(
        "7k/8/5K2/8/8/8/8/7R b - - 0 1"
    )

    assert board.is_valid()
    assert board.is_check()
    assert not board.is_game_over(claim_draw=True)
    assert board.legal_moves.count() == 1

    engine = ChessEngine(max_depth=3)

    result = engine.best_move(
        board,
        time_limit=1.0,
    )

    assert result.status == "forced"
    assert result.depth == 0
    assert result.move == chess.Move.from_uci("h8g8")
    assert result.metrics["total_nodes"] == 0


def test_fallback_when_time_is_exhausted():
    board = chess.Board()
    original_fen = board.fen()

    engine = ChessEngine(max_depth=3)

    # O TimeManager exige tempo positivo.
    # Esse intervalo é pequeno o suficiente para
    # expirar antes de concluir a primeira iteração.
    result = engine.best_move(
        board,
        time_limit=1e-9,
    )

    assert result.status == "fallback"
    assert result.depth == 0
    assert result.move in board.legal_moves
    assert board.fen() == original_fen
    assert len(board.move_stack) == 0


def test_cache_stats_are_per_search():
    board = chess.Board()

    engine = ChessEngine(
        max_depth=1,
        use_transposition_table=True,
    )

    first = engine.best_move(
        board,
        time_limit=10.0,
    )

    second = engine.best_move(
        board,
        time_limit=10.0,
    )

    assert first.cache["hits"] >= 0
    assert second.cache["hits"] >= 0
    assert second.cache["misses"] >= 0

    cumulative = engine.cache_stats()

    assert cumulative["hits"] == (
        first.cache["hits"]
        + second.cache["hits"]
    )


def test_time_manager_rejects_non_positive_limit():
    with pytest.raises(ValueError):
        TimeManager(0.0)

    with pytest.raises(ValueError):
        TimeManager(-1.0)
