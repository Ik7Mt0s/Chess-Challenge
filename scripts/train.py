import os
from pathlib import Path
import chess
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

from chess_engine.neural.model import SimpleChessNet
from chess_engine.neural.representation import board_to_tensor


class ChessDataset(Dataset):
    """
    Dataset PyTorch para carregar posições de xadrez (FEN) e suas avaliações.
    A pontuação deve estar no intervalo [-1.0, 1.0].
    """
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
    data: list[tuple[str, float]],
    epochs: int = 10,
    batch_size: int = 32,
    lr: float = 0.001,
    output_path: str = "weights/simple_chess_net.pth"  # Alterado de models/ para weights/
):
    """
    Executa o loop de treinamento e salva os pesos aprendidos.
    """
    # 1. Preparação dos Dados
    dataset = ChessDataset(data)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    # 2. Inicialização do Modelo, Perda e Otimizador
    model = SimpleChessNet()
    criterion = nn.MSELoss()  # Erro Quadrático Médio para regressão
    optimizer = optim.Adam(model.parameters(), lr=lr)

    model.train()
    print(f"Iniciando treinamento com {len(data)} posições...")

    # 3. Loop de Treinamento
    for epoch in range(1, epochs + 1):
        running_loss = 0.0
        for tensors, targets in dataloader:
            optimizer.zero_grad()
            outputs = model(tensors)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * tensors.size(0)

        epoch_loss = running_loss / len(dataset)
        print(f"Época [{epoch}/{epochs}] - Loss (MSE): {epoch_loss:.6f}")

    # 4. Salvar o arquivo de pesos (.pth)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), output_path)
    print(f"Modelo treinado salvo com sucesso em: {output_path}")


if __name__ == "__main__":
    # Posições sintéticas/exemplo para validação do pipeline (FEN, pontuação)
    sample_data = [
        (chess.STARTING_FEN, 0.0),                                                # Posição inicial (equilibrada)
        ("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1", 0.1),     # 1.e4 (ligeira vantagem branca)
        ("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 0.9),         # Brancas com Dama a mais
        ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR b KQkq - 0 1", -0.9),        # Pretas com Dama a mais
    ]

    train_model(sample_data, epochs=5, batch_size=2)