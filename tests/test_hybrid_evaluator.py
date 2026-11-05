from pathlib import Path
import chess
import pytest

from chess_engine.evaluation.neural import NeuralEvaluator, HybridEvaluator


def test_neural_evaluator_loads_weights_file():
    weights_path = Path("weights/simple_chess_net.pth")
    assert weights_path.exists(), "O arquivo weights/simple_chess_net.pth não foi encontrado."

    evaluator = NeuralEvaluator(model_path=weights_path)
    assert not evaluator.model.training

    board = chess.Board()
    score = evaluator.evaluate(board)

    assert isinstance(score, int)
    assert -1000 <= score <= 1000


def test_neural_evaluator_deterministic_output():
    weights_path = Path("weights/simple_chess_net.pth")
    evaluator = NeuralEvaluator(model_path=weights_path)
    
    # FEN válida (Ruy Lopez / Abertura Espanhola)
    board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")

    score1 = evaluator.evaluate(board)
    score2 = evaluator.evaluate(board)

    assert score1 == score2


def test_hybrid_evaluator_with_neural_weights():
    neural_eval = NeuralEvaluator(model_path="weights/simple_chess_net.pth")
    hybrid = HybridEvaluator(neural=neural_eval, lazy_threshold=300)

    board = chess.Board()
    score = hybrid.evaluate(board)

    assert isinstance(score, int)