
import argparse
import sys
from pathlib import Path
from time import perf_counter

import chess
import chess.pgn

try:
    from chess_engine.engine import ChessEngine
except ModuleNotFoundError:
    sys.path.insert(
        0,
        str(Path(__file__).resolve().parents[1] / "src"),
    )
    from chess_engine.engine import ChessEngine


def play_game(
    depth: int,
    time_limit: float,
    max_plies: int,
    output: Path,
) -> None:
    board = chess.Board()

    engines = {
        chess.WHITE: ChessEngine(max_depth=depth),
        chess.BLACK: ChessEngine(max_depth=depth),
    }

    game = chess.pgn.Game()
    game.headers["Event"] = "Chess Challenge III - Self Play"
    game.headers["White"] = "ChessEngine"
    game.headers["Black"] = "ChessEngine"

    node = game

    print("\n=== SELF-PLAY ===")
    print(f"Profundidade: {depth}")
    print(f"Tempo por lance: {time_limit:.2f}s")
    print(f"Limite de meios-lances: {max_plies}")
    print()

    start = perf_counter()

    for _ in range(max_plies):
        if board.is_game_over(claim_draw=True):
            break

        color = board.turn
        engine = engines[color]

        result = engine.best_move(
            board,
            time_limit=time_limit,
        )

        if result.move not in board.legal_moves:
            raise RuntimeError(
                f"Motor retornou lance ilegal: {result.move}"
            )

        notation = board.san(result.move)

        prefix = (
            f"{board.fullmove_number}."
            if color == chess.WHITE
            else f"{board.fullmove_number}..."
        )

        print(
            f"{prefix} {notation:<8} "
            f"| profundidade={result.depth} "
            f"| avaliação={result.score:+d} cp "
            f"| tempo={result.elapsed:.3f}s"
        )

        node = node.add_variation(result.move)
        board.push(result.move)

        if not board.is_valid():
            raise RuntimeError("Tabuleiro inválido após lance.")

    finished = board.is_game_over(claim_draw=True)
    outcome = board.outcome(claim_draw=True)

    result_text = (
        outcome.result()
        if outcome is not None
        else "*"
    )

    game.headers["Result"] = result_text

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output.open(
        "w",
        encoding="utf-8",
    ) as file:
        print(game, file=file, end="\n\n")

    print("\n=== RESULTADO ===")
    print(board)
    print()
    print(f"Resultado: {result_text}")

    if outcome is not None:
        print(f"Motivo: {outcome.termination.name}")
    elif not finished:
        print("Partida interrompida pelo limite de lances.")

    print(f"Meios-lances: {board.ply()}")
    print(f"Tempo total: {perf_counter() - start:.2f}s")
    print(f"PGN salvo em: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Partida entre duas instâncias do ChessEngine."
    )

    parser.add_argument(
        "--depth",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--time",
        type=float,
        default=1.0,
    )

    parser.add_argument(
        "--max-plies",
        type=int,
        default=200,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmarks/self_play.pgn"),
    )

    args = parser.parse_args()

    if args.depth < 1:
        parser.error("--depth deve ser >= 1")

    if args.time <= 0:
        parser.error("--time deve ser maior que zero")

    if args.max_plies < 1:
        parser.error("--max-plies deve ser >= 1")

    play_game(
        depth=args.depth,
        time_limit=args.time,
        max_plies=args.max_plies,
        output=args.output,
    )


if __name__ == "__main__":
    main()
