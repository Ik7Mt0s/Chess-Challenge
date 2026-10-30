from dataclasses import dataclass

import chess

from chess_engine.evaluation.base import PositionEvaluator
from chess_engine.evaluation.heuristic import HeuristicEvaluator
from chess_engine.search.move_ordering import order_moves
from chess_engine.search.negamax import (
    INFINITY,
    MATE_SCORE,
    negamax,
)
from chess_engine.utils.time_manager import (
    SearchTimeout,
    TimeManager,
)


@dataclass(frozen=True)
class SearchResult:
    move: chess.Move
    score: int
    depth: int
    elapsed: float


class ChessEngine:
    def __init__(
        self,
        evaluator: PositionEvaluator | None = None,
        max_depth: int = 3,
    ):
        if max_depth < 1:
            raise ValueError("A profundidade deve ser pelo menos 1.")

        self.evaluator = evaluator or HeuristicEvaluator()
        self.max_depth = max_depth

    def best_move(
        self,
        board: chess.Board,
        time_limit: float = 2.0,
    ) -> SearchResult:
        if board.is_game_over(claim_draw=True):
            raise ValueError("A partida já terminou.")

        timer = TimeManager(time_limit)
        legal_moves = order_moves(board)

        if not legal_moves:
            raise ValueError("Não existem movimentos legais.")

        # Sempre existe um lance legal de reserva.
        best_move = legal_moves[0]
        best_score = 0
        completed_depth = 0

        if len(legal_moves) == 1:
            return SearchResult(
                move=best_move,
                score=0,
                depth=0,
                elapsed=timer.elapsed(),
            )

        for depth in range(1, self.max_depth + 1):
            iteration_move = None
            iteration_score = -INFINITY
            alpha = -INFINITY
            beta = INFINITY

            # O melhor lance anterior é pesquisado primeiro.
            ordered = [best_move] + [
                move for move in legal_moves if move != best_move
            ]

            try:
                for move in ordered:
                    timer.check()

                    board.push(move)

                    try:
                        score = -negamax(
                            board=board,
                            depth=depth - 1,
                            alpha=-beta,
                            beta=-alpha,
                            evaluator=self.evaluator,
                            timer=timer,
                            ply=1,
                        )
                    finally:
                        board.pop()

                    if score > iteration_score:
                        iteration_score = score
                        iteration_move = move

                    alpha = max(alpha, score)

            except SearchTimeout:
                break

            if iteration_move is not None:
                best_move = iteration_move
                best_score = iteration_score
                completed_depth = depth

            if best_score >= MATE_SCORE - 1000:
                break

        return SearchResult(
            move=best_move,
            score=best_score,
            depth=completed_depth,
            elapsed=timer.elapsed(),
        )