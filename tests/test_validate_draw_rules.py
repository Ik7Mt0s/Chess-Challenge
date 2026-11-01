
import importlib.util
from pathlib import Path

import chess
import chess.pgn
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_draw_rules.py"

spec = importlib.util.spec_from_file_location(
    "validate_draw_rules",
    SCRIPT,
)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def create_pgn(path: Path, moves: list[str]) -> None:
    game = chess.pgn.Game()
    node = game
    board = game.board()

    for uci in moves:
        move = chess.Move.from_uci(uci)
        assert move in board.legal_moves
        node = node.add_variation(move)
        board.push(move)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        str(game) + "\n",
        encoding="utf-8",
    )


def test_original_and_optimized_agree_initially():
    board = chess.Board()

    result = module.validate_position(board)

    assert result["equivalent"]
    assert result["history_plies"] == 0
    assert not result["original_draw"]
    assert not result["optimized_draw"]


def test_validate_position_preserves_history():
    board = chess.Board()

    for move in [
        "g1f3",
        "g8f6",
        "f3g1",
        "f6g8",
    ]:
        board.push_uci(move)

    original_fen = board.fen()
    original_stack = list(board.move_stack)

    result = module.validate_position(board)

    assert result["equivalent"]
    assert result["history_plies"] == 4
    assert board.fen() == original_fen
    assert board.move_stack == original_stack


def test_claimable_threefold_with_real_history():
    board = chess.Board()

    for move in [
        "g1f3",
        "g8f6",
        "f3g1",
        "f6g8",
        "g1f3",
        "g8f6",
        "f3g1",
    ]:
        board.push_uci(move)

    result = module.validate_position(board)

    assert result["equivalent"]
    assert result["original_draw"]
    assert result["optimized_draw"]


def test_fifty_move_claim():
    board = chess.Board(
        "7k/8/8/8/8/8/8/K5R1 w - - 99 50"
    )

    result = module.validate_position(board)

    assert result["equivalent"]
    assert result["optimized_draw"]


def test_find_pgn_files_recursively(tmp_path):
    create_pgn(
        tmp_path / "run_001" / "game_001.pgn",
        ["e2e4", "e7e5"],
    )

    create_pgn(
        tmp_path / "run_002" / "game_002.pgn",
        ["d2d4", "d7d5"],
    )

    files = module.find_pgn_files(tmp_path)

    assert len(files) == 2
    assert all(path.suffix == ".pgn" for path in files)


def test_find_pgn_files_rejects_empty_directory(tmp_path):
    with pytest.raises(FileNotFoundError):
        module.find_pgn_files(tmp_path)


def test_load_positions_preserves_history(tmp_path):
    path = tmp_path / "game.pgn"

    create_pgn(
        path,
        [
            "g1f3",
            "g8f6",
            "f3g1",
            "f6g8",
            "g1f3",
            "g8f6",
            "f3g1",
        ],
    )

    positions = module.load_positions(path)

    assert len(positions) == 8
    assert positions[0]["ply"] == 0
    assert positions[-1]["ply"] == 7

    last_board = positions[-1]["board"]

    assert len(last_board.move_stack) == 7
    assert last_board.can_claim_threefold_repetition()


def test_load_positions_sampling(tmp_path):
    path = tmp_path / "game.pgn"

    create_pgn(
        path,
        [
            "e2e4",
            "e7e5",
            "g1f3",
            "b8c6",
            "f1c4",
        ],
    )

    positions = module.load_positions(
        path,
        sample_every=2,
    )

    assert [p["ply"] for p in positions] == [
        0, 2, 4, 5,
    ]


def test_load_positions_rejects_invalid_sampling(tmp_path):
    with pytest.raises(ValueError):
        module.load_positions(
            tmp_path / "missing.pgn",
            sample_every=0,
        )


def test_save_csv(tmp_path):
    path = tmp_path / "results.csv"

    module.save_csv(
        path,
        [
            {"ply": 1, "equivalent": True},
            {"ply": 2, "equivalent": False},
        ],
    )

    content = path.read_text(encoding="utf-8")

    assert path.exists()
    assert "ply,equivalent" in content
    assert "1,True" in content
    assert "2,False" in content


def test_summary_without_divergences():
    rows = [
        {
            "equivalent": True,
            "original_draw": False,
            "history_plies": 0,
            "original_us": 100.0,
            "optimized_us": 20.0,
        },
        {
            "equivalent": True,
            "original_draw": True,
            "history_plies": 7,
            "original_us": 200.0,
            "optimized_us": 50.0,
        },
    ]

    result = module.summarize(rows)

    assert result["positions"] == 2
    assert result["mismatches"] == 0
    assert result["draw_positions"] == 1
    assert result["positions_with_history"] == 1
    assert result["overall_speedup"] == 4.286


def test_summary_detects_divergence():
    rows = [
        {
            "equivalent": False,
            "original_draw": True,
            "history_plies": 10,
            "original_us": 100.0,
            "optimized_us": 50.0,
        },
    ]

    result = module.summarize(rows)

    assert result["mismatches"] == 1
    assert result["equivalent_positions"] == 0


def test_summary_rejects_empty_results():
    with pytest.raises(ValueError):
        module.summarize([])


def test_measure_function_rejects_inconsistent_results():
    board = chess.Board()
    calls = 0

    def inconsistent(_board):
        nonlocal calls
        calls += 1
        return calls % 2 == 1

    with pytest.raises(AssertionError):
        module.measure_function(
            inconsistent,
            board,
            repeats=3,
        )


def test_validate_position_rejects_invalid_repeats():
    with pytest.raises(ValueError):
        module.validate_position(
            chess.Board(),
            repeats=0,
        )
