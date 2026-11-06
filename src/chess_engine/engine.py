
from dataclasses import dataclass, field

import chess

from chess_engine.evaluation.base import PositionEvaluator
from chess_engine.evaluation.neural import HybridEvaluator
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
    metrics: dict[str, int | float] = field(default_factory=dict)
    cache: dict[str, int | float] = field(default_factory=dict)


class ChessEngine:
    MAX_SEARCH_DEPTH = 64

    # Parada antecipada conservadora.
    EARLY_STOP_MIN_DEPTH = 4
    EARLY_STOP_STABLE_DEPTHS = 3
    EARLY_STOP_SCORE_TOLERANCE = 25
    EARLY_STOP_MIN_TIME_FRACTION = 0.35

    def __init__(
        self,
        evaluator: PositionEvaluator | None = None,
        max_depth: int = 3,
        use_transposition_table: bool = True,
        tt_max_entries: int = 20_000,
        use_advanced_ordering: bool = True,
        score_quiet_checks: bool = True,
        use_full_time: bool = False,
        early_stop_enabled: bool = False,
    ):
        if max_depth < 1:
            raise ValueError(
                "A profundidade deve ser pelo menos 1."
            )

        self.evaluator = (
            evaluator
            if evaluator is not None
            else HybridEvaluator()
        )

        self.max_depth = max_depth
        self.use_full_time = use_full_time

        # A parada antecipada so e utilizada no modo
        # de busca por tempo e quando ativada.
        self.early_stop_enabled = early_stop_enabled

        self.use_advanced_ordering = use_advanced_ordering
        self.score_quiet_checks = score_quiet_checks

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
                "A partida ja terminou."
            )

        begin_search = getattr(
            self.evaluator,
            "begin_search",
            None,
        )

        if callable(begin_search):
            begin_search()

        timer = TimeManager(time_limit)
        metrics = SearchMetrics()

        ordering_heuristics = (
            MoveOrderingHeuristics()
            if self.use_advanced_ordering
            else None
        )

        cache_before = self.cache_stats()

        legal_moves = order_moves(
            board,
            score_quiet_checks=self.score_quiet_checks,
        )

        if not legal_moves:
            raise ValueError(
                "Nao existem movimentos legais."
            )

        # Movimento de reserva caso o tempo acabe
        # antes de qualquer profundidade concluida.
        best_move = legal_moves[0]
        best_score = 0
        completed_depth = 0
        timed_out = False
        early_stopped = False

        # Historico da estabilidade entre profundidades.
        previous_completed_move = None
        previous_completed_score = None
        stable_depths = 0

        # Nao encerramos uma busca antecipadamente
        # enquanto o jogador estiver em xeque.
        root_in_check = board.is_check()

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

            elapsed = timer.elapsed()
            search_metrics = metrics.as_dict().copy()

            negamax_nodes = int(
                search_metrics.get("negamax_nodes", 0)
            )

            quiescence_nodes = int(
                search_metrics.get("quiescence_nodes", 0)
            )

            total_nodes = (
                negamax_nodes + quiescence_nodes
            )

            search_metrics["total_nodes"] = total_nodes

            search_metrics["nps"] = (
                total_nodes / elapsed
                if elapsed > 0
                else 0.0
            )

            search_metrics["early_stopped"] = int(
                early_stopped
            )

            search_metrics["stable_depths"] = stable_depths

            inference_stats = getattr(
                self.evaluator,
                "inference_stats",
                None,
            )

            if callable(inference_stats):
                search_metrics.update(inference_stats())

            return SearchResult(
                move=best_move,
                score=best_score,
                depth=completed_depth,
                elapsed=elapsed,
                status=status,
                metrics=search_metrics,
                cache=cache_metrics,
            )

        # Apenas um lance legal: nao precisamos pesquisar.
        if len(legal_moves) == 1:
            return build_result("forced")

        # Com use_full_time, max_depth nao limita
        # a profundidade maxima.
        depth_limit = (
            max(self.max_depth, self.MAX_SEARCH_DEPTH)
            if self.use_full_time
            else self.max_depth
        )

        for depth in range(1, depth_limit + 1):
            try:
                timer.check()
            except SearchTimeout:
                timed_out = True
                break

            iteration_move = None
            iteration_score = -INFINITY

            alpha = -INFINITY
            beta = INFINITY

            # Melhor lance anterior tem prioridade
            # na nova iteracao.
            ordered = order_moves(
                board,
                legal_moves,
                ply=0,
                heuristics=ordering_heuristics,
                tt_move=best_move,
                score_quiet_checks=self.score_quiet_checks,
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
                            score_quiet_checks=self.score_quiet_checks,
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

            # Nunca substituimos a melhor jogada
            # com uma iteracao incompleta.
            if iteration_move is None:
                continue

            best_move = iteration_move
            best_score = iteration_score
            completed_depth = depth

            # Verifica se a jogada e a avaliacao
            # permaneceram estaveis entre iteracoes.
            same_move = (
                previous_completed_move == best_move
            )

            similar_score = (
                previous_completed_score is not None
                and abs(
                    previous_completed_score - best_score
                ) <= self.EARLY_STOP_SCORE_TOLERANCE
            )

            if same_move and similar_score:
                stable_depths += 1
            else:
                stable_depths = 1

            previous_completed_move = best_move
            previous_completed_score = best_score

            # Mate suficientemente proximo:
            # comportamento ja existente.
            if best_score >= MATE_SCORE - 1000:
                break

            # Parada antecipada somente se:
            #
            # - A busca e controlada por tempo;
            # - O recurso esta habilitado;
            # - Uma profundidade segura foi concluida;
            # - A jogada ficou estavel em tres
            #   profundidades consecutivas;
            # - A avaliacao nao oscilou muito;
            # - Pelo menos 35% do tempo foi utilizado;
            # - O jogador nao esta em xeque.
            #
            # Isso e uma heuristica de economia de
            # tempo, nao uma prova de jogada otima.
            can_stop_early = (
                self.use_full_time
                and self.early_stop_enabled
                and not root_in_check
                and completed_depth >= self.EARLY_STOP_MIN_DEPTH
                and stable_depths >= self.EARLY_STOP_STABLE_DEPTHS
                and timer.elapsed()
                >= (
                    time_limit
                    * self.EARLY_STOP_MIN_TIME_FRACTION
                )
            )

            if can_stop_early:
                early_stopped = True
                break

        if completed_depth == 0:
            return build_result("fallback")

        if timed_out:
            return build_result("timeout")

        return build_result("completed")
