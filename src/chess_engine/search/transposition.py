
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum

import chess
import chess.polyglot


MATE_SCORE = 100_000
MATE_THRESHOLD = MATE_SCORE - 1_000


class BoundType(Enum):
    EXACT = "exact"
    LOWER = "lower"
    UPPER = "upper"


@dataclass(frozen=True)
class TranspositionEntry:
    depth: int
    score: int
    bound: BoundType
    best_move: chess.Move | None = None


PositionKey = tuple[int, int, tuple[chess.Move, ...]]


class TranspositionTable:
    """
    Tabela de transposição com limite de memória.

    Usa hash Zobrist e o relógio dos 50 movimentos.

    Preserva o histórico desde o último lance que
    zerou o relógio, protegendo as regras de repetição.

    Históricos anteriores a esse lance não precisam
    participar da chave.
    """

    def __init__(self, max_entries: int = 20_000):
        if max_entries < 1:
            raise ValueError(
                "max_entries deve ser pelo menos 1."
            )

        self.max_entries = max_entries

        self._entries: OrderedDict[
            PositionKey, TranspositionEntry
        ] = OrderedDict()

        self.hits = 0
        self.misses = 0
        self.stores = 0

    @staticmethod
    def make_key(board: chess.Board) -> PositionKey:
        position_hash = chess.polyglot.zobrist_hash(board)

        halfmove_clock = board.halfmove_clock

        # Apenas os movimentos desde o último lance
        # que zerou o relógio são relevantes para
        # possíveis repetições futuras.
        if halfmove_clock > 0:
            reversible_history = tuple(
                board.move_stack[-halfmove_clock:]
            )
        else:
            reversible_history = ()

        return (
            position_hash,
            halfmove_clock,
            reversible_history,
        )

    @staticmethod
    def _encode_score(score: int, ply: int) -> int:
        if score >= MATE_THRESHOLD:
            return score + ply

        if score <= -MATE_THRESHOLD:
            return score - ply

        return score

    @staticmethod
    def _decode_score(score: int, ply: int) -> int:
        if score >= MATE_THRESHOLD:
            return score - ply

        if score <= -MATE_THRESHOLD:
            return score + ply

        return score

    def get(
        self,
        board: chess.Board,
        ply: int = 0,
    ) -> TranspositionEntry | None:
        key = self.make_key(board)
        entry = self._entries.get(key)

        if entry is None:
            self.misses += 1
            return None

        self.hits += 1
        self._entries.move_to_end(key)

        return TranspositionEntry(
            depth=entry.depth,
            score=self._decode_score(entry.score, ply),
            bound=entry.bound,
            best_move=entry.best_move,
        )

    def store(
        self,
        board: chess.Board,
        depth: int,
        score: int,
        bound: BoundType,
        best_move: chess.Move | None = None,
        ply: int = 0,
    ) -> None:
        key = self.make_key(board)
        previous = self._entries.get(key)

        if previous is not None and previous.depth > depth:
            self._entries.move_to_end(key)
            return

        self._entries[key] = TranspositionEntry(
            depth=depth,
            score=self._encode_score(score, ply),
            bound=bound,
            best_move=best_move,
        )

        self._entries.move_to_end(key)
        self.stores += 1

        if len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()
        self.reset_stats()

    def reset_stats(self) -> None:
        self.hits = 0
        self.misses = 0
        self.stores = 0

    def __len__(self) -> int:
        return len(self._entries)

    def stats(self) -> dict[str, int | float]:
        total = self.hits + self.misses

        return {
            "entries": len(self._entries),
            "hits": self.hits,
            "misses": self.misses,
            "stores": self.stores,
            "hit_rate": (
                self.hits / total if total else 0.0
            ),
        }
