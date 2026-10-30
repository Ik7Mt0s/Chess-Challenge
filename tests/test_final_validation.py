from unittest.mock import patch

import chess
import pytest

from chess_engine.engine import ChessEngine
from chess_engine.evaluation.heuristic import HeuristicEvaluator
from chess_engine.search.negamax import INFINITY, negamax
from chess_engine.search.quiescence import MATE_SCORE, quiescence
from chess_engine.utils.time_manager import SearchTimeout, TimeManager


def test_engine_returns_legal_move_without_changing_board():
    board = chess.Board()
    original_fen = board.fen()
    original_history = list(board.move_stack)

    engine = ChessEngine(max_depth=2)
    result = engine.best_move(board, time_limit=10.0)

    assert result.move in board.legal_moves
    assert result.depth == 2
    assert result.status == "completed"
    assert board.fen() == original_fen
    assert list(board.move_stack) == original_history


def test_engine_rejects_checkmate():
    board = chess.Board()
    for move in ("f3", "e5", "g4", "Qh4#"):
        board.push_san(move)

    assert board.is_checkmate()

    engine = ChessEngine(max_depth=2)

    with pytest.raises(ValueError, match="terminou"):
        engine.best_move(board)


def test_engine_rejects_stalemate():
    board = chess.Board(
        "7k/5K2/6Q1/8/8/8/8/8 b - - 0 1"
    )

    assert board.is_valid()
    assert board.is_stalemate()

    engine = ChessEngine(max_depth=2)

    with pytest.raises(ValueError, match="terminou"):
        engine.best_move(board)


def test_engine_rejects_threefold_repetition():
    board = chess.Board()

    for move in (
        "Nf3", "Nf6", "Ng1", "Ng8",
        "Nf3", "Nf6", "Ng1", "Ng8",
    ):
        board.push_san(move)

    assert board.can_claim_threefold_repetition()
    assert board.is_game_over(claim_draw=True)

    engine = ChessEngine(max_depth=2)

    with pytest.raises(ValueError, match="terminou"):
        engine.best_move(board)


def test_engine_rejects_fifty_move_draw():
    board = chess.Board(
        "7k/8/8/8/8/8/8/K5R1 w - - 100 1"
    )

    assert board.is_valid()
    assert board.can_claim_fifty_moves()
    assert board.is_game_over(claim_draw=True)

    engine = ChessEngine(max_depth=2)

    with pytest.raises(ValueError, match="terminou"):
        engine.best_move(board)


def test_forced_move():
    board = chess.Board(
        "7k/8/5K2/8/8/8/8/7R b - - 0 1"
    )

    assert board.is_valid()
    assert board.legal_moves.count() == 1

    engine = ChessEngine(max_depth=3)
    result = engine.best_move(board, time_limit=1.0)

    assert result.status == "forced"
    assert result.depth == 0
    assert result.move == chess.Move.from_uci("h8g8")


def test_timeout_preserves_last_completed_iteration():
    board = chess.Board()
    original_fen = board.fen()
    original_history = list(board.move_stack)

    engine = ChessEngine(
        max_depth=3,
        use_transposition_table=False,
    )

    root_calls = 0
    root_moves = board.legal_moves.count()

    def simulated_negamax(*args, **kwargs):
        nonlocal root_calls
        root_calls += 1

        # A primeira iteração termina normalmente.
        # A segunda é interrompida no primeiro lance.
        if root_calls > root_moves:
            raise SearchTimeout()

        return 0

    with patch(
        "chess_engine.engine.negamax",
        side_effect=simulated_negamax,
    ):
        result = engine.best_move(
            board,
            time_limit=10.0,
        )

    assert result.status == "timeout"
    assert result.depth == 1
    assert result.move in board.legal_moves
    assert root_calls == root_moves + 1
    assert board.fen() == original_fen
    assert list(board.move_stack) == original_history


def test_timeout_before_first_iteration_uses_fallback():
    board = chess.Board()
    original_fen = board.fen()

    engine = ChessEngine(max_depth=3)

    with patch(
        "chess_engine.engine.negamax",
        side_effect=SearchTimeout(),
    ):
        result = engine.best_move(
            board,
            time_limit=10.0,
        )

    assert result.status == "fallback"
    assert result.depth == 0
    assert result.move in board.legal_moves
    assert board.fen() == original_fen


@pytest.mark.parametrize(
    "fen",
    [
        chess.STARTING_FEN,
        (
            "r1bqk2r/pppp1ppp/2n2n2/4p3/"
            "2B1P3/2N2N2/PPPP1PPP/R1BQK2R "
            "w KQkq - 4 4"
        ),
        (
            "8/5pk1/6p1/7p/7P/6P1/"
            "5PK1/8 w - - 0 1"
        ),
    ],
)
def test_cache_and_ordering_consistency(fen):
    board = chess.Board(fen)

    assert board.is_valid()
    assert not board.is_game_over(claim_draw=True)

    original_fen = board.fen()

    configurations = [
        (False, False),
        (True, False),
        (True, True),
    ]

    results = []

    for use_cache, advanced_ordering in configurations:
        engine = ChessEngine(
            max_depth=2,
            use_transposition_table=use_cache,
            use_advanced_ordering=advanced_ordering,
        )

        result = engine.best_move(
            board,
            time_limit=15.0,
        )

        assert result.depth == 2
        assert result.status == "completed"
        assert result.move in board.legal_moves
        assert board.fen() == original_fen

        results.append(result)

    # A ordenação e o cache não devem alterar a
    # avaliação calculada na mesma profundidade.
    assert len({result.score for result in results}) == 1


def test_negamax_preserves_move_history():
    board = chess.Board()

    for move in ("e4", "e5", "Nf3", "Nc6"):
        board.push_san(move)

    original_fen = board.fen()
    original_history = list(board.move_stack)

    score = negamax(
        board=board,
        depth=2,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=HeuristicEvaluator(),
        timer=TimeManager(15.0),
    )

    assert isinstance(score, int)
    assert board.fen() == original_fen
    assert list(board.move_stack) == original_history


def test_quiescence_recognizes_checkmate():
    board = chess.Board()

    for move in ("f3", "e5", "g4", "Qh4#"):
        board.push_san(move)

    assert board.is_checkmate()

    score = quiescence(
        board=board,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=HeuristicEvaluator(),
        timer=TimeManager(5.0),
    )

    assert score == -MATE_SCORE
