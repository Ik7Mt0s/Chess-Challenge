
from collections import OrderedDict
from pathlib import Path

import chess
import chess.polyglot
import torch

from chess_engine.evaluation.base import PositionEvaluator
from chess_engine.evaluation.heuristic import HeuristicEvaluator
from chess_engine.evaluation.king_safety import (
    KingSafetyHeuristicEvaluator,
)
from chess_engine.neural.model import SimpleChessNet
from chess_engine.neural.representation import board_to_tensor


class NeuralEvaluator(PositionEvaluator):
    def __init__(
        self,
        model_path: str | Path | None = "weights/simple_chess_net.pth",
        model: torch.nn.Module | None = None,
    ):
        if model is not None:
            self.model = model
        else:
            self.model = SimpleChessNet()

            if model_path is None:
                raise ValueError(
                    "Informe o caminho do modelo neural."
                )

            path = Path(model_path)

            if not path.is_file():
                raise FileNotFoundError(
                    f"Modelo neural não encontrado: {path}"
                )

            self.model.load_state_dict(
                torch.load(
                    path,
                    map_location="cpu",
                    weights_only=True,
                )
            )

        self.model.eval()

    def evaluate(self, board: chess.Board) -> int:
        tensor = board_to_tensor(
            board,
            flip_black_perspective=True,
        ).unsqueeze(0)

        with torch.inference_mode():
            normalized_score = self.model(tensor).item()

        score = int(normalized_score * 1000)

        return (
            score
            if board.turn == chess.WHITE
            else -score
        )


class HybridEvaluator(PositionEvaluator):
    def __init__(
        self,
        heuristic: PositionEvaluator | None = None,
        neural: PositionEvaluator | None = None,
        weight_neural: float = 0.2,
        lazy_threshold: int = 300,
        max_neural_inferences: int | None = 128,
        use_king_safety: bool = False,
        neural_cache_size: int = 4096,
    ):
        if not 0.0 <= weight_neural <= 1.0:
            raise ValueError(
                "weight_neural deve estar entre 0 e 1."
            )

        if (
            max_neural_inferences is not None
            and max_neural_inferences < 0
        ):
            raise ValueError(
                "max_neural_inferences não pode ser negativo."
            )

        if neural_cache_size < 0:
            raise ValueError(
                "neural_cache_size não pode ser negativo."
            )

        if heuristic is not None:
            self.heuristic = heuristic
        elif use_king_safety:
            self.heuristic = KingSafetyHeuristicEvaluator()
        else:
            self.heuristic = HeuristicEvaluator()

        self.neural = (
            neural
            if neural is not None
            else (
                NeuralEvaluator()
                if weight_neural > 0
                else None
            )
        )

        self.weight_neural = weight_neural
        self.lazy_threshold = lazy_threshold
        self.max_neural_inferences = max_neural_inferences
        self.neural_cache_size = neural_cache_size

        self._neural_cache: OrderedDict[int, int] = OrderedDict()

        self.begin_search()

    def begin_search(self) -> None:
        self.neural_inferences = 0
        self.heuristic_evaluations = 0
        self.neural_skipped_budget = 0
        self.neural_skipped_threshold = 0
        self.neural_cache_hits = 0

    def clear_neural_cache(self) -> None:
        self._neural_cache.clear()

    def inference_stats(self) -> dict[str, int]:
        return {
            "neural_inferences": self.neural_inferences,
            "heuristic_evaluations": self.heuristic_evaluations,
            "neural_skipped_budget": self.neural_skipped_budget,
            "neural_skipped_threshold": self.neural_skipped_threshold,
            "neural_cache_hits": self.neural_cache_hits,
            "neural_cache_entries": len(self._neural_cache),
        }

    def _get_cached_neural(
        self, board: chess.Board
    ) -> tuple[int | None, int | None]:
        if self.neural_cache_size == 0:
            return None, None

        key = chess.polyglot.zobrist_hash(board)
        cached = self._neural_cache.get(key)

        if cached is not None:
            self._neural_cache.move_to_end(key)
            self.neural_cache_hits += 1

        return key, cached

    def _store_neural(
        self,
        key: int | None,
        score: int,
    ) -> None:
        if key is None or self.neural_cache_size == 0:
            return

        self._neural_cache[key] = score
        self._neural_cache.move_to_end(key)

        if len(self._neural_cache) > self.neural_cache_size:
            self._neural_cache.popitem(last=False)

    def evaluate(self, board: chess.Board) -> int:
        h_score = self.heuristic.evaluate(board)
        self.heuristic_evaluations += 1

        if self.weight_neural == 0 or self.neural is None:
            return h_score

        if abs(h_score) > self.lazy_threshold:
            self.neural_skipped_threshold += 1
            return h_score

        key, cached = self._get_cached_neural(board)

        if cached is not None:
            n_score = cached
        else:
            if (
                self.max_neural_inferences is not None
                and self.neural_inferences
                >= self.max_neural_inferences
            ):
                self.neural_skipped_budget += 1
                return h_score

            n_score = self.neural.evaluate(board)
            self.neural_inferences += 1

            self._store_neural(key, n_score)

        return int(
            h_score * (1.0 - self.weight_neural)
            + n_score * self.weight_neural
        )
