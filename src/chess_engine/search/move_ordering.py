import chess


PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

KILLER_FIRST_BONUS = 7_000
KILLER_SECOND_BONUS = 6_500
MAX_HISTORY_BONUS = 4_000
MAX_HISTORY_SCORE = 100_000


class MoveOrderingHeuristics:
    """
    Guarda informações de ordenação durante uma busca.

    Killer Moves:
        Até dois movimentos silenciosos por ply.

    History Heuristic:
        Pontuação acumulada para movimentos silenciosos,
        separada pela cor que joga.
    """

    def __init__(self):
        self.killers: dict[int, list[chess.Move]] = {}
        self.history: dict[tuple[bool, int, int], int] = {}

    def is_killer(self, move: chess.Move, ply: int) -> int:
        killers = self.killers.get(ply, [])

        if killers and killers[0] == move:
            return 1

        if len(killers) > 1 and killers[1] == move:
            return 2

        return 0

    def history_score(
        self,
        color: bool,
        move: chess.Move,
    ) -> int:
        key = (
            color,
            move.from_square,
            move.to_square,
        )
        return self.history.get(key, 0)

    def record_cutoff(
        self,
        board: chess.Board,
        move: chess.Move,
        ply: int,
        depth: int,
    ) -> None:
        """
        Registra um movimento silencioso que provocou
        um corte Alfa-Beta.

        Deve ser chamado com o tabuleiro na posição
        anterior à execução do movimento.
        """
        if board.is_capture(move) or move.promotion:
            return

        killers = self.killers.setdefault(ply, [])

        if move in killers:
            killers.remove(move)

        killers.insert(0, move)
        del killers[2:]

        key = (
            board.turn,
            move.from_square,
            move.to_square,
        )

        bonus = max(1, depth * depth)

        self.history[key] = min(
            MAX_HISTORY_SCORE,
            self.history.get(key, 0) + bonus,
        )

    def reset(self) -> None:
        self.killers.clear()
        self.history.clear()


def move_score(
    board: chess.Board,
    move: chess.Move,
    *,
    score_quiet_checks: bool = True,
) -> int:
    """
    Calcula a pontuação tática do movimento.

    score_quiet_checks=True:
        Comportamento original: pontua qualquer xeque.

    score_quiet_checks=False:
        Pontua xeques apenas em capturas e promoções.
        Evita board.gives_check() para movimentos silenciosos.

    Essa opção altera a ordenação, não as regras
    de legalidade nem a avaliação da posição.
    """
    score = 0

    attacker = board.piece_at(move.from_square)
    victim = board.piece_at(move.to_square)

    is_en_passant = board.is_en_passant(move)

    if is_en_passant:
        victim_value = PIECE_VALUES[chess.PAWN]
    else:
        victim_value = (
            PIECE_VALUES[victim.piece_type]
            if victim
            else 0
        )

    if victim_value:
        attacker_value = (
            PIECE_VALUES[attacker.piece_type]
            if attacker
            else 0
        )

        score += (
            10_000
            + victim_value
            - attacker_value
        )

    if move.promotion:
        score += (
            8_000
            + PIECE_VALUES[move.promotion]
        )

    is_tactical = bool(victim_value or move.promotion)

    if score_quiet_checks or is_tactical:
        if board.gives_check(move):
            score += 500

    return score


def order_moves(
    board: chess.Board,
    moves: list[chess.Move] | None = None,
    *,
    ply: int = 0,
    heuristics: MoveOrderingHeuristics | None = None,
    tt_move: chess.Move | None = None,
    score_quiet_checks: bool = True,
) -> list[chess.Move]:
    """
    Ordena movimentos usando:
    - Movimento da tabela de transposição;
    - Pontuação de capturas e promoções;
    - Killer Moves;
    - History Heuristic;
    - Bônus de xeque, conforme a estratégia escolhida.

    A prioridade entre categorias é determinada
    pela pontuação combinada, exceto o movimento
    da tabela de transposição, que vem primeiro.

    Mantém compatibilidade com chamadas antigas.
    """
    candidates = (
        list(board.legal_moves)
        if moves is None
        else list(moves)
    )

    def score(move: chess.Move) -> tuple[int, int]:
        if tt_move is not None and move == tt_move:
            return (1, 0)

        tactical_score = move_score(
            board,
            move,
            score_quiet_checks=score_quiet_checks,
        )

        if heuristics is None:
            return (0, tactical_score)

        if board.is_capture(move) or move.promotion:
            return (0, tactical_score)

        killer_position = heuristics.is_killer(
            move,
            ply,
        )

        if killer_position == 1:
            tactical_score += KILLER_FIRST_BONUS
        elif killer_position == 2:
            tactical_score += KILLER_SECOND_BONUS

        history = heuristics.history_score(
            board.turn,
            move,
        )

        tactical_score += min(
            MAX_HISTORY_BONUS,
            history * 4,
        )

        return (0, tactical_score)

    return sorted(
        candidates,
        key=score,
        reverse=True,
    )
