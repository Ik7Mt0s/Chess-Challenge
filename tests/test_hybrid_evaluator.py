import chess
from chess_engine.evaluation.neural import NeuralEvaluator, HybridEvaluator

def test_neural_evaluator_returns_int():
    evaluator = NeuralEvaluator()
    board = chess.Board()
    score = evaluator.evaluate(board)

    assert isinstance(score, int)
    assert -1000 <= score <= 1000

def test_hybrid_evaluator_lazy_evaluation():
    hybrid = HybridEvaluator(lazy_threshold=300)
    
    # Posição desbalanceada (Brancas com Dama a mais)
    board = chess.Board("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    score = hybrid.evaluate(board)

    assert isinstance(score, int)