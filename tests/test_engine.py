import chess
import pytest

from chess_engine.engine import ChessEngine


def test_engine_returns_legal_move():
    board = chess.Board()
    engine = ChessEngine(max_depth=2)

    result = engine.best_move(board, time_limit=5.0)

    assert result.move in board.legal_moves
    assert result.depth >= 1


def test_engine_does_not_modify_board():
    board = chess.Board()
    original_fen = board.fen()

    engine = ChessEngine(max_depth=2)
    engine.best_move(board, time_limit=5.0)

    assert board.fen() == original_fen
    assert len(board.move_stack) == 0


def test_engine_rejects_finished_game():
    board = chess.Board()

    for move in ["f3", "e5", "g4", "Qh4#"]:
        board.push_san(move)

    engine = ChessEngine()

    with pytest.raises(ValueError):
        engine.best_move(board)


def test_engine_rejects_invalid_depth():
    with pytest.raises(ValueError):
        ChessEngine(max_depth=0)


def test_engine_returns_move_with_short_deadline():
    board = chess.Board()
    engine = ChessEngine(max_depth=5)

    result = engine.best_move(
        board,
        time_limit=0.001,
    )

    assert result.move in board.legal_moves