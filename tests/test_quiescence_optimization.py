
import chess
import pytest

from chess_engine.evaluation.base import PositionEvaluator
from chess_engine.search.metrics import SearchMetrics
from chess_engine.search.quiescence import (
    DEFAULT_QUIESCENCE_DEPTH,
    MATE_SCORE,
    _tactical_moves,
    quiescence,
)


class DummyTimer:
    def check(self):
        return None


class MaterialEvaluator(PositionEvaluator):
    VALUES = {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 0,
    }

    def evaluate(self, board: chess.Board) -> int:
        score = 0

        for piece_type, value in self.VALUES.items():
            white = len(board.pieces(piece_type, chess.WHITE))
            black = len(board.pieces(piece_type, chess.BLACK))

            score += (white - black) * value

        return score


def search(board, depth=DEFAULT_QUIESCENCE_DEPTH):
    return quiescence(
        board=board,
        alpha=-1_000_000,
        beta=1_000_000,
        evaluator=MaterialEvaluator(),
        timer=DummyTimer(),
        max_depth=depth,
    )


def test_tactical_moves_exclude_quiet_moves():
    board = chess.Board()

    assert _tactical_moves(board) == []


def test_tactical_moves_include_capture():
    board = chess.Board(
        "4k3/8/8/8/3q4/3R4/8/4K3 w - - 0 1"
    )

    moves = _tactical_moves(board)

    assert chess.Move.from_uci("d3d4") in moves
    assert all(
        board.is_capture(move) or move.promotion
        for move in moves
    )


def test_tactical_moves_include_quiet_promotion():
    board = chess.Board(
        "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"
    )

    moves = _tactical_moves(board)

    for promotion in ("q", "r", "b", "n"):
        move = chess.Move.from_uci(
            f"a7a8{promotion}"
        )

        assert move in moves


def test_tactical_moves_include_en_passant():
    board = chess.Board(
        "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1"
    )

    en_passant = chess.Move.from_uci("e5d6")

    assert en_passant in _tactical_moves(board)
    assert board.is_en_passant(en_passant)


def test_tactical_moves_match_legal_reference():
    positions = [
        chess.STARTING_FEN,
        "4k3/P7/8/8/8/8/8/4K3 w - - 0 1",
        "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
        "4k3/8/8/8/3q4/3R4/8/4K3 w - - 0 1",
    ]

    for fen in positions:
        board = chess.Board(fen)

        reference = {
            move
            for move in board.legal_moves
            if board.is_capture(move) or move.promotion
        }

        assert set(_tactical_moves(board)) == reference


def test_quiescence_recognizes_free_queen_capture():
    board = chess.Board(
        "4k3/8/8/8/3q4/3R4/8/4K3 w - - 0 1"
    )

    score = search(board)

    assert score >= 400


def test_quiescence_recognizes_quiet_promotion():
    board = chess.Board(
        "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"
    )

    score = search(board)

    assert score >= 800


def test_quiescence_recognizes_checkmate():
    board = chess.Board()

    for san in ("f3", "e5", "g4", "Qh4#"):
        board.push_san(san)

    assert search(board) == -MATE_SCORE


def test_quiescence_preserves_position_and_history():
    board = chess.Board()

    for san in ("e4", "d5", "exd5", "Qxd5"):
        board.push_san(san)

    fen = board.fen()
    history = list(board.move_stack)

    search(board)

    assert board.fen() == fen
    assert board.move_stack == history


@pytest.mark.parametrize("depth", [0, 1, 3, 5, 6])
def test_quiescence_accepts_explicit_depth(depth):
    board = chess.Board()

    result = search(board, depth=depth)

    assert isinstance(result, int)
    assert board.fen() == chess.STARTING_FEN


def test_quiescence_counts_nodes():
    board = chess.Board(
        "4k3/8/8/8/3q4/3R4/8/4K3 w - - 0 1"
    )

    metrics = SearchMetrics()

    quiescence(
        board=board,
        alpha=-1_000_000,
        beta=1_000_000,
        evaluator=MaterialEvaluator(),
        timer=DummyTimer(),
        max_depth=3,
        metrics=metrics,
    )

    assert metrics.quiescence_nodes > 0


def test_check_evasions_remain_available():
    board = chess.Board(
        "4k3/8/8/8/8/8/4r3/4K3 w - - 0 1"
    )

    assert board.is_check()

    result = search(board, depth=0)

    assert isinstance(result, int)
    assert board.is_check()
