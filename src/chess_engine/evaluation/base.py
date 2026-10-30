from abc import ABC, abstractmethod

import chess


class PositionEvaluator(ABC):

    @abstractmethod
    def evaluate(self, board: chess.Board) -> int:
        """
        Retorna a avaliação em centipeões.

        Positivo: vantagem das brancas.
        Negativo: vantagem das pretas.
        """
        raise NotImplementedError