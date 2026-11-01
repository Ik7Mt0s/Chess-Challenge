
import chess
import pytest

from chess_engine.engine import ChessEngine
from chess_engine.evaluation.heuristic import HeuristicEvaluator
from chess_engine.search.negamax import INFINITY, negamax
from chess_engine.search.quiescence import quiescence
from chess_engine.utils.time_manager import TimeManager


@pytest.mark.parametrize("score_quiet_checks", [True, False])
def test_engine_completes_both_strategies(score_quiet_checks):
    board = chess.Board()
    original_fen = board.fen()
    original_history = list(board.move_stack)

    engine = ChessEngine(
        max_depth=2,
        score_quiet_checks=score_quiet_checks,
    )

    result = engine.best_move(board, time_limit=10.0)

    assert result.move in board.legal_moves
    assert result.depth == 2
    assert result.status == "completed"
    assert isinstance(result.score, int)
    assert board.fen() == original_fen
    assert board.move_stack == original_history


def test_default_strategy_is_original():
    engine = ChessEngine()

    assert engine.score_quiet_checks is True


@pytest.mark.parametrize("score_quiet_checks", [True, False])
def test_negamax_accepts_strategy(score_quiet_checks):
    board = chess.Board()
    original_fen = board.fen()

    result = negamax(
        board=board,
        depth=2,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=HeuristicEvaluator(),
        timer=TimeManager(10.0),
        score_quiet_checks=score_quiet_checks,
    )

    assert isinstance(result, int)
    assert board.fen() == original_fen
    assert len(board.move_stack) == 0


@pytest.mark.parametrize("score_quiet_checks", [True, False])
def test_quiescence_accepts_strategy(score_quiet_checks):
    board = chess.Board()
    original_fen = board.fen()

    result = quiescence(
        board=board,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=HeuristicEvaluator(),
        timer=TimeManager(10.0),
        score_quiet_checks=score_quiet_checks,
    )

    assert isinstance(result, int)
    assert board.fen() == original_fen
    assert len(board.move_stack) == 0


def test_strategy_is_forwarded_to_negamax(monkeypatch):
    import chess_engine.engine as engine_module

    received = []
    original = engine_module.negamax

    def tracked_negamax(*args, **kwargs):
        received.append(kwargs["score_quiet_checks"])
        return original(*args, **kwargs)

    monkeypatch.setattr(
        engine_module,
        "negamax",
        tracked_negamax,
    )

    engine = ChessEngine(
        max_depth=1,
        score_quiet_checks=False,
    )

    engine.best_move(chess.Board(), time_limit=10.0)

    assert received
    assert all(value is False for value in received)


def test_strategy_is_forwarded_to_quiescence(monkeypatch):
    import chess_engine.search.negamax as negamax_module

    received = []
    original = negamax_module.quiescence

    def tracked_quiescence(*args, **kwargs):
        received.append(kwargs["score_quiet_checks"])
        return original(*args, **kwargs)

    monkeypatch.setattr(
        negamax_module,
        "quiescence",
        tracked_quiescence,
    )

    negamax(
        board=chess.Board(),
        depth=0,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=HeuristicEvaluator(),
        timer=TimeManager(10.0),
        score_quiet_checks=False,
    )

    assert received == [False]


def test_quiescence_recursion_preserves_strategy(monkeypatch):
    import chess_engine.search.quiescence as quiescence_module

    received = []
    original_order_moves = quiescence_module.order_moves

    def tracked_order_moves(*args, **kwargs):
        received.append(kwargs["score_quiet_checks"])
        return original_order_moves(*args, **kwargs)

    monkeypatch.setattr(
        quiescence_module,
        "order_moves",
        tracked_order_moves,
    )

    board = chess.Board(
        "4k3/8/8/8/8/8/4R3/K7 b - - 0 1"
    )

    assert board.is_valid()
    assert board.is_check()

    quiescence(
        board=board,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=HeuristicEvaluator(),
        timer=TimeManager(10.0),
        max_depth=1,
        score_quiet_checks=False,
    )

    assert received
    assert all(value is False for value in received)
