import chess
import pytest

from chess_engine.engine import ChessEngine
from chess_engine.evaluation.heuristic import HeuristicEvaluator
from chess_engine.search.negamax import INFINITY, negamax
from chess_engine.search.transposition import (
    BoundType,
    TranspositionTable,
)
from chess_engine.utils.time_manager import TimeManager


def test_empty_table():
    table = TranspositionTable()

    assert len(table) == 0
    assert table.get(chess.Board()) is None
    assert table.stats()["misses"] == 1


def test_store_and_retrieve_exact_score():
    table = TranspositionTable()
    board = chess.Board()
    move = chess.Move.from_uci("e2e4")

    table.store(
        board=board,
        depth=3,
        score=45,
        bound=BoundType.EXACT,
        best_move=move,
    )

    entry = table.get(board)

    assert entry is not None
    assert entry.depth == 3
    assert entry.score == 45
    assert entry.bound == BoundType.EXACT
    assert entry.best_move == move


def test_reject_shallower_replacement():
    table = TranspositionTable()
    board = chess.Board()

    table.store(board, 4, 100, BoundType.EXACT)
    table.store(board, 2, 50, BoundType.EXACT)

    entry = table.get(board)

    assert entry is not None
    assert entry.depth == 4
    assert entry.score == 100


def test_memory_limit():
    table = TranspositionTable(max_entries=2)
    board = chess.Board()

    table.store(board, 1, 10, BoundType.EXACT)

    board.push_san("e4")
    table.store(board, 1, 20, BoundType.EXACT)

    board.push_san("e5")
    table.store(board, 1, 30, BoundType.EXACT)

    assert len(table) == 2
    assert table.get(chess.Board()) is None


def test_different_histories_do_not_share_cache():
    table = TranspositionTable()

    initial = chess.Board()

    repeated = chess.Board()
    for move in ("Nf3", "Nf6", "Ng1", "Ng8"):
        repeated.push_san(move)

    assert initial.board_fen() == repeated.board_fen()
    assert initial.turn == repeated.turn

    table.store(
        initial,
        depth=3,
        score=50,
        bound=BoundType.EXACT,
    )

    assert table.get(repeated) is None


def test_mate_score_adjusted_by_ply():
    table = TranspositionTable()
    board = chess.Board()

    table.store(
        board,
        depth=4,
        score=99_995,
        bound=BoundType.EXACT,
        ply=5,
    )

    same_ply = table.get(board, ply=5)
    different_ply = table.get(board, ply=8)

    assert same_ply is not None
    assert different_ply is not None

    assert same_ply.score == 99_995
    assert different_ply.score == 99_992


def test_negative_mate_score_adjusted():
    table = TranspositionTable()
    board = chess.Board()

    table.store(
        board,
        depth=4,
        score=-99_995,
        bound=BoundType.EXACT,
        ply=5,
    )

    entry = table.get(board, ply=8)

    assert entry is not None
    assert entry.score == -99_992


def test_cache_clear():
    table = TranspositionTable()
    board = chess.Board()

    table.store(board, 2, 15, BoundType.EXACT)
    table.get(board)

    table.clear()

    assert len(table) == 0
    assert table.stats()["hits"] == 0
    assert table.stats()["stores"] == 0


def test_invalid_capacity():
    with pytest.raises(ValueError):
        TranspositionTable(max_entries=0)


def test_negamax_with_and_without_cache():
    board = chess.Board()
    original_fen = board.fen()

    evaluator = HeuristicEvaluator()

    without_cache = negamax(
        board=board,
        depth=2,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=evaluator,
        timer=TimeManager(10.0),
    )

    table = TranspositionTable()

    with_cache = negamax(
        board=board,
        depth=2,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=evaluator,
        timer=TimeManager(10.0),
        transposition_table=table,
    )

    assert with_cache == without_cache
    assert board.fen() == original_fen
    assert len(board.move_stack) == 0
    assert len(table) > 0


def test_second_search_reuses_cache():
    board = chess.Board()
    table = TranspositionTable()
    evaluator = HeuristicEvaluator()

    first_score = negamax(
        board=board,
        depth=2,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=evaluator,
        timer=TimeManager(10.0),
        transposition_table=table,
    )

    hits_before = table.hits

    second_score = negamax(
        board=board,
        depth=2,
        alpha=-INFINITY,
        beta=INFINITY,
        evaluator=evaluator,
        timer=TimeManager(10.0),
        transposition_table=table,
    )

    assert second_score == first_score
    assert table.hits > hits_before


def test_engine_with_cache_returns_legal_move():
    board = chess.Board()
    original_fen = board.fen()

    engine = ChessEngine(
        max_depth=2,
        use_transposition_table=True,
    )

    result = engine.best_move(
        board,
        time_limit=5.0,
    )

    assert result.move in board.legal_moves
    assert board.fen() == original_fen
    assert len(board.move_stack) == 0


def test_engine_without_cache_returns_legal_move():
    board = chess.Board()

    engine = ChessEngine(
        max_depth=2,
        use_transposition_table=False,
    )

    result = engine.best_move(
        board,
        time_limit=5.0,
    )

    assert result.move in board.legal_moves
    assert engine.cache_stats()["entries"] == 0
