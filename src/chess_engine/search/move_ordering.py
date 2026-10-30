import chess


PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}


def move_score(board: chess.Board, move: chess.Move) -> int:
    score = 0

    attacker = board.piece_at(move.from_square)
    victim = board.piece_at(move.to_square)

    if board.is_en_passant(move):
        victim_value = PIECE_VALUES[chess.PAWN]
    else:
        victim_value = (
            PIECE_VALUES[victim.piece_type] if victim else 0
        )

    if victim_value:
        attacker_value = (
            PIECE_VALUES[attacker.piece_type] if attacker else 0
        )
        score += 10_000 + victim_value - attacker_value

    if move.promotion:
        score += 8_000 + PIECE_VALUES[move.promotion]

    if board.gives_check(move):
        score += 500

    return score


def order_moves(
    board: chess.Board,
    moves: list[chess.Move] | None = None,
) -> list[chess.Move]:
    candidates = (
        list(board.legal_moves) if moves is None else list(moves)
    )

    return sorted(
        candidates,
        key=lambda move: move_score(board, move),
        reverse=True,
    )