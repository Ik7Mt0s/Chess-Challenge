
import chess
import pytest

from chess_engine.evaluation.heuristic import HeuristicEvaluator
from chess_engine.search.draw_rules import is_draw
from chess_engine.search.negamax import (
    INFINITY,
    negamax,
)
from chess_engine.search.quiescence import quiescence
from chess_engine.utils.time_manager import TimeManager


def make_board(moves):
    board = chess.Board()

    for move in moves:
        board.push_uci(move)

    return board


def search_score(board, depth=1):
    return negamax(
        board=board,
        depth=depth,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=HeuristicEvaluator(),
        timer=TimeManager(10.0),
    )


def quiescence_score(board):
    return quiescence(
        board=board,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=HeuristicEvaluator(),
        timer=TimeManager(10.0),
    )


def test_initial_position_is_not_draw():
    board = chess.Board()

    assert not is_draw(board)
    assert not board.can_claim_draw()


def test_no_expensive_claim_check_without_sufficient_history(
    monkeypatch,
):
    board = chess.Board()

    def unexpected_call():
        pytest.fail(
            "can_claim_draw não deveria ser chamado."
        )

    monkeypatch.setattr(
        board,
        "can_claim_draw",
        unexpected_call,
    )

    assert not is_draw(board)


def test_six_reversible_plies_do_not_require_claim_check(
    monkeypatch,
):
    board = make_board(
        [
            "g1f3",
            "g8f6",
            "f3g1",
            "f6g8",
            "g1f3",
            "g8f6",
        ]
    )

    def unexpected_call():
        pytest.fail(
            "Ainda não há histórico suficiente."
        )

    monkeypatch.setattr(
        board,
        "can_claim_draw",
        unexpected_call,
    )

    assert not is_draw(board)


def test_threefold_can_be_claimed_by_next_move():
    board = make_board(
        [
            "g1f3",
            "g8f6",
            "f3g1",
            "f6g8",
            "g1f3",
            "g8f6",
            "f3g1",
        ]
    )

    assert board.can_claim_threefold_repetition()
    assert is_draw(board)


def test_threefold_repetition_already_on_board():
    board = make_board(
        [
            "g1f3",
            "g8f6",
            "f3g1",
            "f6g8",
            "g1f3",
            "g8f6",
            "f3g1",
            "f6g8",
        ]
    )

    assert board.is_repetition(3)
    assert is_draw(board)


def test_capture_resets_reversible_history():
    board = make_board(
        [
            "e2e4",
            "d7d5",
            "e4d5",
        ]
    )

    assert board.halfmove_clock == 0
    assert not is_draw(board)


def test_fifty_move_rule_can_be_claimed():
    board = chess.Board(
        "7k/8/8/8/8/8/8/K5R1 w - - 99 50"
    )

    assert board.is_valid()
    assert board.can_claim_fifty_moves()
    assert is_draw(board)


def test_seventyfive_move_rule():
    board = chess.Board(
        "7k/8/8/8/8/8/8/K5R1 w - - 150 76"
    )

    assert board.is_valid()
    assert board.is_seventyfive_moves()
    assert is_draw(board)

def test_insufficient_material():
    board = chess.Board(
        "7k/8/8/8/8/8/8/K7 w - - 0 1"
    )

    assert board.is_insufficient_material()
    assert is_draw(board)


def test_stalemate():
    board = chess.Board(
        "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
    )

    assert board.is_stalemate()
    assert is_draw(board)


def test_negamax_recognizes_claimable_threefold():
    board = make_board(
        [
            "g1f3",
            "g8f6",
            "f3g1",
            "f6g8",
            "g1f3",
            "g8f6",
            "f3g1",
        ]
    )

    original_fen = board.fen()
    original_moves = list(board.move_stack)

    assert search_score(board) == 0
    assert board.fen() == original_fen
    assert board.move_stack == original_moves


def test_quiescence_recognizes_claimable_threefold():
    board = make_board(
        [
            "g1f3",
            "g8f6",
            "f3g1",
            "f6g8",
            "g1f3",
            "g8f6",
            "f3g1",
        ]
    )

    original_fen = board.fen()
    original_moves = list(board.move_stack)

    assert quiescence_score(board) == 0
    assert board.fen() == original_fen
    assert board.move_stack == original_moves


def test_fivefold_repetition():
    board = make_board(
        [
            "g1f3",
            "g8f6",
            "f3g1",
            "f6g8",
        ] * 4
    )

    assert board.is_fivefold_repetition()
    assert is_draw(board)


@pytest.mark.parametrize(
    "moves",
    [
        [],
        ["g1f3"],
        ["g1f3", "g8f6"],
        ["g1f3", "g8f6", "f3g1"],
        ["g1f3", "g8f6", "f3g1", "f6g8"],
        ["g1f3", "g8f6", "f3g1", "f6g8", "g1f3"],
        [
            "g1f3",
            "g8f6",
            "f3g1",
            "f6g8",
            "g1f3",
            "g8f6",
            "f3g1",
        ],
    ],
)
def test_matches_python_chess_draw_semantics(moves):
    board = make_board(moves)

    expected = (
        board.is_stalemate()
        or board.is_insufficient_material()
        or board.is_seventyfive_moves()
        or board.is_fivefold_repetition()
        or board.can_claim_draw()
    )

    assert is_draw(board) == expected
