import argparse
import csv
import random
from pathlib import Path

import chess
import chess.pgn

from chess_engine.evaluation.heuristic import HeuristicEvaluator


def generate_dataset(
    pgn_path: Path,
    output_path: Path,
    samples: int,
    seed: int,
    sample_probability: float,
) -> None:
    if not pgn_path.is_file():
        raise FileNotFoundError(f"PGN não encontrado: {pgn_path}")

    if samples <= 0:
        raise ValueError("A quantidade de amostras deve ser positiva.")

    rng = random.Random(seed)
    evaluator = HeuristicEvaluator()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Preserva o CSV existente e evita posições repetidas.
    seen = set()
    existing = 0

    if output_path.exists():
        with output_path.open("r", encoding="utf-8", newline="") as file:
            for row in csv.DictReader(file):
                fen = row.get("fen")
                if fen:
                    seen.add(" ".join(fen.split()[:4]))
                    existing += 1

    collected = 0
    games = 0
    mode = "a" if output_path.exists() else "w"

    with (
        pgn_path.open("r", encoding="utf-8", errors="replace") as source,
        output_path.open(mode, encoding="utf-8", newline="") as target,
    ):
        writer = csv.writer(target)

        if mode == "w":
            writer.writerow(["fen", "evaluation"])

        while collected < samples:
            game = chess.pgn.read_game(source)

            if game is None:
                print("Fim do PGN.")
                break

            games += 1
            board = game.board()

            for move in game.mainline_moves():
                board.push(move)

                if board.is_game_over():
                    continue

                # Amostragem ao longo de diferentes partidas.
                if rng.random() > sample_probability:
                    continue

                fen = board.fen()
                position_key = " ".join(fen.split()[:4])

                if position_key in seen:
                    continue

                # Avaliação em centipeões, positiva para as brancas.
                score = evaluator.evaluate(board)

                writer.writerow([fen, score])
                seen.add(position_key)
                collected += 1

                if collected % 1000 == 0:
                    target.flush()
                    print(
                        f"Posições novas: {collected:,}/{samples:,} "
                        f"| Partidas lidas: {games:,}"
                    )

                if collected >= samples:
                    break

    print(
        f"Concluído! {collected:,} posições adicionadas. "
        f"Linhas anteriores: {existing:,}. "
        f"Arquivo: {output_path}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera dataset de avaliações a partir de partidas PGN."
    )
    parser.add_argument(
        "--pgn",
        type=Path,
        default=Path("data/lichess_db_standard_rated_2016-05.pgn"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/chess_evals.csv"),
    )
    parser.add_argument("--samples", type=int, default=30000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--sample-probability",
        type=float,
        default=0.15,
    )

    args = parser.parse_args()

    if not 0 < args.sample_probability <= 1:
        parser.error("--sample-probability deve estar entre 0 e 1.")

    generate_dataset(
        pgn_path=args.pgn,
        output_path=args.output,
        samples=args.samples,
        seed=args.seed,
        sample_probability=args.sample_probability,
    )


if __name__ == "__main__":
    main()
