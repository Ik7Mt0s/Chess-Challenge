import argparse
import csv
from pathlib import Path

import chess
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset, random_split

from chess_engine.neural.model import SimpleChessNet
from chess_engine.neural.representation import board_to_tensor


class RealChessDataset(Dataset):
    def __init__(self, csv_filepath: Path | str):
        path = Path(csv_filepath)

        if not path.is_file():
            raise FileNotFoundError(f"Dataset não encontrado: {path}")

        self.samples = []

        with path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)

            if not reader.fieldnames or not {"fen", "evaluation"}.issubset(
                reader.fieldnames
            ):
                raise ValueError(
                    "O CSV precisa das colunas 'fen' e 'evaluation'."
                )

            for row in reader:
                fen = row["fen"]
                score = float(row["evaluation"])

                board = chess.Board(fen)

                # Avaliação original: perspectiva das brancas.
                # Rede neural: perspectiva de quem joga.
                if board.turn == chess.BLACK:
                    score = -score

                target = max(-1.0, min(1.0, score / 1000.0))
                self.samples.append((fen, target))

        if len(self.samples) < 2:
            raise ValueError("O dataset precisa de pelo menos 2 posições.")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        fen, target = self.samples[index]
        board = chess.Board(fen)

        tensor = board_to_tensor(
            board,
            flip_black_perspective=True,
        )

        return tensor, torch.tensor([target], dtype=torch.float32)


def train_model(
    csv_path: Path,
    output_path: Path,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    seed: int,
):
    torch.manual_seed(seed)

    dataset = RealChessDataset(csv_path)
    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    validation_size = max(1, int(len(dataset) * 0.1))
    training_size = len(dataset) - validation_size

    train_dataset, validation_dataset = random_split(
        dataset,
        [training_size, validation_size],
        generator=torch.Generator().manual_seed(seed),
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        pin_memory=device.type == "cuda",
    )

    validation_loader = DataLoader(
        validation_dataset,
        batch_size=batch_size,
        shuffle=False,
        pin_memory=device.type == "cuda",
    )

    model = SimpleChessNet().to(device)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=learning_rate,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    best_validation_loss = float("inf")

    print(f"Dispositivo: {device}")
    print(f"Treinamento: {training_size:,} posições")
    print(f"Validação: {validation_size:,} posições")

    for epoch in range(1, epochs + 1):
        model.train()
        training_loss = 0.0

        for tensors, targets in train_loader:
            tensors = tensors.to(device)
            targets = targets.to(device)

            optimizer.zero_grad()

            predictions = model(tensors)
            loss = criterion(predictions, targets)

            loss.backward()
            optimizer.step()

            training_loss += loss.item() * tensors.size(0)

        training_loss /= training_size

        model.eval()
        validation_loss = 0.0

        with torch.no_grad():
            for tensors, targets in validation_loader:
                tensors = tensors.to(device)
                targets = targets.to(device)

                predictions = model(tensors)
                loss = criterion(predictions, targets)

                validation_loss += loss.item() * tensors.size(0)

        validation_loss /= validation_size

        print(
            f"Época {epoch}/{epochs} "
            f"| Treino: {training_loss:.6f} "
            f"| Validação: {validation_loss:.6f}"
        )

        if validation_loss < best_validation_loss:
            best_validation_loss = validation_loss

            torch.save(
                {
                    key: value.detach().cpu()
                    for key, value in model.state_dict().items()
                },
                output_path,
            )

            print(f"Melhor modelo salvo: {output_path}")

    print(
        f"Treinamento concluído. "
        f"Melhor perda de validação: {best_validation_loss:.6f}"
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("data/chess_evals.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("weights/simple_chess_net.pth"),
    )
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()

    train_model(
        csv_path=args.csv,
        output_path=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()