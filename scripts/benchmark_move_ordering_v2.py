
import argparse
import csv
import statistics
import time
from pathlib import Path

import chess
import chess.pgn

from chess_engine.search.move_ordering import order_moves


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = ROOT / "benchmarks" / "stockfish_matches"
DEFAULT_OUTPUT = ROOT / "benchmarks" / "move_ordering_v2"


def collect_positions(
    directory: Path,
    sample_every: int,
    max_positions: int,
) -> list[tuple[str, int, chess.Board]]:
    if sample_every < 1:
        raise ValueError("sample_every deve ser >= 1.")

    if max_positions < 1:
        raise ValueError("max_positions deve ser >= 1.")

    files = sorted(directory.rglob("*.pgn"))
    if not files:
        raise FileNotFoundError(
            f"Nenhum PGN encontrado em {directory}"
        )

    positions = []

    for path in files:
        with path.open("r", encoding="utf-8-sig") as file:
            while True:
                game = chess.pgn.read_game(file)
                if game is None:
                    break

                if game.errors:
                    raise ValueError(
                        f"PGN inválido: {path}: {game.errors}"
                    )

                board = game.board()

                for ply, move in enumerate(
                    game.mainline_moves(),
                    start=1,
                ):
                    board.push(move)

                    if ply % sample_every != 0:
                        continue

                    if board.is_game_over():
                        continue

                    positions.append(
                        (
                            path.name,
                            ply,
                            board.copy(stack=True),
                        )
                    )

                    if len(positions) >= max_positions:
                        return positions

    return positions


def benchmark_position(
    board: chess.Board,
    repeats: int,
) -> dict:
    if repeats < 1:
        raise ValueError("repeats deve ser >= 1.")

    moves = list(board.legal_moves)
    original_fen = board.fen()
    original_stack = list(board.move_stack)

    results = {}

    for name, quiet_checks in (
        ("original", True),
        ("optimized", False),
    ):
        times = []
        ordered = None

        for _ in range(repeats):
            start = time.perf_counter_ns()

            current = order_moves(
                board,
                moves,
                score_quiet_checks=quiet_checks,
            )

            elapsed = time.perf_counter_ns() - start

            if ordered is not None:
                assert current == ordered

            ordered = current
            times.append(elapsed / 1000)

        results[name] = {
            "ordered": ordered,
            "median_us": statistics.median(times),
        }

    if board.fen() != original_fen:
        raise AssertionError("A posição foi modificada.")

    if board.move_stack != original_stack:
        raise AssertionError("O histórico foi modificado.")

    if set(results["original"]["ordered"]) != set(moves):
        raise AssertionError("A ordenação original perdeu movimentos.")

    if set(results["optimized"]["ordered"]) != set(moves):
        raise AssertionError("A ordenação otimizada perdeu movimentos.")

    original_us = results["original"]["median_us"]
    optimized_us = results["optimized"]["median_us"]

    original_order = results["original"]["ordered"]
    optimized_order = results["optimized"]["ordered"]

    return {
        "legal_moves": len(moves),
        "original_us": round(original_us, 3),
        "optimized_us": round(optimized_us, 3),
        "speedup": round(
            original_us / optimized_us, 3
        ) if optimized_us > 0 else 0,
        "same_order": original_order == optimized_order,
        "same_first_move": (
            original_order[0] == optimized_order[0]
            if original_order else True
        ),
        "original_first": (
            original_order[0].uci()
            if original_order else ""
        ),
        "optimized_first": (
            optimized_order[0].uci()
            if optimized_order else ""
        ),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        return

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
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    parser.add_argument(
        "--sample-every",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--max-positions",
        type=int,
        default=200,
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=5,
    )

    args = parser.parse_args()

    positions = collect_positions(
        args.input,
        args.sample_every,
        args.max_positions,
    )

    if not positions:
        raise ValueError("Nenhuma posição encontrada.")

    rows = []

    for index, (file_name, ply, board) in enumerate(
        positions,
        start=1,
    ):
        result = benchmark_position(
            board,
            args.repeats,
        )

        rows.append({
            "file": file_name,
            "ply": ply,
            **result,
        })

        if index % 25 == 0:
            print(
                f"Processadas {index}/{len(positions)} posições"
            )

    original_total = sum(
        row["original_us"] for row in rows
    )
    optimized_total = sum(
        row["optimized_us"] for row in rows
    )

    summary = {
        "positions": len(rows),
        "original_total_us": round(original_total, 3),
        "optimized_total_us": round(optimized_total, 3),
        "overall_speedup": round(
            original_total / optimized_total, 3
        ) if optimized_total > 0 else 0,
        "same_order_positions": sum(
            row["same_order"] for row in rows
        ),
        "same_first_move_positions": sum(
            row["same_first_move"] for row in rows
        ),
        "average_legal_moves": round(
            statistics.mean(
                row["legal_moves"] for row in rows
            ),
            2,
        ),
    }

    write_csv(
        args.output / "position_results.csv",
        rows,
    )
    write_csv(
        args.output / "summary.csv",
        [summary],
    )

    print("\n=== Benchmark de Ordenação V2 ===")
    print(f"Posições: {summary['positions']}")
    print(
        f"Aceleração isolada: "
        f"{summary['overall_speedup']:.2f}x"
    )
    print(
        "Mesma ordem: "
        f"{summary['same_order_positions']}"
    )
    print(
        "Mesmo primeiro movimento: "
        f"{summary['same_first_move_positions']}"
    )
    print(f"\nResultados: {args.output}")


if __name__ == "__main__":
    main()
