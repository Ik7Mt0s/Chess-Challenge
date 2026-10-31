import argparse
import csv
import sys
from pathlib import Path
from statistics import median
from time import perf_counter

import chess

try:
    from chess_engine.engine import ChessEngine
    from chess_engine.evaluation.heuristic import HeuristicEvaluator
except ModuleNotFoundError:
    sys.path.insert(
        0,
        str(Path(__file__).resolve().parents[1] / "src"),
    )
    from chess_engine.engine import ChessEngine
    from chess_engine.evaluation.heuristic import HeuristicEvaluator

from chess_engine.evaluation.base import PositionEvaluator


class BaselineEvaluator(PositionEvaluator):
    """Cópia da avaliação material/centralização anterior ao passo 3."""

    PIECE_VALUES = {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 0,
    }
    CENTER_BONUS = {chess.KNIGHT: 8, chess.BISHOP: 4}
    PAWN_ADVANCE_BONUS = 5

    def evaluate(self, board: chess.Board) -> int:
        score = 0

        for piece_type, value in self.PIECE_VALUES.items():
            for color in (chess.WHITE, chess.BLACK):
                sign = 1 if color == chess.WHITE else -1

                for square in board.pieces(piece_type, color):
                    score += sign * value
                    score += sign * self._positional_score(
                        piece_type,
                        square,
                        color,
                    )

        return score

    def _positional_score(
        self,
        piece_type: chess.PieceType,
        square: chess.Square,
        color: chess.Color,
    ) -> int:
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        score = 0

        if piece_type in self.CENTER_BONUS:
            distance = (
                min(abs(file - 3), abs(file - 4))
                + min(abs(rank - 3), abs(rank - 4))
            )
            score += (6 - distance) * self.CENTER_BONUS[piece_type]

        if piece_type == chess.PAWN:
            advancement = rank - 1 if color == chess.WHITE else 6 - rank
            score += max(0, advancement) * self.PAWN_ADVANCE_BONUS

        return score


POSITIONS = (
    ("Abertura", chess.STARTING_FEN),
    (
        "Meio-jogo",
        "r1bqk2r/pppp1ppp/2n2n2/4p3/2B1P3/2N2N2/"
        "PPPP1PPP/R1BQK2R w KQkq - 4 4",
    ),
    (
        "Final",
        "8/5pk1/6p1/7p/7P/6P1/5PK1/8 w - - 0 1",
    ),
    (
        "Peão passado",
        "8/8/4P3/5k2/8/8/5K2/8 w - - 0 1",
    ),
)


def benchmark(
    depth: int,
    time_limit: float,
    evaluation_repetitions: int,
    repetitions: int,
    output: Path,
) -> list[dict]:
    evaluators = (
        ("baseline", BaselineEvaluator()),
        ("passo_3", HeuristicEvaluator()),
    )
    rows = []

    for position_name, fen in POSITIONS:
        board = chess.Board(fen)

        if not board.is_valid():
            raise ValueError(f"Posição inválida no benchmark: {position_name}")

        for evaluator_name, evaluator in evaluators:
            for _ in range(min(20, evaluation_repetitions)):
                evaluator.evaluate(board)

            evaluation_times = []
            results = []

            for _ in range(repetitions):
                evaluation_start = perf_counter()
                for _ in range(evaluation_repetitions):
                    evaluator.evaluate(board)
                evaluation_times.append(
                    perf_counter() - evaluation_start
                )

                engine = ChessEngine(
                    evaluator=evaluator,
                    max_depth=depth,
                    use_transposition_table=False,
                    use_advanced_ordering=True,
                )
                results.append(
                    engine.best_move(board, time_limit=time_limit)
                )

            evaluation_seconds = median(evaluation_times)
            search_seconds = median(result.elapsed for result in results)
            total_nodes = median(
                result.metrics.get("total_nodes", 0)
                for result in results
            )
            quiescence_nodes = median(
                result.metrics.get("quiescence_nodes", 0)
                for result in results
            )
            scores = [result.score for result in results]
            depths = [result.depth for result in results]
            result = results[0]
            distinct_moves = len({item.move for item in results})

            row = {
                "position": position_name,
                "evaluator": evaluator_name,
                "static_score_cp_white": evaluator.evaluate(board),
                "static_evaluation_repetitions": evaluation_repetitions,
                "benchmark_repetitions": repetitions,
                "static_evaluation_seconds": round(
                    evaluation_seconds,
                    4,
                ),
                "static_evaluations_per_second": round(
                    evaluation_repetitions / evaluation_seconds,
                    1,
                ),
                "move_uci": result.move.uci(),
                "median_search_score_cp_side_to_move": median(scores),
                "distinct_scores_across_repetitions": len(set(scores)),
                "distinct_moves_across_repetitions": distinct_moves,
                "min_completed_depth": min(depths),
                "max_completed_depth": max(depths),
                "status": "/".join(sorted({item.status for item in results})),
                "median_elapsed_seconds": round(search_seconds, 4),
                "median_total_nodes": int(total_nodes),
                "median_quiescence_nodes": int(quiescence_nodes),
            }
            rows.append(row)
            print(
                f"{position_name:14} | {evaluator_name:8} | "
                f"lance={row['move_uci']:5} | "
                f"estática={row['static_score_cp_white']:+5} cp | "
                f"avaliações/s={row['static_evaluations_per_second']:>7} | "
                f"prof={row['min_completed_depth']}-"
                f"{row['max_completed_depth']} | "
                f"mediana={row['median_elapsed_seconds']:.3f}s | "
                f"nós={row['median_total_nodes']} | "
                f"lances distintos={distinct_moves}"
            )

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nBenchmark salvo em: {output}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compara duas versões da avaliação do motor."
    )
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--time", type=float, default=10.0)
    parser.add_argument("--evaluation-repetitions", type=int, default=1000)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmarks/evaluation_benchmark.csv"),
    )
    args = parser.parse_args()

    if args.depth < 1:
        parser.error("--depth deve ser pelo menos 1")
    if args.time <= 0:
        parser.error("--time deve ser maior que zero")
    if args.evaluation_repetitions < 1:
        parser.error("--evaluation-repetitions deve ser positivo")
    if args.repetitions < 3:
        parser.error("--repetitions deve ser pelo menos 3")

    benchmark(
        args.depth,
        args.time,
        args.evaluation_repetitions,
        args.repetitions,
        args.output,
    )


if __name__ == "__main__":
    main()
