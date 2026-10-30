
import chess

from chess_engine.evaluation.base import PositionEvaluator
from chess_engine.search.metrics import SearchMetrics
from chess_engine.search.move_ordering import order_moves
from chess_engine.utils.time_manager import TimeManager


MATE_SCORE = 100_000


def quiescence(
    board: chess.Board,
    alpha: int,
    beta: int,
    evaluator: PositionEvaluator,
    timer: TimeManager,
    ply: int = 0,
    max_depth: int = 8,
    metrics: SearchMetrics | None = None,
) -> int:
    """
    Busca de quiescência com poda Alfa-Beta.

    Analisa capturas e promoções em posições normais.
    Quando há xeque, pesquisa todas as respostas legais.

    As métricas são opcionais para preservar
    compatibilidade com as chamadas anteriores.
    """

    timer.check()

    if metrics is not None:
        metrics.quiescence_nodes += 1

    if board.is_checkmate():
        return -MATE_SCORE + ply

    if (
        board.is_stalemate()
        or board.is_insufficient_material()
        or board.is_seventyfive_moves()
        or board.is_fivefold_repetition()
        or board.can_claim_draw()
    ):
        return 0

    in_check = board.is_check()

    if not in_check:
        static_score = evaluator.evaluate(board)

        if board.turn == chess.BLACK:
            static_score = -static_score

        if static_score >= beta:
            if metrics is not None:
                metrics.alpha_beta_cutoffs += 1

            return static_score

        alpha = max(alpha, static_score)

        if max_depth <= 0:
            return alpha

        moves = [
            move
            for move in board.legal_moves
            if board.is_capture(move) or move.promotion
        ]
    else:
        moves = list(board.legal_moves)

    if not moves:
        return alpha

    for move in order_moves(board, moves):
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
            )
        finally:
            board.pop()

        if score >= beta:
            if metrics is not None:
                metrics.alpha_beta_cutoffs += 1

            return score

        alpha = max(alpha, score)

    return alpha
