import importlib.util
from pathlib import Path

import chess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "profile_engine.py"

spec = importlib.util.spec_from_file_location(
    "profile_engine",
    SCRIPT,
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_positions_are_valid():
    module.validate_positions()

    for fen in module.POSITIONS.values():
        assert chess.Board(fen).is_valid()


def test_benchmark_has_distinct_positions():
    assert len(module.POSITIONS) == 4
    assert len(set(module.POSITIONS.values())) == 4


def test_run_engine_preserves_input_position():
    fen = module.POSITIONS["initial"]

    result, elapsed, profiler = module.run_engine(
        fen=fen,
        depth=1,
        time_limit=1.0,
    )

    board = chess.Board(fen)

    assert result.move in board.legal_moves
    assert elapsed >= 0
    assert profiler is None
    assert board.fen() == fen


def test_profile_returns_function_costs():
    fen = module.POSITIONS["opening"]

    result, elapsed, profiler = module.run_engine(
        fen=fen,
        depth=1,
        time_limit=1.0,
        profile=True,
    )

    rows = module.profile_functions(profiler)

    assert result.move in chess.Board(fen).legal_moves
    assert elapsed >= 0
    assert rows
    assert all(row["calls"] >= 1 for row in rows)
    assert all(row["cumulative_seconds"] >= 0 for row in rows)


def test_save_csv(tmp_path):
    path = tmp_path / "results.csv"

    module.save_csv(
        path,
        [
            {"position": "initial", "nodes": 100},
            {"position": "opening", "nodes": 200},
        ],
    )

    content = path.read_text(encoding="utf-8")

    assert path.exists()
    assert "position,nodes" in content
    assert "initial,100" in content
    assert "opening,200" in content
