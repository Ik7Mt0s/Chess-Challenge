import argparse
import cProfile
import csv
import pstats
import time
from pathlib import Path

import chess

from chess_engine.engine import ChessEngine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "benchmarks" / "profiling"

POSITIONS = {
    "initial": chess.STARTING_FEN,
    "opening": (
        "rnbqkb1r/pp2pppp/2pp1n2/8/2N5/2N5/"
        "PPPPPPPP/R1BQKB1R b KQkq - 3 4"
    ),
    "middlegame": (
        "1rb3rk/p1q2ppp/2p5/2n1b3/Pp4PP/"
        "7Q/1PP1PPB1/R2NK2R w KQ - 4 17"
    ),
    "endgame": (
        "8/5pk1/4p1p1/8/3P4/4P1P1/"
        "5PK1/8 w - - 0 1"
    ),
}

def parse_args():
    parser = argparse.ArgumentParser(
        description="Diagnóstico de desempenho do ChessEngine."
    )

    parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Profundidade máxima da busca.",
    )

    parser.add_argument(
        "--time",
        type=float,
        default=3.0,
        help="Tempo máximo por busca, em segundos.",
    )

    parser.add_argument(
        "--repeats",
        type=int,
        default=3,
        help="Quantidade de repetições sem profiling.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Diretório para salvar os resultados.",
    )

    return parser.parse_args()


def validate_positions():
    for name, fen in POSITIONS.items():
        board = chess.Board(fen)

        if not board.is_valid():
            raise ValueError(
                f"Posição inválida para profiling: {name}"
            )

        if board.is_game_over(claim_draw=True):
            raise ValueError(
                f"A posição {name} já está encerrada."
            )


def run_engine(
    fen: str,
    depth: int,
    time_limit: float,
    profile: bool = False,
):
    board = chess.Board(fen)

    engine = ChessEngine(
        max_depth=depth,
    )

    profiler = cProfile.Profile() if profile else None

    started = time.perf_counter()

    if profiler is not None:
        profiler.enable()

    try:
        result = engine.best_move(
            board,
            time_limit=time_limit,
        )
    finally:
        if profiler is not None:
            profiler.disable()

    wall_time = time.perf_counter() - started

    return result, wall_time, profiler


def profile_functions(
    profiler: cProfile.Profile,
    limit: int = 25,
) -> list[dict]:
    stats = pstats.Stats(profiler)
    rows = []

    for (
        filename,
        line,
        function,
    ), values in stats.stats.items():
        primitive_calls, total_calls, own_time, cumulative_time, _ = values

        rows.append(
            {
                "function": function,
                "file": Path(filename).name,
                "line": line,
                "calls": total_calls,
                "primitive_calls": primitive_calls,
                "own_seconds": round(own_time, 6),
                "cumulative_seconds": round(cumulative_time, 6),
            }
        )

    rows.sort(
        key=lambda row: row["cumulative_seconds"],
        reverse=True,
    )

    return rows[:limit]


def save_csv(
    path: Path,
    rows: list[dict],
) -> None:
    if not rows:
        return

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
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


def main():
    args = parse_args()

    if args.depth < 1:
        raise ValueError(
            "--depth deve ser pelo menos 1."
        )

    if args.time <= 0:
        raise ValueError(
            "--time deve ser positivo."
        )

    if args.repeats < 1:
        raise ValueError(
            "--repeats deve ser pelo menos 1."
        )

    validate_positions()

    args.output.mkdir(
        parents=True,
        exist_ok=True,
    )

    benchmark_rows = []
    function_rows = []

    print("\n=== Chess Challenge III — Profiling ===")
    print(f"Profundidade máxima: {args.depth}")
    print(f"Tempo por busca: {args.time:.2f}s")
    print(f"Repetições: {args.repeats}")
    print(f"Saída: {args.output}\n")

    for name, fen in POSITIONS.items():
        print(f"--- {name} ---")

        for repetition in range(1, args.repeats + 1):
            result, wall_time, _ = run_engine(
                fen=fen,
                depth=args.depth,
                time_limit=args.time,
            )

            nodes = result.metrics.get(
                "total_nodes",
                0,
            )

            qnodes = result.metrics.get(
                "quiescence_nodes",
                0,
            )

            nps = (
                nodes / wall_time
                if wall_time > 0
                else 0
            )

            quiescence_percentage = (
                100 * qnodes / nodes
                if nodes > 0
                else 0
            )

            row = {
                "position": name,
                "repetition": repetition,
                "depth_limit": args.depth,
                "time_limit": args.time,
                "move": result.move.uci(),
                "score_cp": result.score,
                "completed_depth": result.depth,
                "status": result.status,
                "elapsed_seconds": round(
                    wall_time,
                    6,
                ),
                "reported_seconds": round(
                    result.elapsed,
                    6,
                ),
                "negamax_nodes": result.metrics.get(
                    "negamax_nodes",
                    0,
                ),
                "quiescence_nodes": qnodes,
                "total_nodes": nodes,
                "quiescence_percentage": round(
                    quiescence_percentage,
                    2,
                ),
                "nodes_per_second": round(
                    nps,
                    2,
                ),
                "alpha_beta_cutoffs": result.metrics.get(
                    "alpha_beta_cutoffs",
                    0,
                ),
                "tt_hits": result.cache.get(
                    "hits",
                    0,
                ),
                "tt_misses": result.cache.get(
                    "misses",
                    0,
                ),
                "tt_hit_rate": result.cache.get(
                    "hit_rate",
                    0,
                ),
            }

            benchmark_rows.append(row)

            print(
                f"  Execução {repetition}: "
                f"lance={row['move']} "
                f"prof={row['completed_depth']} "
                f"status={row['status']} "
                f"nós={nodes} "
                f"NPS={nps:.0f} "
                f"quiescência={quiescence_percentage:.1f}%"
            )

        print("  Executando cProfile...")

        result, wall_time, profiler = run_engine(
            fen=fen,
            depth=args.depth,
            time_limit=args.time,
            profile=True,
        )

        profiler.dump_stats(
            str(
                args.output
                / f"profile_{name}.prof"
            )
        )

        for function_row in profile_functions(
            profiler
        ):
            function_rows.append(
                {
                    "position": name,
                    **function_row,
                }
            )

        print(
            f"  Profiling concluído em "
            f"{wall_time:.2f}s "
            f"(profundidade {result.depth}).\n"
        )

    benchmark_path = (
        args.output / "benchmark_results.csv"
    )

    function_path = (
        args.output / "function_costs.csv"
    )

    save_csv(
        benchmark_path,
        benchmark_rows,
    )

    save_csv(
        function_path,
        function_rows,
    )

    print("=== Diagnóstico concluído ===")
    print("Arquivos gerados:")
    print(f"  {benchmark_path}")
    print(f"  {function_path}")
    print("  profile_*.prof")


if __name__ == "__main__":
    main()
