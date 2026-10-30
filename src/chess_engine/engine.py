from dataclasses import dataclass, field

import chess

from chess_engine.evaluation.base import PositionEvaluator
from chess_engine.evaluation.heuristic import HeuristicEvaluator
from chess_engine.search.metrics import SearchMetrics
from chess_engine.search.move_ordering import (
    MoveOrderingHeuristics,
    order_moves,
)
from chess_engine.search.negamax import (
    INFINITY,
    MATE_SCORE,
    negamax,
)
from chess_engine.search.transposition import TranspositionTable
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

    status: str = "completed"
    metrics: dict[str, int] = field(default_factory=dict)
    cache: dict[str, int | float] = field(default_factory=dict)


class ChessEngine:
    def __init__(
        self,
        evaluator: PositionEvaluator | None = None,
        max_depth: int = 3,
        use_transposition_table: bool = True,
        tt_max_entries: int = 20_000,
        use_advanced_ordering: bool = True,
    ):
        if max_depth < 1:
            raise ValueError(
                "A profundidade deve ser pelo menos 1."
            )

        self.evaluator = (
            evaluator
            if evaluator is not None
            else HeuristicEvaluator()
        )

        self.max_depth = max_depth
        self.use_advanced_ordering = use_advanced_ordering

        self.transposition_table = (
            TranspositionTable(max_entries=tt_max_entries)
            if use_transposition_table
            else None
        )

    def clear_cache(self) -> None:
        if self.transposition_table is not None:
            self.transposition_table.clear()

    def cache_stats(self) -> dict[str, int | float]:
        if self.transposition_table is None:
            return {
                "entries": 0,
                "hits": 0,
                "misses": 0,
                "stores": 0,
                "hit_rate": 0.0,
            }

        return self.transposition_table.stats()

    def best_move(
        self,
        board: chess.Board,
        time_limit: float = 2.0,
    ) -> SearchResult:
        if board.is_game_over(claim_draw=True):
            raise ValueError(
                "A partida já terminou."
            )

        timer = TimeManager(time_limit)
        metrics = SearchMetrics()

        ordering_heuristics = (
            MoveOrderingHeuristics()
            if self.use_advanced_ordering
            else None
        )

        cache_before = self.cache_stats()
        legal_moves = order_moves(board)

        if not legal_moves:
            raise ValueError(
                "Não existem movimentos legais."
            )

        best_move = legal_moves[0]
        best_score = 0
        completed_depth = 0
        timed_out = False

        def build_result(status: str) -> SearchResult:
            cache_after = self.cache_stats()

            hits = int(
                cache_after["hits"] - cache_before["hits"]
            )
            misses = int(
                cache_after["misses"] - cache_before["misses"]
            )
            stores = int(
                cache_after["stores"] - cache_before["stores"]
            )

            total = hits + misses

            cache_metrics = {
                "entries": int(cache_after["entries"]),
                "hits": hits,
                "misses": misses,
                "stores": stores,
                "hit_rate": (
                    hits / total if total else 0.0
                ),
            }

            return SearchResult(
                move=best_move,
                score=best_score,
                depth=completed_depth,
                elapsed=timer.elapsed(),
                status=status,
                metrics=metrics.as_dict(),
                cache=cache_metrics,
            )

        if len(legal_moves) == 1:
            return build_result("forced")

        for depth in range(1, self.max_depth + 1):
            iteration_move = None
            iteration_score = -INFINITY

            alpha = -INFINITY
            beta = INFINITY

            ordered = order_moves(
                board,
                legal_moves,
                ply=0,
                heuristics=ordering_heuristics,
                tt_move=best_move,
            )

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
                            transposition_table=(
                                self.transposition_table
                            ),
                            metrics=metrics,
                            ordering_heuristics=ordering_heuristics,
                        )
                    finally:
                        board.pop()

                    if score > iteration_score:
                        iteration_score = score
                        iteration_move = move

                    alpha = max(alpha, score)

            except SearchTimeout:
                timed_out = True
                break

            if iteration_move is not None:
                best_move = iteration_move
                best_score = iteration_score
                completed_depth = depth

            if best_score >= MATE_SCORE - 1000:
                break

        if completed_depth == 0:
            return build_result("fallback")

        if timed_out:
            return build_result("timeout")

        return build_result("completed")
