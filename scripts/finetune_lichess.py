
import argparse
import random
import sys
from pathlib import Path

import chess
import chess.pgn
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chess_engine.evaluation.heuristic import HeuristicEvaluator
from chess_engine.neural.model import SimpleChessNet
from chess_engine.neural.representation import board_to_tensor


def outcome_for_turn(result: str, turn: chess.Color) -> float:
    if result == "1/2-1/2":
        return 0.0

    white_won = result == "1-0"
    player_won = white_won == (turn == chess.WHITE)

    return 1.0 if player_won else -1.0


def training_target(
    board: chess.Board,
    result: str,
    evaluator: HeuristicEvaluator,
    outcome_weight: float = 0.25,
) -> float:
    """
    Retorna um alvo normalizado na perspectiva do jogador ativo.

    75%: avaliação heurística em centipawns.
    25%: resultado real, equivalente a +/-300 cp.

    A combinação preserva aproximadamente a escala
    utilizada pelo modelo original.
    """
    heuristic_cp = evaluator.evaluate(board)

    if board.turn == chess.BLACK:
        heuristic_cp = -heuristic_cp

    heuristic_normalized = max(
        -0.95,
        min(0.95, heuristic_cp / 1000.0),
    )

    result_normalized = (
        outcome_for_turn(result, board.turn) * 0.3
    )

    target = (
        (1.0 - outcome_weight) * heuristic_normalized
        + outcome_weight * result_normalized
    )

    return float(max(-0.95, min(0.95, target)))


def collect_positions(
    pgn_path: Path,
    max_games: int,
    max_positions: int,
    min_elo: int,
    positions_per_game: int,
    seed: int,
    outcome_weight: float = 0.25,
):
    if not pgn_path.is_file():
        raise FileNotFoundError(
            f"Arquivo PGN não encontrado: {pgn_path}"
        )

    rng = random.Random(seed)
    evaluator = HeuristicEvaluator()

    train_samples = []
    validation_samples = []

    processed = 0
    accepted = 0

    with pgn_path.open(
        "r",
        encoding="utf-8",
        errors="replace",
    ) as file:
        while (
            processed < max_games
            and len(train_samples) + len(validation_samples)
            < max_positions
        ):
            game = chess.pgn.read_game(file)

            if game is None:
                break

            processed += 1

            try:
                white_elo = int(
                    game.headers.get("WhiteElo", "0")
                )
                black_elo = int(
                    game.headers.get("BlackElo", "0")
                )
            except (ValueError, TypeError):
                continue

            if min(white_elo, black_elo) < min_elo:
                continue

            result = game.headers.get("Result", "*")

            if result not in ("1-0", "0-1", "1/2-1/2"):
                continue

            if game.errors:
                continue

            moves = list(game.mainline_moves())

            # Evita usar apenas posições iniciais ou
            # posições excessivamente próximas do final.
            start = 12
            end = min(len(moves) - 2, 80)

            if end <= start:
                continue

            available = list(range(start, end))
            selected = set(
                rng.sample(
                    available,
                    min(positions_per_game, len(available)),
                )
            )

            # Separação por partida: posições da mesma
            # partida não aparecem em treino e validação.
            destination = (
                validation_samples
                if rng.random() < 0.1
                else train_samples
            )

            board = game.board()

            for ply, move in enumerate(moves):
                if ply in selected:
                    target = training_target(
                        board,
                        result,
                        evaluator,
                        outcome_weight=outcome_weight,
                    )

                    destination.append(
                        (board.fen(), target)
                    )

                    if (
                        len(train_samples)
                        + len(validation_samples)
                        >= max_positions
                    ):
                        break

                board.push(move)

            accepted += 1

            if processed % 5000 == 0:
                print(
                    f"Partidas lidas: {processed:,} | "
                    f"Aceitas: {accepted:,} | "
                    f"Posições: "
                    f"{len(train_samples) + len(validation_samples):,}",
                    flush=True,
                )

    print(
        f"\nColeta concluída: {processed:,} partidas lidas, "
        f"{accepted:,} aceitas."
    )
    print(
        f"Treino: {len(train_samples):,} posições | "
        f"Validação: {len(validation_samples):,} posições"
    )

    return train_samples, validation_samples


def make_dataset(samples):
    if not samples:
        raise ValueError("Não há posições para criar o dataset.")

    features = np.empty(
        (len(samples), 12, 8, 8),
        dtype=np.float32,
    )
    labels = np.empty(
        (len(samples), 1),
        dtype=np.float32,
    )

    for index, (fen, target) in enumerate(samples):
        board = chess.Board(fen)

        features[index] = board_to_tensor(
            board,
            flip_black_perspective=True,
        ).numpy()

        labels[index, 0] = target

    return TensorDataset(
        torch.from_numpy(features),
        torch.from_numpy(labels),
    )


def finetune(
    pgn_path: Path,
    input_model: Path,
    output_model: Path,
    max_games: int = 20000,
    max_positions: int = 30000,
    min_elo: int = 1800,
    positions_per_game: int = 3,
    epochs: int = 6,
    batch_size: int = 256,
    learning_rate: float = 0.0001,
    outcome_weight: float = 0.25,
    seed: int = 42,
):
    if not input_model.is_file():
        raise FileNotFoundError(
            f"Pesos originais não encontrados: {input_model}"
        )

    if not 0.0 <= outcome_weight <= 1.0:
        raise ValueError("outcome_weight deve estar entre 0 e 1.")

    if epochs < 1 or batch_size < 1:
        raise ValueError("epochs e batch_size devem ser positivos.")

    torch.manual_seed(seed)
    random.seed(seed)
    np.random.seed(seed)

    # Para inferência/treino de rede pequena na CPU,
    # testar uma thread reduz a contenção.
    torch.set_num_threads(1)

    train_samples, validation_samples = collect_positions(
        pgn_path=pgn_path,
        max_games=max_games,
        max_positions=max_positions,
        min_elo=min_elo,
        positions_per_game=positions_per_game,
        seed=seed,
        outcome_weight=outcome_weight,
    )

    if not train_samples or not validation_samples:
        raise ValueError(
            "Dados insuficientes. Aumente --max-games "
            "ou reduza --min-elo."
        )

    train_loader = DataLoader(
        make_dataset(train_samples),
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,
    )

    validation_loader = DataLoader(
        make_dataset(validation_samples),
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
    )

    model = SimpleChessNet()
    model.load_state_dict(
        torch.load(
            input_model,
            map_location="cpu",
            weights_only=True,
        )
    )

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=learning_rate,
        weight_decay=0.0001,
    )

    criterion = nn.MSELoss()
    best_validation = float("inf")
    best_state = None

    print("\nIniciando fine-tuning...\n")

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        train_count = 0

        for features, labels in train_loader:
            optimizer.zero_grad(set_to_none=True)

            predictions = model(features)
            loss = criterion(predictions, labels)

            loss.backward()
            optimizer.step()

            count = labels.size(0)
            train_loss += loss.item() * count
            train_count += count

        model.eval()
        validation_loss = 0.0
        validation_count = 0

        with torch.inference_mode():
            for features, labels in validation_loader:
                predictions = model(features)
                loss = criterion(predictions, labels)

                count = labels.size(0)
                validation_loss += loss.item() * count
                validation_count += count

        train_mse = train_loss / train_count
        val_mse = validation_loss / validation_count

        print(
            f"Época {epoch}/{epochs} | "
            f"Train MSE: {train_mse:.6f} | "
            f"Val MSE: {val_mse:.6f}",
            flush=True,
        )

        if val_mse < best_validation:
            best_validation = val_mse
            best_state = {
                name: tensor.detach().cpu().clone()
                for name, tensor in model.state_dict().items()
            }

    if best_state is None:
        raise RuntimeError("Nenhum modelo foi treinado.")

    output_model.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    torch.save(best_state, output_model)

    print("\nFine-tuning concluído!")
    print(f"Melhor Val MSE: {best_validation:.6f}")
    print(f"Modelo salvo em: {output_model}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--pgn",
        type=Path,
        default=ROOT / "lichess_db_standard_rated_2016-05.pgn",
    )
    parser.add_argument(
        "--input-model",
        type=Path,
        default=ROOT / "weights" / "simple_chess_net.pth",
    )
    parser.add_argument(
        "--output-model",
        type=Path,
        default=ROOT / "weights" / "simple_chess_net_v2.pth",
    )
    parser.add_argument("--max-games", type=int, default=20000)
    parser.add_argument("--max-positions", type=int, default=30000)
    parser.add_argument("--min-elo", type=int, default=1800)
    parser.add_argument("--positions-per-game", type=int, default=3)
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=0.0001)
    parser.add_argument("--outcome-weight", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()

    finetune(
        pgn_path=args.pgn,
        input_model=args.input_model,
        output_model=args.output_model,
        max_games=args.max_games,
        max_positions=args.max_positions,
        min_elo=args.min_elo,
        positions_per_game=args.positions_per_game,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        outcome_weight=args.outcome_weight,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
