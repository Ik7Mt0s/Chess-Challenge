import chess

from chess_engine.evaluation.base import PositionEvaluator
from chess_engine.search.metrics import SearchMetrics
from chess_engine.search.move_ordering import (
    MoveOrderingHeuristics,
    order_moves,
)
from chess_engine.search.quiescence import quiescence
from chess_engine.search.transposition import (
    BoundType,
    TranspositionTable,
)
from chess_engine.utils.time_manager import TimeManager


MATE_SCORE = 100_000
INFINITY = 1_000_000


def negamax(
    board: chess.Board,
    depth: int,
    alpha: int,
    beta: int,
    evaluator: PositionEvaluator,
    timer: TimeManager,
    ply: int = 0,
    transposition_table: TranspositionTable | None = None,
    metrics: SearchMetrics | None = None,
    ordering_heuristics: MoveOrderingHeuristics | None = None,
) -> int:
    timer.check()

    if metrics is not None:
        metrics.negamax_nodes += 1

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

    if depth <= 0:
        return quiescence(
            board=board,
            alpha=alpha,
            beta=beta,
            evaluator=evaluator,
            timer=timer,
            ply=ply,
            metrics=metrics,
        )

    original_alpha = alpha
    original_beta = beta
    cached_move = None

    if transposition_table is not None:
        entry = transposition_table.get(
            board,
            ply=ply,
        )

        if entry is not None:
            cached_move = entry.best_move

            if entry.depth >= depth:
                if entry.bound == BoundType.EXACT:
                    return entry.score

                if entry.bound == BoundType.LOWER:
                    alpha = max(alpha, entry.score)

                elif entry.bound == BoundType.UPPER:
                    beta = min(beta, entry.score)

                if alpha >= beta:
                    if metrics is not None:
                        metrics.alpha_beta_cutoffs += 1

                    return entry.score

    best_score = -INFINITY
    best_move = None

    moves = order_moves(
        board,
        ply=ply,
        heuristics=ordering_heuristics,
        tt_move=cached_move,
    )

    for move in moves:
        timer.check()
        board.push(move)

        try:
            score = -negamax(
                board=board,
                depth=depth - 1,
                alpha=-beta,
                beta=-alpha,
                evaluator=evaluator,
                timer=timer,
                ply=ply + 1,
                transposition_table=transposition_table,
                metrics=metrics,
                ordering_heuristics=ordering_heuristics,
            )
        finally:
            board.pop()

        if score > best_score:
            best_score = score
            best_move = move

        alpha = max(alpha, score)

        if alpha >= beta:
            if metrics is not None:
                metrics.alpha_beta_cutoffs += 1

            if ordering_heuristics is not None:
                ordering_heuristics.record_cutoff(
                    board=board,
                    move=move,
                    ply=ply,
                    depth=depth,
                )

            break

    if transposition_table is not None:
        if best_score <= original_alpha:
            bound = BoundType.UPPER
        elif best_score >= original_beta:
            bound = BoundType.LOWER
        else:
            bound = BoundType.EXACT

        transposition_table.store(
            board=board,
            depth=depth,
            score=best_score,
            bound=bound,
            best_move=best_move,
            ply=ply,
        )

    return best_score
