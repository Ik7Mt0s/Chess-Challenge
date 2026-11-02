from pathlib import Path
import chess
import torch

from chess_engine.evaluation.base import PositionEvaluator
from chess_engine.evaluation.heuristic import HeuristicEvaluator
from chess_engine.neural.model import SimpleChessNet
from chess_engine.neural.representation import board_to_tensor


class NeuralEvaluator(PositionEvaluator):
    """
    Avaliador baseado na rede neural PyTorch (SimpleChessNet).
    Traduz a saída [-1.0, 1.0] da rede para centipeões na perspectiva do jogador ativo.
    """

    def __init__(self, model_path: str | Path | None = "weights/simple_chess_net.pth", model: torch.nn.Module | None = None):
        if model is not None:
            self.model = model
        else:
            self.model = SimpleChessNet()
            path = Path(model_path) if model_path else None
            if path and path.is_file():
                self.model.load_state_dict(torch.load(path, map_location="cpu"))

        # Coloca a rede em modo de avaliação (desativa aprendizado/dropout)
        self.model.eval()

    def evaluate(self, board: chess.Board) -> int:
        """
        Retorna a pontuação da posição em centipeões sob a perspectiva do jogador da vez.
        """
        # Converte o tabuleiro mantendo a perspectiva do jogador ativo
        tensor = board_to_tensor(board, flip_black_perspective=True).unsqueeze(0)

        # Inferência rápida desativando cálculo de gradientes
        with torch.no_grad():
            score_normalized = self.model(tensor).item()

        # Converte o intervalo [-1.0, 1.0] para centipeões (ex: -1000 a +1000 centipeões)
        return int(score_normalized * 1000)


class HybridEvaluator(PositionEvaluator):
    """
    Avaliador Híbrido: Combina a Heurística tradicional com o modelo Neural.
    Utiliza Lazy Evaluation para economizar tempo em posições desbalanceadas.
    """

    def __init__(
        self,
        heuristic: PositionEvaluator | None = None,
        neural: PositionEvaluator | None = None,
        weight_neural: float = 0.2,
        lazy_threshold: int = 300,
    ):
        self.heuristic = heuristic or HeuristicEvaluator()
        self.neural = neural or NeuralEvaluator()
        self.weight_neural = weight_neural
        self.lazy_threshold = lazy_threshold

    def evaluate(self, board: chess.Board) -> int:
        # 1. Executa primeiro a Heurística rápida
        h_score = self.heuristic.evaluate(board)

        # 2. Lazy Evaluation: Se a posição for claramente desequilibrada (> 3 peões),
        # ignora o cálculo neural para poupar tempo no Negamax
        if abs(h_score) > self.lazy_threshold:
            return h_score

        # 3. Em posições equilibradas, consulta a intuição do modelo neural
        n_score = self.neural.evaluate(board)

        # 4. Combina os dois resultados via média ponderada
        combined_score = (h_score * (1.0 - self.weight_neural)) + (n_score * self.weight_neural)
        return int(combined_score)