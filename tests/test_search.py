
import chess

from chess_engine.evaluation.heuristic import HeuristicEvaluator
from chess_engine.search.negamax import (
    INFINITY,
    MATE_SCORE,
    negamax,
)
from chess_engine.search.quiescence import quiescence
from chess_engine.utils.time_manager import TimeManager


def run_search(board: chess.Board, depth: int) -> int:
    return negamax(
        board=board,
        depth=depth,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=HeuristicEvaluator(),
        timer=TimeManager(10.0),
    )


def run_quiescence(board: chess.Board) -> int:
    return quiescence(
        board=board,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=HeuristicEvaluator(),
        timer=TimeManager(10.0),
    )


def test_depth_zero_initial_position():
    board = chess.Board()

    assert run_search(board, depth=0) == 0


def test_negamax_does_not_modify_board():
    board = chess.Board()
    original_fen = board.fen()

    run_search(board, depth=2)

    assert board.fen() == original_fen
    assert len(board.move_stack) == 0


def test_checkmate_returns_negative_score():
    board = chess.Board()
    board.push_san("f3")
    board.push_san("e5")
    board.push_san("g4")
    board.push_san("Qh4#")

    score = run_search(board, depth=2)

    assert score <= -MATE_SCORE + 10


def test_stalemate_returns_zero():
    board = chess.Board(
        "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
    )

    assert board.is_stalemate()
    assert run_search(board, depth=2) == 0


def test_quiescence_does_not_modify_board():
    board = chess.Board(
        "4k3/8/8/8/3q4/8/3R4/4K3 w - - 0 1"
    )

    original_fen = board.fen()

    run_quiescence(board)

    assert board.fen() == original_fen


def test_quiescence_recognizes_free_capture():
    board = chess.Board(
        "4k3/8/8/8/3q4/8/3R4/4K3 w - - 0 1"
    )

    # A torre branca em d2 pode capturar a dama
    # preta em d4? Não diretamente: existe d3.
    # Como d3 está vazio, a captura é legal.
    assert chess.Move.from_uci("d2d4") in board.legal_moves

    static_score = HeuristicEvaluator().evaluate(board)
    tactical_score = run_quiescence(board)

    assert tactical_score > static_score


def test_quiescence_handles_checkmate():
    board = chess.Board()
    board.push_san("f3")
    board.push_san("e5")
    board.push_san("g4")
    board.push_san("Qh4#")

    assert run_quiescence(board) <= -MATE_SCORE + 10


def test_quiescence_handles_check():
    board = chess.Board(
        "4k3/8/8/8/8/8/4r3/4K3 w - - 0 1"
    )

    assert board.is_check()

    original_fen = board.fen()
    run_quiescence(board)

    assert board.fen() == original_fen


def test_quiescence_recognizes_stalemate():
    board = chess.Board(
        "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"
    )

    assert run_quiescence(board) == 0