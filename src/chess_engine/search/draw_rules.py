import chess


MIN_PLIES_FOR_THREEFOLD_CLAIM = 7
MIN_PLIES_FOR_FIVEFOLD_REPETITION = 16
FIFTY_MOVE_CLAIM_THRESHOLD = 99


def is_draw(board: chess.Board) -> bool:
    """
    Verifica condições de empate relevantes para a busca.

    Evita verificações caras de repetição quando ainda
    não existe histórico suficiente para uma reivindicação.

    Preserva:
    - Afogamento (stalemate);
    - Material insuficiente;
    - Regra automática dos 75 movimentos;
    - Repetição automática de cinco ocorrências;
    - Reivindicação pela regra dos 50 movimentos;
    - Reivindicação por três repetições, inclusive
      quando possível pelo próximo lance.
    """

    if board.is_stalemate():
        return True

    if board.is_insufficient_material():
        return True

    if board.is_seventyfive_moves():
        return True

    reversible_plies = min(
        board.halfmove_clock,
        len(board.move_stack),
    )

    if reversible_plies >= MIN_PLIES_FOR_FIVEFOLD_REPETITION:
        if board.is_fivefold_repetition():
            return True

    can_claim_fifty_moves = (
        board.halfmove_clock >= FIFTY_MOVE_CLAIM_THRESHOLD
    )

    can_claim_threefold = (
        reversible_plies >= MIN_PLIES_FOR_THREEFOLD_CLAIM
    )

    if can_claim_fifty_moves or can_claim_threefold:
        return board.can_claim_draw()

    return False
