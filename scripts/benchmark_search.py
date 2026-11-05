
import argparse
import csv
import statistics
import sys
from pathlib import Path

import chess
import chess.engine
import chess.pgn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chess_engine.engine import ChessEngine
from chess_engine.evaluation.neural import (
    HybridEvaluator,
    NeuralEvaluator,
)


FIELDS = [
    "position_id",
    "profile",
    "fen",
    "side",
    "best_move",
    "score_cp",
    "depth",
    "status",
    "elapsed_seconds",
    "negamax_nodes",
    "quiescence_nodes",
    "total_nodes",
    "q_ratio",
    "nps",
    "neural_inferences",
    "neural_cache_hits",
    "neural_skipped_budget",
    "neural_skipped_threshold",
    "stockfish_move",
    "stockfish_match",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Benchmark reproduzivel de busca."
    )

    parser.add_argument(
        "--pgn",
        nargs="+",
        required=True,
        help="Arquivos PGN das partidas anteriores.",
    )

    parser.add_argument(
        "--model",
        default="weights/simple_chess_net.pth",
    )

    parser.add_argument(
        "--weight",
        type=float,
        default=0.4,
    )

    parser.add_argument(
        "--budget",
        type=int,
        default=128,
        help="-1 representa inferencias ilimitadas.",
    )

    parser.add_argument(
        "--time",
        type=float,
        default=1.0,
    )

    parser.add_argument(
        "--depth",
        type=int,
        default=4,
    )

    parser.add_argument(
        "--full-time",
        action="store_true",
        help="Continua aprofundando ate esgotar o tempo.",
    )

    parser.add_argument(
        "--sample-step",
        type=int,
        default=4,
        help="Intervalo, em meios-lances, entre posicoes.",
    )

    parser.add_argument(
        "--max-positions",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--profiles",
        nargs="+",
        choices=["baseline", "king_safety"],
        default=["baseline", "king_safety"],
    )

    parser.add_argument(
        "--stockfish",
        default=None,
        help="Caminho do executavel Stockfish.",
    )

    parser.add_argument(
        "--stockfish-time",
        type=float,
        default=0.15,
    )

    parser.add_argument(
        "--output",
        default="benchmarks/search_comparison.csv",
    )

    return parser.parse_args()


def collect_positions(args):
    positions = []

    for filename in args.pgn:
        path = Path(filename)

        if not path.is_file():
            raise FileNotFoundError(path)

        with path.open("r", encoding="utf-8-sig") as handle:
            game_number = 0

            while True:
                game = chess.pgn.read_game(handle)

                if game is None:
                    break

                game_number += 1
                board = game.board()

                for ply, move in enumerate(
                    game.mainline_moves(),
                    start=1,
                ):
                    board.push(move)

                    if ply % args.sample_step:
                        continue

                    if board.is_game_over(claim_draw=True):
                        continue

                    position_id = (
                        f"{path.stem}:"
                        f"{game_number}:"
                        f"{ply}"
                    )

                    positions.append(
                        (position_id, board.copy(stack=True))
                    )

                    if len(positions) >= args.max_positions:
                        return positions

    return positions


def make_engine(profile, args):
    neural = NeuralEvaluator(model_path=args.model)

    evaluator = HybridEvaluator(
        neural=neural,
        weight_neural=args.weight,
        max_neural_inferences=(
            None if args.budget < 0 else args.budget
        ),
        use_king_safety=(profile == "king_safety"),
    )

    return ChessEngine(
        evaluator=evaluator,
        max_depth=args.depth,
        use_full_time=args.full_time,
        score_quiet_checks=True,
    )


def analyze_stockfish(engine, board, seconds):
    if engine is None:
        return ""

    info = engine.analyse(
        board,
        chess.engine.Limit(time=seconds),
    )

    pv = info.get("pv", [])

    return pv[0].uci() if pv else ""


def run_position(
    position_id,
    board,
    profile,
    engine,
    reference_move,
    seconds,
):
    result = engine.best_move(
        board.copy(stack=True),
        time_limit=seconds,
    )

    metrics = result.metrics

    negamax_nodes = int(
        metrics.get("negamax_nodes", 0)
    )
    q_nodes = int(
        metrics.get("quiescence_nodes", 0)
    )
    total = negamax_nodes + q_nodes

    selected = result.move.uci()

    return {
        "position_id": position_id,
        "profile": profile,
        "fen": board.fen(),
        "side": (
            "white"
            if board.turn == chess.WHITE
            else "black"
        ),
        "best_move": selected,
        "score_cp": result.score,
        "depth": result.depth,
        "status": result.status,
        "elapsed_seconds": round(result.elapsed, 4),
        "negamax_nodes": negamax_nodes,
        "quiescence_nodes": q_nodes,
        "total_nodes": total,
        "q_ratio": round(
            q_nodes / total if total else 0.0, 4
        ),
        "nps": round(
            float(metrics.get("nps", 0.0)), 2
        ),
        "neural_inferences": metrics.get(
            "neural_inferences", 0
        ),
        "neural_cache_hits": metrics.get(
            "neural_cache_hits", 0
        ),
        "neural_skipped_budget": metrics.get(
            "neural_skipped_budget", 0
        ),
        "neural_skipped_threshold": metrics.get(
            "neural_skipped_threshold", 0
        ),
        "stockfish_move": reference_move,
        "stockfish_match": (
            int(selected == reference_move)
            if reference_move
            else ""
        ),
    }


def report(rows):
    print("\n=== RESUMO ===")

    profiles = sorted(
        {row["profile"] for row in rows}
    )

    for profile in profiles:
        subset = [
            row for row in rows
            if row["profile"] == profile
        ]

        mean_depth = statistics.mean(
            row["depth"] for row in subset
        )
        mean_nps = statistics.mean(
            row["nps"] for row in subset
        )
        mean_q = statistics.mean(
            row["q_ratio"] for row in subset
        )

        print(
            f"\n{profile}: "
            f"{len(subset)} posicoes"
        )
        print(
            f"  Profundidade media: {mean_depth:.2f}"
        )
        print(
            f"  NPS medio: {mean_nps:,.0f}"
        )
        print(
            f"  Proporcao quiescencia: {mean_q:.1%}"
        )

        matched = [
            row["stockfish_match"]
            for row in subset
            if row["stockfish_match"] != ""
        ]

        if matched:
            print(
                "  Concordancia com Stockfish: "
                f"{statistics.mean(matched):.1%}"
            )

    positions = sorted(
        {row["position_id"] for row in rows}
    )

    print("\n=== DIFERENCAS ENTRE PERFIS ===")

    for position_id in positions:
        subset = [
            row for row in rows
            if row["position_id"] == position_id
        ]

        if len(subset) < 2:
            continue

        if len(
            {row["best_move"] for row in subset}
        ) == 1:
            continue

        print(f"\n{position_id}")

        for row in subset:
            print(
                f"  {row['profile']}: "
                f"{row['best_move']} | "
                f"depth={row['depth']} | "
                f"score={row['score_cp']}"
            )


def main():
    args = parse_args()

    if args.time <= 0:
        raise ValueError("--time deve ser positivo.")

    if args.sample_step < 1:
        raise ValueError(
            "--sample-step deve ser pelo menos 1."
        )

    positions = collect_positions(args)

    if not positions:
        raise RuntimeError(
            "Nenhuma posicao disponivel para o benchmark."
        )

    engines = {
        profile: make_engine(profile, args)
        for profile in args.profiles
    }

    reference = (
        chess.engine.SimpleEngine.popen_uci(args.stockfish)
        if args.stockfish
        else None
    )

    rows = []

    try:
        for index, (position_id, board) in enumerate(
            positions,
            start=1,
        ):
            stockfish_move = analyze_stockfish(
                reference,
                board,
                args.stockfish_time,
            )

            print(
                f"\n[{index}/{len(positions)}] "
                f"{position_id}"
            )

            for profile, engine in engines.items():
                row = run_position(
                    position_id,
                    board,
                    profile,
                    engine,
                    stockfish_move,
                    args.time,
                )

                rows.append(row)

                print(
                    f"  {profile}: "
                    f"{row['best_move']} | "
                    f"depth={row['depth']} | "
                    f"q={row['q_ratio']:.1%} | "
                    f"nps={row['nps']:,.0f}"
                )
    finally:
        if reference is not None:
            reference.quit()

    output = Path(args.output)
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=FIELDS,
        )

        writer.writeheader()
        writer.writerows(rows)

    report(rows)

    print(f"\nCSV salvo em: {output}")


if __name__ == "__main__":
    main()
