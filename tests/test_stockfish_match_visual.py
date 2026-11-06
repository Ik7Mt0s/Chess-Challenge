import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "stockfish_match_visual.py"

spec = importlib.util.spec_from_file_location(
    "stockfish_match_visual",
    SCRIPT,
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_strategy_name_records_see_quiescence_ordering():
    assert module.ordering_strategy_name(True) == "original-see-pvs"
    assert module.ordering_strategy_name(False) == "optimized-see-pvs"


def test_visual_match_has_no_artificial_move_delay():
    assert module.DEFAULT_VISUAL_INTERVAL == 0.0
