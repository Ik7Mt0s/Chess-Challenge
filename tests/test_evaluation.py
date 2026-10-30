
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


def test_centralized_white_knight_is_better():
    board = chess.Board()
    evaluator = HeuristicEvaluator()

    initial_score = evaluator.evaluate(board)

    board.remove_piece_at(chess.G1)
    board.set_piece_at(
        chess.D4,
        chess.Piece(chess.KNIGHT, chess.WHITE),
    )

    assert evaluator.evaluate(board) > initial_score


def test_centralized_black_knight_is_better_for_black():
    board = chess.Board()
    evaluator = HeuristicEvaluator()

    initial_score = evaluator.evaluate(board)

    board.remove_piece_at(chess.G8)
    board.set_piece_at(
        chess.D5,
        chess.Piece(chess.KNIGHT, chess.BLACK),
    )

    assert evaluator.evaluate(board) < initial_score


def test_advanced_white_pawn_receives_bonus():
    board = chess.Board()
    evaluator = HeuristicEvaluator()

    initial_score = evaluator.evaluate(board)

    board.remove_piece_at(chess.E2)
    board.set_piece_at(
        chess.E4,
        chess.Piece(chess.PAWN, chess.WHITE),
    )

    assert evaluator.evaluate(board) > initial_score


def test_advanced_black_pawn_receives_bonus():
    board = chess.Board()
    evaluator = HeuristicEvaluator()

    initial_score = evaluator.evaluate(board)

    board.remove_piece_at(chess.E7)
    board.set_piece_at(
        chess.E5,
        chess.Piece(chess.PAWN, chess.BLACK),
    )

    assert evaluator.evaluate(board) < initial_score


def test_positional_evaluation_is_symmetric():
    board = chess.Board()
    evaluator = HeuristicEvaluator()

    board.push_san("e4")
    board.push_san("e5")
    board.push_san("Nf3")
    board.push_san("Nc6")

    assert evaluator.evaluate(board) == 0
