import importlib

import chess
import pytest

from chess_engine.engine import ChessEngine
from chess_engine.evaluation.base import PositionEvaluator
from chess_engine.evaluation.heuristic import HeuristicEvaluator


negamax_module = importlib.import_module(
    "chess_engine.search.negamax"
)
engine_module = importlib.import_module(
    "chess_engine.engine"
)


class ZeroEvaluator(PositionEvaluator):
    def evaluate(self, board):
        return 0


class DummyTimer:
    def check(self):
        return None


def test_recursive_pvs_uses_null_window_after_first_move(
    monkeypatch,
):
    windows = []

    def recorded_quiescence(*, alpha, beta, **kwargs):
        windows.append((alpha, beta))
        return 0

    monkeypatch.setattr(
        negamax_module,
        "quiescence",
        recorded_quiescence,
    )

    negamax_module.negamax(
        board=chess.Board(),
        depth=1,
        alpha=-100,
        beta=100,
        evaluator=ZeroEvaluator(),
        timer=DummyTimer(),
        use_pvs=True,
    )

    assert windows[0] == (-100, 100)
    assert windows[1:] == [(-1, 0)] * 19


def test_root_pvs_uses_null_window_after_first_move(
    monkeypatch,
):
    windows = []

    def recorded_negamax(*, alpha, beta, **kwargs):
        windows.append((alpha, beta))
        return 0

    monkeypatch.setattr(
        engine_module,
        "negamax",
        recorded_negamax,
    )

    engine = ChessEngine(
        evaluator=ZeroEvaluator(),
        max_depth=1,
        use_transposition_table=False,
        use_pvs=True,
    )
    result = engine.best_move(
        chess.Board(),
        time_limit=10.0,
    )

    assert result.depth == 1
    assert windows[0] == (-1_000_000, 1_000_000)
    assert windows[1:] == [(-1, 0)] * 19


def test_recursive_pvs_researches_improving_probe(
    monkeypatch,
):
    windows = []
    responses = iter([0, -10, -10] + [0] * 30)

    def recorded_quiescence(*, alpha, beta, **kwargs):
        windows.append((alpha, beta))
        return next(responses)

    monkeypatch.setattr(
        negamax_module,
        "quiescence",
        recorded_quiescence,
    )

    score = negamax_module.negamax(
        board=chess.Board(),
        depth=1,
        alpha=-100,
        beta=100,
        evaluator=ZeroEvaluator(),
        timer=DummyTimer(),
        use_pvs=True,
    )

    assert score == 10
    assert windows[:3] == [
        (-100, 100),
        (-1, 0),
        (-100, 0),
    ]


@pytest.mark.parametrize(
    "fen",
    [
        chess.STARTING_FEN,
        "4k3/8/8/8/3q4/3R4/8/4K3 w - - 0 1",
        "4k3/8/8/8/8/8/4r3/4K3 w - - 0 1",
    ],
)
def test_pvs_matches_full_window_at_fixed_depth(fen):
    results = []

    for use_pvs in (False, True):
        board = chess.Board(fen)
        original_fen = board.fen()
        engine = ChessEngine(
            evaluator=HeuristicEvaluator(),
            max_depth=2,
            use_transposition_table=True,
            use_pvs=use_pvs,
        )

        result = engine.best_move(
            board,
            time_limit=20.0,
        )

        assert result.depth == 2
        assert result.status == "completed"
        assert result.move in board.legal_moves
        assert board.fen() == original_fen
        results.append(result)

    assert results[0].score == results[1].score
    assert results[0].move == results[1].move
