
import argparse
import csv
from pathlib import Path

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


def benchmark(
    depth: int,
    time_limit: float,
    output: Path,
) -> list[dict]:
    rows = []

    for name, fen in POSITIONS:
        print(f"\n=== {name} ===")

        for use_cache in (False, True):
            board = chess.Board(fen)

            engine = ChessEngine(
                max_depth=depth,
                use_transposition_table=use_cache,
            )

            result = engine.best_move(
                board,
                time_limit=time_limit,
            )

            metrics = result.metrics
            cache = result.cache

            row = {
                "position": name,
                "cache_enabled": use_cache,
                "move": result.move.uci(),
                "score": result.score,
                "depth": result.depth,
                "status": result.status,
                "elapsed": round(result.elapsed, 4),
                "negamax_nodes": metrics["negamax_nodes"],
                "quiescence_nodes": metrics["quiescence_nodes"],
                "total_nodes": metrics["total_nodes"],
                "alpha_beta_cutoffs": metrics[
                    "alpha_beta_cutoffs"
                ],
                "cache_hits": cache["hits"],
                "cache_misses": cache["misses"],
                "cache_stores": cache["stores"],
                "cache_hit_rate": round(
                    cache["hit_rate"] * 100, 2
                ),
            }

            rows.append(row)

            label = (
                "COM CACHE"
                if use_cache
                else "SEM CACHE"
            )

            print(
                f"{label:10} | "
                f"lance={row['move']:5} | "
                f"prof={row['depth']} | "
                f"status={row['status']:9} | "
                f"tempo={row['elapsed']:.3f}s | "
                f"nós={row['total_nodes']} | "
                f"hits={row['cache_hits']}"
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

    print(f"\nBenchmark salvo em: {output}")

    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark do motor de xadrez."
    )

    parser.add_argument(
        "--depth",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--time",
        type=float,
        default=15.0,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmarks/search_benchmark.csv"),
    )

    args = parser.parse_args()

    if args.depth < 1:
        parser.error(
            "--depth deve ser pelo menos 1."
        )

    if args.time <= 0:
        parser.error(
            "--time deve ser maior que zero."
        )

    benchmark(
        depth=args.depth,
        time_limit=args.time,
        output=args.output,
    )


if __name__ == "__main__":
    main()