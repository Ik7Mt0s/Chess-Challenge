"""Compara a avaliação completa com critérios desligados, por partidas pareadas."""

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

import chess
import chess.pgn

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

try:
    from benchmark_evaluation import BaselineEvaluator
except ModuleNotFoundError:
    from scripts.benchmark_evaluation import BaselineEvaluator


class NoMobilityEvaluator(HeuristicEvaluator):
    MOBILITY_WEIGHTS = {}


class NoPawnStructureEvaluator(HeuristicEvaluator):
    @classmethod
    def _pawn_structure(cls, board: chess.Board, color: chess.Color) -> int:
        return 0


class NoKingSafetyEvaluator(HeuristicEvaluator):
    @classmethod
    def _king_safety(
        cls,
        board: chess.Board,
        color: chess.Color,
        phase: int,
    ) -> int:
        return 0


@dataclass(frozen=True)
class Matchup:
    name: str
    evaluator: type[HeuristicEvaluator] | type[BaselineEvaluator]


MATCHUPS = {
    "baseline": Matchup("baseline", BaselineEvaluator),
    "no_mobility": Matchup("sem_mobilidade", NoMobilityEvaluator),
    "no_pawn_structure": Matchup(
        "sem_estrutura_de_peoes",
        NoPawnStructureEvaluator,
    ),
    "no_king_safety": Matchup("sem_seguranca_do_rei", NoKingSafetyEvaluator),
}

OPENINGS = (
    ("Italiana", ("e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5")),
    ("Siciliana", ("e4", "c5", "Nf3", "d6", "d4", "cxd4")),
    ("Gambito_da_dama", ("d4", "d5", "c4", "e6", "Nc3", "Nf6")),
    ("Espanhola", ("e4", "e5", "Nf3", "Nc6", "Bb5", "a6")),
)


def play_game(
    opponent: Matchup,
    pair_id: int,
    full_color: chess.Color,
    opening_name: str,
    opening_moves: tuple[str, ...],
    depth: int,
    time_limit: float,
    max_plies: int,
) -> tuple[dict, chess.pgn.Game]:
    board = chess.Board()
    game = chess.pgn.Game()
    game.headers["Event"] = "Chess Challenge III - Evaluation Match"
    game.headers["White"] = "Passo3" if full_color else opponent.name
    game.headers["Black"] = opponent.name if full_color else "Passo3"
    game.headers["Opening"] = opening_name
    node = game

    for san in opening_moves:
        move = board.parse_san(san)
        node = node.add_variation(move)
        board.push(move)

    full_engine = ChessEngine(
        evaluator=HeuristicEvaluator(),
        max_depth=depth,
    )
    opponent_engine = ChessEngine(
        evaluator=opponent.evaluator(),
        max_depth=depth,
    )

    elapsed = {chess.WHITE: 0.0, chess.BLACK: 0.0}
    nodes = {chess.WHITE: 0, chess.BLACK: 0}
    depths = {chess.WHITE: 0, chess.BLACK: 0}
    move_counts = {chess.WHITE: 0, chess.BLACK: 0}
    statuses = set()

    for _ in range(max_plies):
        if board.is_game_over(claim_draw=True):
            break

        color = board.turn
        engine = (
            full_engine
            if color == full_color
            else opponent_engine
        )
        result = engine.best_move(board, time_limit=time_limit)
        statuses.add(result.status)

        if result.move not in board.legal_moves:
            raise RuntimeError(f"Lance ilegal retornado: {result.move}")

        elapsed[color] += result.elapsed
        nodes[color] += result.metrics.get("total_nodes", 0)
        depths[color] += result.depth
        move_counts[color] += 1
        node = node.add_variation(result.move)
        board.push(result.move)

    outcome = board.outcome(claim_draw=True)
    result_text = outcome.result() if outcome is not None else "*"
    game.headers["Result"] = result_text

    if outcome is None:
        full_result = "unfinished"
    elif outcome.winner is None:
        full_result = "draw"
    elif outcome.winner == full_color:
        full_result = "win"
    else:
        full_result = "loss"

    full_plies = board.ply() - len(opening_moves)
    full_moves_played = max(1, move_counts[full_color])
    opponent_moves_played = max(1, move_counts[not full_color])

    row = {
        "opponent": opponent.name,
        "pair_id": pair_id,
        "opening": opening_name,
        "full_color": "white" if full_color else "black",
        "full_result": full_result,
        "game_result": result_text,
        "termination": (
            outcome.termination.name if outcome is not None else "move_limit"
        ),
        "plies_after_opening": full_plies,
        "full_elapsed_seconds": round(elapsed[full_color], 3),
        "opponent_elapsed_seconds": round(elapsed[not full_color], 3),
        "full_average_depth": round(
            depths[full_color] / full_moves_played,
            2,
        ),
        "opponent_average_depth": round(
            depths[not full_color] / opponent_moves_played,
            2,
        ),
        "full_nodes": nodes[full_color],
        "opponent_nodes": nodes[not full_color],
        "statuses": "/".join(sorted(statuses)),
    }
    return row, game


def run_matches(
    opponent_names: list[str],
    pairs: int,
    depth: int,
    time_limit: float,
    max_plies: int,
    csv_output: Path,
    pgn_output: Path,
) -> list[dict]:
    rows = []
    games = []

    def save_progress() -> None:
        csv_output.parent.mkdir(parents=True, exist_ok=True)
        with csv_output.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

        pgn_output.parent.mkdir(parents=True, exist_ok=True)
        with pgn_output.open("w", encoding="utf-8") as file:
            for saved_game in games:
                print(saved_game, file=file, end="\n\n")

    for opponent_name in opponent_names:
        opponent = MATCHUPS[opponent_name]

        for pair_index in range(pairs):
            opening_name, opening_moves = OPENINGS[
                pair_index % len(OPENINGS)
            ]

            for full_color in (chess.WHITE, chess.BLACK):
                row, game = play_game(
                    opponent=opponent,
                    pair_id=pair_index + 1,
                    full_color=full_color,
                    opening_name=opening_name,
                    opening_moves=opening_moves,
                    depth=depth,
                    time_limit=time_limit,
                    max_plies=max_plies,
                )
                rows.append(row)
                games.append(game)
                save_progress()
                print(
                    f"{opponent.name:22} | {opening_name:14} | "
                    f"Etapa 3 de {row['full_color']:5} | "
                    f"resultado={row['full_result']:10} | "
                    f"profundidade média="
                    f"{row['full_average_depth']:.2f}/"
                    f"{row['opponent_average_depth']:.2f}",
                    flush=True,
                )

        opponent_rows = [
            row for row in rows if row["opponent"] == opponent.name
        ]
        wins = sum(row["full_result"] == "win" for row in opponent_rows)
        draws = sum(row["full_result"] == "draw" for row in opponent_rows)
        losses = sum(row["full_result"] == "loss" for row in opponent_rows)
        unfinished = sum(
            row["full_result"] == "unfinished" for row in opponent_rows
        )
        decided = wins + draws + losses
        points = wins + draws / 2
        score_percent = (
            f"{100 * points / decided:.1f}%"
            if decided
            else "n/a"
        )
        print(
            f"Resumo vs {opponent.name}: "
            f"{wins}V-{draws}E-{losses}D, "
            f"{unfinished} inconclusiva(s), "
            f"pontuação={score_percent}"
        )

    print(f"\nResultados CSV: {csv_output}")
    print(f"Partidas PGN: {pgn_output}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compara a avaliação completa com critérios desligados, "
            "trocando as cores em cada par."
        )
    )
    parser.add_argument(
        "--opponents",
        nargs="+",
        choices=sorted(MATCHUPS),
        default=["baseline", "no_mobility", "no_pawn_structure", "no_king_safety"],
    )
    parser.add_argument("--pairs", type=int, default=1)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--time", type=float, default=0.1)
    parser.add_argument("--max-plies", type=int, default=120)
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("benchmarks/evaluation_match_benchmark.csv"),
    )
    parser.add_argument(
        "--pgn-output",
        type=Path,
        default=Path("benchmarks/evaluation_match_benchmark.pgn"),
    )
    args = parser.parse_args()

    if args.pairs < 1:
        parser.error("--pairs deve ser pelo menos 1")
    if args.depth < 1:
        parser.error("--depth deve ser pelo menos 1")
    if args.time <= 0:
        parser.error("--time deve ser positivo")
    if args.max_plies < 1:
        parser.error("--max-plies deve ser pelo menos 1")

    run_matches(
        opponent_names=args.opponents,
        pairs=args.pairs,
        depth=args.depth,
        time_limit=args.time,
        max_plies=args.max_plies,
        csv_output=args.csv_output,
        pgn_output=args.pgn_output,
    )


if __name__ == "__main__":
    main()
