
import chess

from chess_engine.engine import ChessEngine
from chess_engine.evaluation.heuristic import HeuristicEvaluator
from chess_engine.search.move_ordering import (
    MoveOrderingHeuristics,
    order_moves,
)
from chess_engine.search.negamax import (
    INFINITY,
    negamax,
)
from chess_engine.utils.time_manager import TimeManager


def test_killer_move_is_prioritized():
    board = chess.Board()
    heuristics = MoveOrderingHeuristics()

    killer = chess.Move.from_uci("a2a3")

    heuristics.record_cutoff(
        board=board,
        move=killer,
        ply=1,
        depth=3,
    )

    ordered = order_moves(
        board,
        ply=1,
        heuristics=heuristics,
    )

    assert ordered[0] == killer


def test_two_killer_moves_per_ply():
    board = chess.Board()
    heuristics = MoveOrderingHeuristics()

    first = chess.Move.from_uci("a2a3")
    second = chess.Move.from_uci("b2b3")
    third = chess.Move.from_uci("c2c3")

    for move in (first, second, third):
        heuristics.record_cutoff(
            board=board,
            move=move,
            ply=2,
            depth=3,
        )

    assert heuristics.killers[2] == [
        third,
        second,
    ]

    assert heuristics.is_killer(first, 2) == 0
    assert heuristics.is_killer(second, 2) == 2
    assert heuristics.is_killer(third, 2) == 1


def test_killer_moves_are_separated_by_ply():
    board = chess.Board()
    heuristics = MoveOrderingHeuristics()

    move = chess.Move.from_uci("a2a3")

    heuristics.record_cutoff(
        board,
        move,
        ply=2,
        depth=3,
    )

    assert heuristics.is_killer(move, 2) == 1
    assert heuristics.is_killer(move, 3) == 0


def test_history_is_separated_by_color():
    board = chess.Board()
    heuristics = MoveOrderingHeuristics()

    move = chess.Move.from_uci("a2a3")

    heuristics.record_cutoff(
        board,
        move,
        ply=1,
        depth=3,
    )

    assert (
        heuristics.history_score(chess.WHITE, move)
        == 9
    )

    assert (
        heuristics.history_score(chess.BLACK, move)
        == 0
    )


def test_capture_is_not_recorded_as_killer():
    board = chess.Board()
    board.push_san("e4")
    board.push_san("d5")

    capture = chess.Move.from_uci("e4d5")
    heuristics = MoveOrderingHeuristics()

    assert board.is_capture(capture)

    heuristics.record_cutoff(
        board,
        capture,
        ply=2,
        depth=3,
    )

    assert heuristics.is_killer(capture, 2) == 0
    assert (
        heuristics.history_score(board.turn, capture)
        == 0
    )


def test_capture_has_priority_over_killer():
    board = chess.Board()
    board.push_san("e4")
    board.push_san("d5")

    capture = chess.Move.from_uci("e4d5")
    killer = chess.Move.from_uci("g1f3")

    heuristics = MoveOrderingHeuristics()
    heuristics.record_cutoff(
        board,
        killer,
        ply=1,
        depth=3,
    )

    ordered = order_moves(
        board,
        ply=1,
        heuristics=heuristics,
    )

    assert ordered.index(capture) < ordered.index(killer)


def test_tt_move_has_highest_priority():
    board = chess.Board()
    tt_move = chess.Move.from_uci("a2a3")

    ordered = order_moves(
        board,
        tt_move=tt_move,
    )

    assert ordered[0] == tt_move


def test_reset_clears_heuristics():
    board = chess.Board()
    heuristics = MoveOrderingHeuristics()

    move = chess.Move.from_uci("a2a3")

    heuristics.record_cutoff(
        board,
        move,
        ply=1,
        depth=3,
    )

    heuristics.reset()

    assert heuristics.killers == {}
    assert heuristics.history == {}


def test_negamax_accepts_advanced_ordering():
    board = chess.Board()
    original_fen = board.fen()

    heuristics = MoveOrderingHeuristics()

    score = negamax(
        board=board,
        depth=2,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=HeuristicEvaluator(),
        timer=TimeManager(10.0),
        ordering_heuristics=heuristics,
    )

    assert isinstance(score, int)
    assert board.fen() == original_fen
    assert len(board.move_stack) == 0


def test_engine_with_advanced_ordering():
    board = chess.Board()

    engine = ChessEngine(
        max_depth=2,
        use_advanced_ordering=True,
    )

    result = engine.best_move(
        board,
        time_limit=10.0,
    )

    assert result.move in board.legal_moves
    assert result.depth == 2
    assert result.status == "completed"


def test_engine_without_advanced_ordering():
    board = chess.Board()

    engine = ChessEngine(
        max_depth=2,
        use_advanced_ordering=False,
    )

    result = engine.best_move(
        board,
        time_limit=10.0,
    )

    assert result.move in board.legal_moves
    assert result.depth == 2
    assert result.status == "completed"
