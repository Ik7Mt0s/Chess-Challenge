
import chess
import pytest

from scripts.finetune_lichess import (
    make_dataset,
    outcome_for_turn,
    training_target,
)


class FixedEvaluator:
    def __init__(self, score: int):
        self.score = score

    def evaluate(self, board: chess.Board) -> int:
        return self.score


def test_white_win_from_white_perspective():
    assert outcome_for_turn("1-0", chess.WHITE) == 1.0


def test_white_win_from_black_perspective():
    assert outcome_for_turn("1-0", chess.BLACK) == -1.0


def test_black_win_from_black_perspective():
    assert outcome_for_turn("0-1", chess.BLACK) == 1.0


def test_draw_is_neutral():
    assert outcome_for_turn("1/2-1/2", chess.WHITE) == 0.0
    assert outcome_for_turn("1/2-1/2", chess.BLACK) == 0.0


def test_target_combines_heuristic_and_result():
    board = chess.Board()

    target = training_target(
        board,
        result="1-0",
        evaluator=FixedEvaluator(100),
        outcome_weight=0.25,
    )

    # 75% de 0.1 + 25% de 0.3
    assert target == pytest.approx(0.15)


def test_target_respects_black_perspective():
    board = chess.Board()
    board.push_uci("e2e4")

    target = training_target(
        board,
        result="1-0",
        evaluator=FixedEvaluator(100),
        outcome_weight=0.25,
    )

    assert target == pytest.approx(-0.15)


def test_target_is_clamped():
    target = training_target(
        chess.Board(),
        result="1-0",
        evaluator=FixedEvaluator(100000),
    )

    assert -0.95 <= target <= 0.95


def test_dataset_tensor_shape():
    board = chess.Board()

    dataset = make_dataset([
        (board.fen(), 0.2),
        (board.fen(), -0.1),
    ])

    features, target = dataset[0]

    assert len(dataset) == 2
    assert tuple(features.shape) == (12, 8, 8)
    assert tuple(target.shape) == (1,)
    assert target.item() == pytest.approx(0.2)
