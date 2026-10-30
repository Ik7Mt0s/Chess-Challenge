import pytest
import chess

from chess_engine.board import ChessBoard


def test_initial_position():
    game = ChessBoard()

    assert game.board.fen() == chess.STARTING_FEN
    assert len(game.legal_moves()) == 20


def test_play_uci():
    game = ChessBoard()
    game.play("e2e4")

    assert game.board.piece_at(chess.E4).symbol() == "P"
    assert game.board.turn == chess.BLACK


def test_play_san():
    game = ChessBoard()
    game.play("e4")

    assert game.board.piece_at(chess.E4).symbol() == "P"


def test_illegal_move():
    game = ChessBoard()

    with pytest.raises(ValueError):
        game.play("e2e5")


def test_undo():
    game = ChessBoard()
    initial_fen = game.fen()

    game.play("e4")
    game.undo()

    assert game.fen() == initial_fen


def test_checkmate():
    game = ChessBoard()

    for move in ["f3", "e5", "g4", "Qh4#"]:
        game.play(move)

    assert game.is_game_over()
    assert game.result() == "0-1"