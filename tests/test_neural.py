import pytest
import torch
import chess
from chess_engine.neural.representation import board_to_tensor
from chess_engine.neural.model import SimpleChessNet

# --- Testes da Representação (board_to_tensor) ---

def test_board_to_tensor_dimensions_and_type():
    """Garante que a saída é um Tensor float32 de formato (12, 8, 8)."""
    board = chess.Board()
    tensor = board_to_tensor(board)

    assert isinstance(tensor, torch.Tensor)
    assert tensor.shape == (12, 8, 8)
    assert tensor.dtype == torch.float32


def test_board_to_tensor_initial_piece_count():
    """Na posição inicial, exatamente 32 peças devem ser mapeadas (soma das matrizes = 32)."""
    board = chess.Board()
    tensor = board_to_tensor(board)

    # A soma de todos os valores 1.0 deve ser igual a 32 peças
    assert tensor.sum().item() == 32.0


def test_board_to_tensor_black_perspective_flip():
    """Verifica se a rotação do tabuleiro mantém o número correto de peças quando for a vez das Pretas."""
    board = chess.Board()
    board.push_san("e4") # Passa a vez para as Pretas

    tensor = board_to_tensor(board, flip_black_perspective=True)
    
    assert tensor.shape == (12, 8, 8)
    assert tensor.sum().item() == 32.0


# --- Testes da Arquitetura (SimpleChessNet) ---

def test_model_forward_pass_shape():
    """Verifica se a rede aceita o batch tensor e devolve o formato (1, 1)."""
    model = SimpleChessNet()
    board = chess.Board()
    
    # Adiciona a dimensão do batch: (12, 8, 8) -> (1, 12, 8, 8)
    input_tensor = board_to_tensor(board).unsqueeze(0)
    
    output = model(input_tensor)

    assert output.shape == (1, 1)


def test_model_output_range():
    """Garante que a saída do tanh está estritamente entre -1.0 e 1.0."""
    model = SimpleChessNet()
    board = chess.Board()
    input_tensor = board_to_tensor(board).unsqueeze(0)
    
    output = model(input_tensor).item()

    assert -1.0 <= output <= 1.0