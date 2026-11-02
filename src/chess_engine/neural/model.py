import torch
import torch.nn as nn
import torch.nn.functional as F

class SimpleChessNet(nn.Module):
    """
    Rede Neural Convolucional enxuta para avaliação estática de posições.
    
    Entrada:  Tensor de formato (batch_size, 12, 8, 8)
    Saída:    Escalar entre -1.0 (vantagem total do oponente) e +1.0 (vantagem total do jogador ativo)
    """
    def __init__(self):
        super(SimpleChessNet, self).__init__()
        
        # 1. Extração de Padrões Espaciais (Camadas Convolucionais)
        # Processa os 12 canais do tabuleiro preservando a geometria 8x8
        self.conv1 = nn.Conv2d(in_channels=12, out_channels=32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3, padding=1)
        
        # 2. Tomada de Decisão / Avaliação (Camadas Densas)
        # 64 mapas de características x 8 linhas x 8 colunas = 4096 conexões
        self.fc1 = nn.Linear(64 * 8 * 8, 128)
        self.fc2 = nn.Linear(128, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Define o fluxo de dados (forward pass) através da rede.
        """
        # Entrada: (batch_size, 12, 8, 8)
        x = F.relu(self.conv1(x))   # -> (batch_size, 32, 8, 8)
        x = F.relu(self.conv2(x))   # -> (batch_size, 64, 8, 8)
        
        # Achata a matriz 3D em um vetor 1D por amostra
        x = x.view(-1, 64 * 8 * 8)   # -> (batch_size, 4096)
        
        # Camadas totalmente conectadas
        x = F.relu(self.fc1(x))     # -> (batch_size, 128)
        x = torch.tanh(self.fc2(x)) # -> (batch_size, 1) no intervalo [-1.0, 1.0]
        
        return x