
import chess

from chess_engine.evaluation.base import PositionEvaluator
from chess_engine.search.draw_rules import is_draw
from chess_engine.search.metrics import SearchMetrics
from chess_engine.search.move_ordering import order_moves
from chess_engine.utils.time_manager import TimeManager

MATE_SCORE = 100_000
DEFAULT_QUIESCENCE_DEPTH = 5
DEFAULT_CHECK_EXTENSIONS = 2


def _static_score(
    board: chess.Board,
    evaluator: PositionEvaluator,
) -> int:
    score = evaluator.evaluate(board)
    return score if board.turn == chess.WHITE else -score


def _tactical_moves(board: chess.Board) -> list[chess.Move]:
    """
    Gera capturas legais e promocoes sem captura.

    Evita percorrer todos os movimentos legais apenas
    para descobrir quais sao capturas.

    Promocoes sem captura precisam ser preservadas:
    elas podem alterar radicalmente a avaliacao.
    """
    moves = list(board.generate_legal_captures())

    promotion_rank = (
        chess.BB_RANK_7
        if board.turn == chess.WHITE
        else chess.BB_RANK_2
    )

    for move in board.generate_legal_moves(
        from_mask=promotion_rank
    ):
        if move.promotion and not board.is_capture(move):
            moves.append(move)

    return moves


def _bounded_evasions(
    board: chess.Board,
    alpha: int,
    beta: int,
    evaluator: PositionEvaluator,
    timer: TimeManager,
    ply: int,
    metrics: SearchMetrics | None,
) -> int:
    """
    Avalia respostas legais ao xeque sem iniciar outra
    sequencia recursiva.

    Nunca utiliza stand-pat enquanto o rei esta em xeque.
    """
    best = -1_000_000
    found = False

    for move in board.legal_moves:
        timer.check()
        found = True
        board.push(move)

        try:
            if board.is_checkmate():
                score = MATE_SCORE - (ply + 1)
            elif is_draw(board):
                score = 0
            else:
                score = -_static_score(board, evaluator)
        finally:
            board.pop()

        best = max(best, score)
        alpha = max(alpha, score)

        if alpha >= beta:
            if metrics is not None:
                metrics.alpha_beta_cutoffs += 1
            break

    if not found:
        return -MATE_SCORE + ply

    return best


def quiescence(
    board: chess.Board,
    alpha: int,
    beta: int,
    evaluator: PositionEvaluator,
    timer: TimeManager,
    ply: int = 0,
    max_depth: int = DEFAULT_QUIESCENCE_DEPTH,
    metrics: SearchMetrics | None = None,
    score_quiet_checks: bool = True,
    max_check_extensions: int = DEFAULT_CHECK_EXTENSIONS,
) -> int:
    """
    Quiescencia com geracao seletiva de movimentos.

    Regras:
    - Posicao normal: stand-pat, capturas e promocoes.
    - Rei em xeque: todas as evasoes legais.
    - Nenhum stand-pat enquanto estiver em xeque.
    - Extensoes de xeque limitadas.
    - Nenhuma poda de capturas baseada em material:
      evita descartar sacrificios potencialmente corretos.

    Retorna centipeoes do ponto de vista de quem joga.
    """
    timer.check()

    if metrics is not None:
        metrics.quiescence_nodes += 1

    in_check = board.is_check()

    if in_check and board.is_checkmate():
        return -MATE_SCORE + ply

    if is_draw(board):
        return 0

    if not in_check:
        static_score = _static_score(board, evaluator)

        if static_score >= beta:
            if metrics is not None:
                metrics.alpha_beta_cutoffs += 1
            return static_score

        alpha = max(alpha, static_score)

        if max_depth <= 0:
            return alpha

        moves = _tactical_moves(board)
        next_extensions = max_check_extensions

    else:
        if max_depth <= 0 and max_check_extensions <= 0:
            return _bounded_evasions(
                board=board,
                alpha=alpha,
                beta=beta,
                evaluator=evaluator,
                timer=timer,
                ply=ply,
                metrics=metrics,
            )

        moves = list(board.legal_moves)

        next_extensions = (
            max_check_extensions - 1
            if max_depth <= 0
            else max_check_extensions
        )

    if not moves:
        return -MATE_SCORE + ply if in_check else alpha

    ordered = order_moves(
        board,
        moves,
        score_quiet_checks=score_quiet_checks,
        use_see=True,
    )

    for move in ordered:
        timer.check()
        board.push(move)

        try:
            score = -quiescence(
                board=board,
                alpha=-beta,
                beta=-alpha,
                evaluator=evaluator,
                timer=timer,
                ply=ply + 1,
                max_depth=max_depth - 1,
                metrics=metrics,
                score_quiet_checks=score_quiet_checks,
                max_check_extensions=next_extensions,
            )
        finally:
            board.pop()

        if score >= beta:
            if metrics is not None:
                metrics.alpha_beta_cutoffs += 1
            return score

        alpha = max(alpha, score)

    return alpha
