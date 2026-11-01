import argparse
import csv
import statistics
from pathlib import Path

import chess

from chess_engine.engine import ChessEngine


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "benchmarks" / "search_ordering_v2"

POSITIONS = {
    "initial": chess.STARTING_FEN,
    "opening": (
        "r1bqkbnr/pppp1ppp/2n5/4p3/"
        "4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"
    ),
    "middlegame": (
        "r2q1rk1/ppp2ppp/2npbn2/3Np3/"
        "2B1P3/2N1BP2/PPPQ2PP/R3K2R b KQ - 1 10"
    ),
    "endgame": (
        "8/5pk1/6p1/3p4/3P4/5P2/5KPP/8 w - - 0 1"
    ),
}


def run_search(
    fen: str,
    depth: int,
    time_limit: float,
    score_quiet_checks: bool,
) -> dict:
    board = chess.Board(fen)

    if not board.is_valid():
        raise ValueError(f"FEN inválida: {fen}")

    engine = ChessEngine(
        max_depth=depth,
        score_quiet_checks=score_quiet_checks,
    )

    result = engine.best_move(
        board,
        time_limit=time_limit,
    )

    metrics = result.metrics
    total_nodes = metrics.get(
        "total_nodes",
        metrics.get("negamax_nodes", 0)
        + metrics.get("quiescence_nodes", 0),
    )

    return {
        "move": result.move.uci(),
        "score": result.score,
        "depth": result.depth,
        "status": result.status,
        "elapsed_s": round(result.elapsed, 6),
        "total_nodes": total_nodes,
        "negamax_nodes": metrics.get("negamax_nodes", 0),
        "quiescence_nodes": metrics.get(
            "quiescence_nodes", 0
        ),
        "alpha_beta_cutoffs": metrics.get(
            "alpha_beta_cutoffs", 0
        ),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0]),
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--depth",
        type=int,
        default=3,
    )
    parser.add_argument(
        "--time",
        type=float,
        default=3.0,
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=3,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    args = parser.parse_args()

    if args.depth < 1:
        parser.error("--depth deve ser >= 1.")

    if args.time <= 0:
        parser.error("--time deve ser positivo.")

    if args.repeats < 1:
        parser.error("--repeats deve ser >= 1.")

    rows = []

    print("\n=== Benchmark da Busca — Ordenação V2 ===")

    for position_name, fen in POSITIONS.items():
        for repetition in range(1, args.repeats + 1):
            modes = (
                [True, False]
                if repetition % 2
                else [False, True]
            )

            for quiet_checks in modes:
                strategy = (
                    "original"
                    if quiet_checks
                    else "optimized"
                )

                result = run_search(
                    fen=fen,
                    depth=args.depth,
                    time_limit=args.time,
                    score_quiet_checks=quiet_checks,
                )

                row = {
                    "position": position_name,
                    "repetition": repetition,
                    "strategy": strategy,
                    **result,
                }

                rows.append(row)

                print(
                    f"{position_name:12} "
                    f"{strategy:9} "
                    f"depth={result['depth']} "
                    f"nodes={result['total_nodes']} "
                    f"time={result['elapsed_s']:.3f}s "
                    f"move={result['move']} "
                    f"status={result['status']}"
                )

    summaries = []

    for position_name in POSITIONS:
        for strategy in ("original", "optimized"):
            selected = [
                row
                for row in rows
                if row["position"] == position_name
                and row["strategy"] == strategy
            ]

            summaries.append({
                "position": position_name,
                "strategy": strategy,
                "runs": len(selected),
                "median_elapsed_s": round(
                    statistics.median(
                        row["elapsed_s"]
                        for row in selected
                    ),
                    6,
                ),
                "median_total_nodes": statistics.median(
                    row["total_nodes"]
                    for row in selected
                ),
                "median_depth": statistics.median(
                    row["depth"]
                    for row in selected
                ),
                "completed_runs": sum(
                    row["status"] == "completed"
                    for row in selected
                ),
                "timeout_runs": sum(
                    row["status"] == "timeout"
                    for row in selected
                ),
                "fallback_runs": sum(
                    row["status"] == "fallback"
                    for row in selected
                ),
            })

    write_csv(
        args.output / "search_results.csv",
        rows,
    )

    write_csv(
        args.output / "summary.csv",
        summaries,
    )

    print(f"\nResultados em: {args.output}")


if __name__ == "__main__":
    main()
