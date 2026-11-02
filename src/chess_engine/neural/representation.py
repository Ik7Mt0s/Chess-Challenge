import numpy as np
import torch
import chess

# Mapeamento dos tipos de peça para os índices de canais (0 a 5)
PIECE_INDICES = {
    chess.PAWN: 0,
    chess.KNIGHT: 1,
    chess.BISHOP: 2,
    chess.ROOK: 3,
    chess.QUEEN: 4,
    chess.KING: 5,
}

def board_to_tensor(board: chess.Board, flip_black_perspective: bool = True) -> torch.Tensor:
    """
    Converte um objeto chess.Board em um tensor PyTorch de formato (12, 8, 8).
    
    Canais 0 a 5:  Peças do jogador ativo (P, N, B, R, Q, K)
    Canais 6 a 11: Peças do oponente (P, N, B, R, Q, K)

    :param board: Instância atual do tabuleiro do python-chess.
    :param flip_black_perspective: Se True, inverte o tabuleiro quando for a vez das Pretas,
                                   fazendo a rede sempre analisar da perspectiva do jogador atual.
    :return: torch.Tensor de forma (12, 8, 8) e tipo float32.
    """
    # numpy.zeros(shape, dtype=float, order='C')
    # cria um novo array(3d) de forma e tipo especificados, preenchido inteiramente com zeros
    tensor = np.zeros((12, 8, 8), dtype=np.float32)
    
    # Define a cor de quem está jogando e quem é o oponente
    # Usa a propriedade board.turn: Retorna chess.WHITE(True) ou chess.BLACK(False)
    active_color = board.turn
    opponent_color = not active_color

    for piece_type, layer in PIECE_INDICES.items():
        #Peças do jogador ativo (canais 0-5)
        #sq(square)=casa do tabuleiro
        #tabuleiro é armazenado como uma lista simples de 64 elementos
        for sq in board.pieces(piece_type, active_color):
            row = sq // 8 #Retorna a linha (Divisão inteira)
            col = sq % 8 #Retorna a coluna (Resto da divisão)
            
            # Se for a vez das pretas e quisermos virar a perspectiva
            if flip_black_perspective and active_color == chess.BLACK:
                row = 7 - row
                col = 7 - col
            else:
                row = 7 - row  # Inverte para manter a fileira 1 na base da matriz

            tensor[layer, row, col] = 1.0

        # Peças do oponente (canais 6-11)
        for sq in board.pieces(piece_type, opponent_color):
            row = sq // 8
            col = sq % 8
            
            if flip_black_perspective and active_color == chess.BLACK:
                row = 7 - row
                col = 7 - col
            else:
                row = 7 - row

            tensor[layer + 6, row, col] = 1.0

    return torch.from_numpy(tensor)