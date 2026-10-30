
import argparse
import csv
from pathlib import Path
from statistics import median

import chess

from chess_engine.engine import ChessEngine


POSITIONS = [
    (
        "Abertura",
        chess.STARTING_FEN,
    ),
    (
        "Meio-jogo",
        "r1bqk2r/pppp1ppp/2n2n2/4p3/"
        "2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 4 4",
    ),
    (
        "Final",
        "8/5pk1/6p1/7p/7P/6P1/5PK1/8 w - - 0 1",
    ),
]


def run_benchmark(
    depth: int,
    time_limit: float,
    repetitions: int,
    output: Path,
) -> None:
    rows = []

    for name, fen in POSITIONS:
        print(f"\n=== {name} ===")

        for repetition in range(1, repetitions + 1):
            # Alterna a ordem para reduzir o viés
            # de executar sempre a mesma versão primeiro.
            configurations = (
                [False, True]
                if repetition % 2
                else [True, False]
            )

            for advanced in configurations:
                board = chess.Board(fen)

                engine = ChessEngine(
                    max_depth=depth,
                    use_transposition_table=True,
                    use_advanced_ordering=advanced,
                )

                result = engine.best_move(
                    board,
                    time_limit=time_limit,
                )

                row = {
                    "position": name,
                    "repetition": repetition,
                    "advanced_ordering": advanced,
                    "move": result.move.uci(),
                    "score": result.score,
                    "depth": result.depth,
                    "status": result.status,
                    "elapsed": round(result.elapsed, 4),
                    "total_nodes": result.metrics["total_nodes"],
                    "negamax_nodes": result.metrics["negamax_nodes"],
                    "quiescence_nodes": result.metrics[
                        "quiescence_nodes"
                    ],
                    "alpha_beta_cutoffs": result.metrics[
                        "alpha_beta_cutoffs"
                    ],
                    "cache_hits": result.cache["hits"],
                }

                rows.append(row)

                label = (
                    "AVANCADA"
                    if advanced
                    else "ORIGINAL"
                )

                print(
                    f"Rodada {repetition} | "
                    f"{label:9} | "
                    f"lance={row['move']:5} | "
                    f"prof={row['depth']} | "
                    f"status={row['status']:9} | "
                    f"tempo={row['elapsed']:.3f}s | "
                    f"nós={row['total_nodes']}"
                )

        print("\nResumo (medianas):")

        for advanced in (False, True):
            group = [
                row
                for row in rows
                if row["position"] == name
                and row["advanced_ordering"] == advanced
            ]

            print(
                f"{'AVANCADA' if advanced else 'ORIGINAL':9} | "
                f"tempo={median(row['elapsed'] for row in group):.3f}s | "
                f"nós={median(row['total_nodes'] for row in group):.0f}"
            )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nResultados salvos em: {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark da ordenação de movimentos."
    )

    parser.add_argument(
        "--depth",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--time",
        type=float,
        default=30.0,
    )

    parser.add_argument(
        "--repetitions",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "benchmarks/ordering_benchmark.csv"
        ),
    )

    args = parser.parse_args()

    if args.depth < 1:
        parser.error("--depth deve ser pelo menos 1.")

    if args.time <= 0:
        parser.error("--time deve ser positivo.")

    if args.repetitions < 1:
        parser.error(
            "--repetitions deve ser pelo menos 1."
        )

    run_benchmark(
        depth=args.depth,
        time_limit=args.time,
        repetitions=args.repetitions,
        output=args.output,
    )


if __name__ == "__main__":
    main()
