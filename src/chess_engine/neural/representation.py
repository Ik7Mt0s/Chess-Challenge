import chess
import numpy as np
import torch


PIECE_INDICES = {
    chess.PAWN: 0,
    chess.KNIGHT: 1,
    chess.BISHOP: 2,
    chess.ROOK: 3,
    chess.QUEEN: 4,
    chess.KING: 5,
}


def board_to_tensor(
    board: chess.Board,
    flip_black_perspective: bool = True,
) -> torch.Tensor:
    """
    Converte o tabuleiro em um tensor (12, 8, 8).

    Canais 0-5: peças do jogador ativo.
    Canais 6-11: peças do adversário.

    Preserva a representação utilizada no treinamento.
    """
    tensor = np.zeros(
        (12, 8, 8),
        dtype=np.float32,
    )

    active_color = board.turn

    flip = (
        flip_black_perspective
        and active_color == chess.BLACK
    )

    for square, piece in board.piece_map().items():
        layer = PIECE_INDICES[piece.piece_type]

        if piece.color != active_color:
            layer += 6

        rank = square >> 3
        file = square & 7

        if flip:
            row = rank
            col = 7 - file
        else:
            row = 7 - rank
            col = file

        tensor[layer, row, col] = 1.0

    return torch.from_numpy(tensor)
