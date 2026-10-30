import chess

from chess_engine.evaluation.base import PositionEvaluator
from chess_engine.search.move_ordering import order_moves
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
) -> int:
    timer.check()

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
        score = evaluator.evaluate(board)
        return score if board.turn == chess.WHITE else -score

    best_score = -INFINITY

    for move in order_moves(board):
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
            )
        finally:
            board.pop()

        best_score = max(best_score, score)
        alpha = max(alpha, score)

        if alpha >= beta:
            break

    return best_score