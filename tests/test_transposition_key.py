
import chess
import chess.polyglot

from chess_engine.search.transposition import (
    BoundType,
    TranspositionTable,
)


def make_board(moves: list[str]) -> chess.Board:
    board = chess.Board()

    for move in moves:
        board.push_san(move)

    return board


def test_same_position_after_irreversible_move():
    first = make_board([
        "Nf3", "Nf6", "Nc3", "Nc6", "e4",
    ])

    second = make_board([
        "Nc3", "Nc6", "Nf3", "Nf6", "e4",
    ])

    assert first.fen() == second.fen()
    assert first.move_stack != second.move_stack

    assert (
        TranspositionTable.make_key(first)
        == TranspositionTable.make_key(second)
    )


def test_cache_reuses_equivalent_position():
    first = make_board([
        "Nf3", "Nf6", "Nc3", "Nc6", "e4",
    ])

    second = make_board([
        "Nc3", "Nc6", "Nf3", "Nf6", "e4",
    ])

    table = TranspositionTable()

    table.store(
        board=first,
        depth=3,
        score=35,
        bound=BoundType.EXACT,
    )

    entry = table.get(second)

    assert entry is not None
    assert entry.score == 35
    assert table.hits == 1


def test_reversible_histories_remain_distinct():
    first = make_board([
        "Nf3", "Nf6", "Nc3", "Nc6",
    ])

    second = make_board([
        "Nc3", "Nc6", "Nf3", "Nf6",
    ])

    assert first.fen() == second.fen()

    assert (
        TranspositionTable.make_key(first)
        != TranspositionTable.make_key(second)
    )


def test_halfmove_clock_changes_key():
    first = chess.Board(
        "8/5pk1/6p1/7p/7P/6P1/5PK1/8 w - - 0 1"
    )

    second = chess.Board(
        "8/5pk1/6p1/7p/7P/6P1/5PK1/8 w - - 99 1"
    )

    assert (
        chess.polyglot.zobrist_hash(first)
        == chess.polyglot.zobrist_hash(second)
    )

    assert (
        TranspositionTable.make_key(first)
        != TranspositionTable.make_key(second)
    )


def test_same_position_different_repetition_history():
    initial = chess.Board()

    repeated = make_board([
        "Nf3", "Nf6", "Ng1", "Ng8",
    ])

    assert initial.board_fen() == repeated.board_fen()

    table = TranspositionTable()

    table.store(
        board=initial,
        depth=3,
        score=50,
        bound=BoundType.EXACT,
    )

    assert table.get(repeated) is None


def test_memory_limit_still_works():
    table = TranspositionTable(max_entries=2)

    board = chess.Board()
    table.store(board, 1, 10, BoundType.EXACT)

    board.push_san("e4")
    table.store(board, 1, 20, BoundType.EXACT)

    board.push_san("e5")
    table.store(board, 1, 30, BoundType.EXACT)

    assert len(table) == 2
    assert table.get(chess.Board()) is None
