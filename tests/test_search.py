import chess

from chess_engine.evaluation.heuristic import HeuristicEvaluator
from chess_engine.search.negamax import (
    INFINITY,
    negamax,
)
from chess_engine.utils.time_manager import TimeManager


def test_initial_position_is_balanced():
    board = chess.Board()
    evaluator = HeuristicEvaluator()
    timer = TimeManager(5.0)

    score = negamax(
        board,
        depth=0,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=evaluator,
        timer=timer,
    )

    assert score == 0


def test_search_does_not_modify_board():
    board = chess.Board()
    original_fen = board.fen()
    evaluator = HeuristicEvaluator()
    timer = TimeManager(5.0)

    negamax(
        board,
        depth=2,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=evaluator,
        timer=timer,
    )

    assert board.fen() == original_fen
    assert len(board.move_stack) == 0


def test_checkmate_has_negative_score():
    board = chess.Board()

    for move in ["f3", "e5", "g4", "Qh4#"]:
        board.push_san(move)

    score = negamax(
        board,
        depth=2,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=HeuristicEvaluator(),
        timer=TimeManager(5.0),
    )

    assert score < -90_000


def test_stalemate_is_draw():
    board = chess.Board(
        "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
    )

    score = negamax(
        board,
        depth=2,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=HeuristicEvaluator(),
        timer=TimeManager(5.0),
    )

    assert board.is_stalemate()
    assert score == 0