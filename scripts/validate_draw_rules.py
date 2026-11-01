
import argparse
import csv
import statistics
import time
from pathlib import Path

import chess
import chess.pgn

from chess_engine.search.draw_rules import is_draw


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = PROJECT_ROOT / "benchmarks" / "stockfish_matches"
DEFAULT_OUTPUT = PROJECT_ROOT / "benchmarks" / "draw_rules_validation"


def original_is_draw(board: chess.Board) -> bool:
    """
    Implementação original, anterior à Otimização 1.
    """
    return (
        board.is_stalemate()
        or board.is_insufficient_material()
        or board.is_seventyfive_moves()
        or board.is_fivefold_repetition()
        or board.can_claim_draw()
    )


def find_pgn_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        raise FileNotFoundError(
            f"Diretório de partidas não encontrado: {directory}"
        )

    files = sorted(directory.rglob("*.pgn"))

    if not files:
        raise FileNotFoundError(
            f"Nenhum arquivo PGN encontrado em: {directory}"
        )

    return files


def load_positions(
    path: Path,
    sample_every: int = 1,
) -> list[dict]:
    """
    Reconstrói as posições preservando o histórico.

    Inclui a posição inicial e, conforme sample_every,
    posições após os lances da partida.
    """
    if sample_every < 1:
        raise ValueError("sample_every deve ser >= 1.")

    positions = []

    with path.open("r", encoding="utf-8-sig") as file:
        game_number = 0

        while True:
            game = chess.pgn.read_game(file)

            if game is None:
                break

            game_number += 1

            if game.errors:
                raise ValueError(
                    f"PGN inválido: {path}, "
                    f"partida {game_number}: {game.errors}"
                )

            board = game.board()
            moves = list(game.mainline_moves())

            if not board.is_valid():
                raise ValueError(
                    f"Posição inicial inválida em {path}."
                )

            positions.append({
                "game_number": game_number,
                "ply": 0,
                "board": board.copy(stack=True),
            })

            for ply, move in enumerate(moves, start=1):
                if move not in board.legal_moves:
                    raise ValueError(
                        f"Lance ilegal em {path}, "
                        f"partida {game_number}, ply {ply}."
                    )

                board.push(move)

                if not board.is_valid():
                    raise ValueError(
                        f"Posição inválida em {path}, "
                        f"partida {game_number}, ply {ply}."
                    )

                if (
                    ply % sample_every == 0
                    or ply == len(moves)
                ):
                    positions.append({
                        "game_number": game_number,
                        "ply": ply,
                        "board": board.copy(stack=True),
                    })

    return positions


def measure_function(function, board, repeats: int) -> tuple[bool, float]:
    """
    Retorna o resultado e a mediana do tempo
    por chamada, em microssegundos.
    """
    measurements = []
    result = None

    for _ in range(repeats):
        started = time.perf_counter_ns()
        current = function(board)
        elapsed_ns = time.perf_counter_ns() - started

        if result is not None and current != result:
            raise AssertionError(
                "A função retornou resultados inconsistentes."
            )

        result = current
        measurements.append(elapsed_ns / 1000)

    return result, statistics.median(measurements)


def validate_position(
    board: chess.Board,
    repeats: int = 3,
) -> dict:
    if repeats < 1:
        raise ValueError("repeats deve ser >= 1.")

    if not board.is_valid():
        raise ValueError("Tabuleiro inválido.")

    original_fen = board.fen()
    original_stack = list(board.move_stack)

    old_result, old_us = measure_function(
        original_is_draw,
        board,
        repeats,
    )

    new_result, new_us = measure_function(
        is_draw,
        board,
        repeats,
    )

    if board.fen() != original_fen:
        raise AssertionError(
            "A validação modificou a posição."
        )

    if board.move_stack != original_stack:
        raise AssertionError(
            "A validação modificou o histórico."
        )

    return {
        "fen": original_fen,
        "history_plies": len(board.move_stack),
        "halfmove_clock": board.halfmove_clock,
        "original_draw": old_result,
        "optimized_draw": new_result,
        "equivalent": old_result == new_result,
        "original_us": round(old_us, 3),
        "optimized_us": round(new_us, 3),
        "speedup": round(
            old_us / new_us, 3
        ) if new_us > 0 else 0,
    }


def save_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        return

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("Nenhuma posição analisada.")

    mismatches = sum(
        not row["equivalent"]
        for row in rows
    )

    old_total = sum(
        row["original_us"]
        for row in rows
    )

    new_total = sum(
        row["optimized_us"]
        for row in rows
    )

    return {
        "positions": len(rows),
        "equivalent_positions": len(rows) - mismatches,
        "mismatches": mismatches,
        "draw_positions": sum(
            row["original_draw"]
            for row in rows
        ),
        "positions_with_history": sum(
            row["history_plies"] > 0
            for row in rows
        ),
        "original_total_us": round(old_total, 3),
        "optimized_total_us": round(new_total, 3),
        "overall_speedup": round(
            old_total / new_total, 3
        ) if new_total > 0 else 0,
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Valida a Otimização 1 usando "
            "históricos reais de partidas PGN."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Diretório com arquivos PGN.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Diretório dos resultados.",
    )

    parser.add_argument(
        "--sample-every",
        type=int,
        default=1,
        help="Analisa uma posição a cada N meios-lances.",
    )

    parser.add_argument(
        "--repeats",
        type=int,
        default=3,
        help="Repetições de cada medição.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if args.sample_every < 1:
        raise ValueError("--sample-every deve ser >= 1.")

    if args.repeats < 1:
        raise ValueError("--repeats deve ser >= 1.")

    files = find_pgn_files(args.input)
    rows = []

    print("\n=== Validação da Otimização 1 ===")
    print(f"PGNs encontrados: {len(files)}")
    print(f"Amostragem: 1 a cada {args.sample_every} ply")
    print(f"Repetições: {args.repeats}\n")

    for index, path in enumerate(files, start=1):
        positions = load_positions(
            path,
            sample_every=args.sample_every,
        )

        mismatches = 0

        for position in positions:
            result = validate_position(
                position["board"],
                repeats=args.repeats,
            )

            row = {
                "file": str(path.relative_to(args.input)),
                "game_number": position["game_number"],
                "ply": position["ply"],
                **result,
            }

            rows.append(row)

            if not result["equivalent"]:
                mismatches += 1

        print(
            f"[{index}/{len(files)}] {path.name}: "
            f"{len(positions)} posições, "
            f"{mismatches} divergências"
        )

    summary = summarize(rows)

    save_csv(
        args.output / "position_results.csv",
        rows,
    )

    save_csv(
        args.output / "summary.csv",
        [summary],
    )

    print("\n=== Resultado ===")
    print(f"Posições: {summary['positions']}")
    print(f"Com histórico: {summary['positions_with_history']}")
    print(f"Posições de empate: {summary['draw_positions']}")
    print(f"Divergências: {summary['mismatches']}")
    print(
        f"Aceleração agregada: "
        f"{summary['overall_speedup']:.2f}x"
    )

    print("\nArquivos:")
    print(args.output / "summary.csv")
    print(args.output / "position_results.csv")

    if summary["mismatches"]:
        print(
            "\nATENÇÃO: foram encontradas divergências. "
            "Consulte position_results.csv."
        )
        raise SystemExit(1)

    print("\nValidação concluída sem divergências.")


if __name__ == "__main__":
    main()
