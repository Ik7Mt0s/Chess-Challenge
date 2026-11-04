import csv
from pathlib import Path
import chess
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

from chess_engine.neural.model import SimpleChessNet
from chess_engine.neural.representation import board_to_tensor


class RealChessDataset(Dataset):
    """
    Carrega posições FEN reais e suas avaliações (centipeões) a partir de um arquivo CSV.
    """
    def __init__(self, csv_filepath: Path | str):
        self.samples = []
        path = Path(csv_filepath)
        if not path.exists():
            raise FileNotFoundError(f"Arquivo CSV não encontrado em: {path}")

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fen = row["fen"]
                # Suporta nomes comuns de coluna: evaluation, score ou cp
                raw_score = float(row.get("evaluation") or row.get("score") or row.get("cp") or 0.0)
                # Normaliza centipeões para o intervalo [-1.0, 1.0]
                normalized_score = max(-1.0, min(1.0, raw_score / 1000.0))
                self.samples.append((fen, normalized_score))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        fen, score = self.samples[idx]
        board = chess.Board(fen)
        tensor = board_to_tensor(board, flip_black_perspective=True)
        target = torch.tensor([score], dtype=torch.float32)
        return tensor, target


class SyntheticDataset(Dataset):
    """Dataset sintético de fallback para validação e testes rápidos."""
    def __init__(self, samples: list[tuple[str, float]]):
        self.samples = samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        fen, score = self.samples[idx]
        board = chess.Board(fen)
        tensor = board_to_tensor(board, flip_black_perspective=True)
        target = torch.tensor([score], dtype=torch.float32)
        return tensor, target


def train_model(
    dataset: Dataset,
    epochs: int = 10,
    batch_size: int = 64,
    lr: float = 0.001,
    output_path: str = "weights/simple_chess_net.pth"
):
    """
    Executa o treinamento com suporte a aceleração de hardware (GPU/CUDA se disponível).
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Utilizando dispositivo de processamento: {device}")

    dataloader = DataLoader(
        dataset, 
        batch_size=batch_size, 
        shuffle=True, 
        pin_memory=(device.type == "cuda")
    )

    model = SimpleChessNet().to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    model.train()
    print(f"Iniciando treinamento com {len(dataset)} posições...")

    for epoch in range(1, epochs + 1):
        running_loss = 0.0
        for tensors, targets in dataloader:
            tensors = tensors.to(device)
            targets = targets.to(device)

            optimizer.zero_grad()
            outputs = model(tensors)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * tensors.size(0)

        epoch_loss = running_loss / len(dataset)
        print(f"Época [{epoch}/{epochs}] - Loss (MSE): {epoch_loss:.6f}")

    # Salva os pesos convertendo para CPU para garantir inferência sem erros no motor
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.cpu().state_dict(), output_file)
    print(f"Modelo treinado salvo com sucesso em: {output_file}")


if __name__ == "__main__":
    csv_path = Path("data/chess_evals.csv")

    if csv_path.exists():
        print(f"Carregando dataset real a partir de: {csv_path}")
        dataset = RealChessDataset(csv_path)
        # Ajuste batch_size para 64 ou 128 para aceleração do treinamento
        train_model(dataset, epochs=10, batch_size=64, lr=0.001)
    else:
        print(f"Aviso: Arquivo '{csv_path}' não encontrado. Executando fallback com dados sintéticos.")
        sample_data = [
            (chess.STARTING_FEN, 0.0),
            ("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1", 0.1),
            ("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 0.9),
            ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR b KQkq - 0 1", -0.9),
        ]
        dataset = SyntheticDataset(sample_data)
        train_model(dataset, epochs=5, batch_size=2)