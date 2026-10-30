import chess

from chess_engine.evaluation.heuristic import HeuristicEvaluator


def test_initial_position_is_equal():
    board = chess.Board()
    evaluator = HeuristicEvaluator()

    assert evaluator.evaluate(board) == 0


def test_white_material_advantage():
    board = chess.Board()
    board.remove_piece_at(chess.D8)

    evaluator = HeuristicEvaluator()

    assert evaluator.evaluate(board) == 900


def test_black_material_advantage():
    board = chess.Board()
    board.remove_piece_at(chess.D1)

    evaluator = HeuristicEvaluator()

    assert evaluator.evaluate(board) == -900


def test_evaluation_does_not_modify_board():
    board = chess.Board()
    original_fen = board.fen()

    evaluator = HeuristicEvaluator()
    evaluator.evaluate(board)

    assert board.fen() == original_fen