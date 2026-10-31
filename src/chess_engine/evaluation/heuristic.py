import chess

from chess_engine.evaluation.base import PositionEvaluator


def _center_score(file: int, rank: int) -> int:
    distance = (
        min(abs(file - 3), abs(file - 4))
        + min(abs(rank - 3), abs(rank - 4))
    )
    return 6 - distance


def _make_piece_square_tables() -> dict[int, tuple[tuple[int, ...], ...]]:
    """Precalcula una tabla por pieza y fase (0..24)."""
    tables = {}

    for piece_type in (
        chess.PAWN,
        chess.KNIGHT,
        chess.BISHOP,
        chess.ROOK,
        chess.QUEEN,
        chess.KING,
    ):
        phase_tables = []

        for phase in range(25):
            square_scores = []

            for square in chess.SQUARES:
                file = chess.square_file(square)
                rank = chess.square_rank(square)
                center = _center_score(file, rank)

                middle_game = 0
                end_game = 0

                if piece_type == chess.PAWN:
                    middle_game = rank * 5 + center * 2
                    end_game = rank * 9 + center * 2
                elif piece_type == chess.KNIGHT:
                    middle_game = center * 10
                    end_game = center * 8
                elif piece_type == chess.BISHOP:
                    middle_game = center * 5 + rank * 2
                    end_game = center * 6 + rank * 2
                elif piece_type == chess.ROOK:
                    middle_game = rank * 3 + (4 if rank == 6 else 0)
                    end_game = rank * 4 + center
                elif piece_type == chess.KING:
                    middle_game = -center * 7
                    end_game = center * 9

                square_scores.append(
                    (
                        middle_game * phase
                        + end_game * (24 - phase)
                    ) // 24
                )

            phase_tables.append(tuple(square_scores))

        tables[piece_type] = tuple(phase_tables)

    return tables


def _make_passed_pawn_masks() -> dict[bool, tuple[int, ...]]:
    masks = {chess.WHITE: [], chess.BLACK: []}

    for color in (chess.WHITE, chess.BLACK):
        for square in chess.SQUARES:
            file = chess.square_file(square)
            rank = chess.square_rank(square)
            files = range(max(0, file - 1), min(7, file + 1) + 1)
            ranks = range(rank + 1, 8) if color == chess.WHITE else range(rank)
            mask = 0

            for target_file in files:
                for target_rank in ranks:
                    mask |= chess.BB_SQUARES[
                        chess.square(target_file, target_rank)
                    ]

            masks[color].append(mask)

    return {color: tuple(mask) for color, mask in masks.items()}


PIECE_SQUARE_TABLES = _make_piece_square_tables()
PASSED_PAWN_MASKS = _make_passed_pawn_masks()


class HeuristicEvaluator(PositionEvaluator):

    PIECE_VALUES = {
        chess.PAWN: 100,
        chess.KNIGHT: 320,
        chess.BISHOP: 330,
        chess.ROOK: 500,
        chess.QUEEN: 900,
        chess.KING: 0,
    }

    PHASE_WEIGHTS = {
        chess.KNIGHT: 1,
        chess.BISHOP: 1,
        chess.ROOK: 2,
        chess.QUEEN: 4,
    }
    MAX_PHASE = 24

    MOBILITY_WEIGHTS = {
        chess.KNIGHT: 4,
        chess.BISHOP: 3,
        chess.ROOK: 2,
        chess.QUEEN: 1,
    }
    MAX_MOBILITY = 14

    DOUBLED_PAWN_PENALTY = 16
    ISOLATED_PAWN_PENALTY = 12
    PASSED_PAWN_BONUS = (0, 0, 8, 16, 28, 45, 70, 105)

    def evaluate(self, board: chess.Board) -> int:
        """
        Retorna uma pontuação positiva para vantagem das brancas.
        """
        phase = self._game_phase(board)
        white_score = 0
        black_score = 0

        for color in (chess.WHITE, chess.BLACK):
            side_score = 0

            for piece_type, material in self.PIECE_VALUES.items():
                pieces = board.pieces_mask(piece_type, color)
                for square in chess.scan_forward(pieces):
                    side_score += material
                    side_score += self._piece_square_score(
                        piece_type,
                        square,
                        color,
                        phase,
                    )

            side_score += self._pawn_structure(board, color)
            side_score += self._king_safety(board, color, phase)
            side_score += self._mobility(board, color)

            if color == chess.WHITE:
                white_score = side_score
            else:
                black_score = side_score

        return white_score - black_score

    @classmethod
    def _game_phase(cls, board: chess.Board) -> int:
        """Retorna 0 no final e 24 na posição inicial."""
        phase = 0

        for piece_type, weight in cls.PHASE_WEIGHTS.items():
            white_count = board.pieces_mask(
                piece_type,
                chess.WHITE,
            ).bit_count()
            black_count = board.pieces_mask(
                piece_type,
                chess.BLACK,
            ).bit_count()
            phase += (white_count + black_count) * weight

        return min(phase, cls.MAX_PHASE)

    @classmethod
    def _piece_square_score(
        cls,
        piece_type: chess.PieceType,
        square: chess.Square,
        color: chess.Color,
        phase: int,
    ) -> int:
        oriented_square = (
            square if color == chess.WHITE else chess.square_mirror(square)
        )
        return PIECE_SQUARE_TABLES[piece_type][phase][oriented_square]

    @classmethod
    def _pawn_structure(
        cls,
        board: chess.Board,
        color: chess.Color,
    ) -> int:
        pawns = board.pieces_mask(chess.PAWN, color)
        enemy_pawns = board.pieces_mask(chess.PAWN, not color)
        pawns_by_file = [
            (pawns & file_mask).bit_count()
            for file_mask in chess.BB_FILES
        ]

        score = 0

        for file, count in enumerate(pawns_by_file):
            if count > 1:
                score -= (count - 1) * cls.DOUBLED_PAWN_PENALTY

            if count == 0:
                continue

            has_neighbor = (
                file > 0 and pawns_by_file[file - 1] > 0
            ) or (
                file < 7 and pawns_by_file[file + 1] > 0
            )

            if not has_neighbor:
                score -= count * cls.ISOLATED_PAWN_PENALTY

        for square in chess.scan_forward(pawns):
            file = chess.square_file(square)
            rank = chess.square_rank(square)
            relative_rank = rank if color == chess.WHITE else 7 - rank

            if not enemy_pawns & PASSED_PAWN_MASKS[color][square]:
                score += cls.PASSED_PAWN_BONUS[relative_rank]

        return score

    @classmethod
    def _king_safety(
        cls,
        board: chess.Board,
        color: chess.Color,
        phase: int,
    ) -> int:
        king = board.king(color)

        if king is None or phase == 0:
            return 0

        king_file = chess.square_file(king)
        king_rank = chess.square_rank(king)
        direction = 1 if color == chess.WHITE else -1
        shield_rank = king_rank + direction
        shield = 0

        if 0 <= shield_rank < 8:
            for file in range(max(0, king_file - 1), min(7, king_file + 1) + 1):
                pawn = board.piece_at(chess.square(file, shield_rank))
                if pawn == chess.Piece(chess.PAWN, color):
                    shield += 1

        enemy = not color
        pressure = min(
            4,
            board.attackers_mask(enemy, king).bit_count() * 2,
        )

        for file in range(max(0, king_file - 1), min(7, king_file + 1) + 1):
            for rank in range(max(0, king_rank - 1), min(7, king_rank + 1) + 1):
                if file == king_file and rank == king_rank:
                    continue

                attackers = board.attackers_mask(
                    enemy,
                    chess.square(file, rank),
                ).bit_count()
                if attackers:
                    pressure += min(2, attackers)

        raw_score = shield * 12 - min(pressure, 8) * 7
        return raw_score * phase // cls.MAX_PHASE

    @classmethod
    def _mobility(
        cls,
        board: chess.Board,
        color: chess.Color,
    ) -> int:
        own_pieces = board.occupied_co[color]
        score = 0

        for piece_type, weight in cls.MOBILITY_WEIGHTS.items():
            pieces = board.pieces_mask(piece_type, color)
            for square in chess.scan_forward(pieces):
                destinations = board.attacks_mask(square) & ~own_pieces
                mobility = min(
                    destinations.bit_count(),
                    cls.MAX_MOBILITY,
                )
                score += mobility * weight

        return score
