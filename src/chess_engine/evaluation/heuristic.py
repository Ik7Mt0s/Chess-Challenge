
"""Avaliação estática em centipawns da perspectiva das brancas.

Compatível com HybridEvaluator e com a arquitetura original.
Não gera lances, não modifica o tabuleiro e não executa buscas.
"""

import chess

from chess_engine.evaluation.base import PositionEvaluator


def _center_score(file: int, rank: int) -> int:
    return (
        6
        - min(abs(file - 3), abs(file - 4))
        - min(abs(rank - 3), abs(rank - 4))
    )


def _make_piece_square_tables():
    tables = {}

    for piece_type in (
        chess.PAWN,
        chess.KNIGHT,
        chess.BISHOP,
        chess.ROOK,
        chess.QUEEN,
        chess.KING,
    ):
        phases = []

        for phase in range(25):
            values = []

            for square in chess.SQUARES:
                file = chess.square_file(square)
                rank = chess.square_rank(square)
                center = _center_score(file, rank)

                mg = eg = 0

                if piece_type == chess.PAWN:
                    mg = rank * 5 + center * 2
                    eg = rank * 9 + center * 2

                elif piece_type == chess.KNIGHT:
                    mg = center * 10
                    eg = center * 8

                elif piece_type == chess.BISHOP:
                    mg = center * 5 + rank * 2
                    eg = center * 6 + rank * 2

                elif piece_type == chess.ROOK:
                    mg = rank * 3 + (4 if rank == 6 else 0)
                    eg = rank * 4 + center

                elif piece_type == chess.KING:
                    mg = -center * 7
                    eg = center * 9

                values.append(
                    (mg * phase + eg * (24 - phase)) // 24
                )

            phases.append(tuple(values))

        tables[piece_type] = tuple(phases)

    return tables


def _make_passed_pawn_masks():
    masks = {
        chess.WHITE: [],
        chess.BLACK: [],
    }

    challenges = {
        chess.WHITE: [],
        chess.BLACK: [],
    }

    for color in (chess.WHITE, chess.BLACK):
        for square in chess.SQUARES:
            file = chess.square_file(square)
            rank = chess.square_rank(square)

            ranks = (
                range(rank + 1, 8)
                if color == chess.WHITE
                else range(rank)
            )

            passed = 0
            challenge = 0

            for f in range(
                max(0, file - 1),
                min(7, file + 1) + 1,
            ):
                for r in ranks:
                    bit = chess.BB_SQUARES[
                        chess.square(f, r)
                    ]

                    passed |= bit

                    if f != file:
                        challenge |= bit

            masks[color].append(passed)
            challenges[color].append(challenge)

    return (
        {
            color: tuple(values)
            for color, values in masks.items()
        },
        {
            color: tuple(values)
            for color, values in challenges.items()
        },
    )


def _make_king_masks():
    zones = []

    shields = {
        chess.WHITE: [],
        chess.BLACK: [],
    }

    for square in chess.SQUARES:
        file = chess.square_file(square)
        rank = chess.square_rank(square)

        zone = []

        for f in range(
            max(0, file - 1),
            min(7, file + 1) + 1,
        ):
            for r in range(
                max(0, rank - 1),
                min(7, rank + 1) + 1,
            ):
                if (f, r) != (file, rank):
                    zone.append(chess.square(f, r))

        zones.append(tuple(zone))

        for color in (chess.WHITE, chess.BLACK):
            shield_rank = rank + (
                1 if color == chess.WHITE else -1
            )

            mask = 0

            if 0 <= shield_rank < 8:
                for f in range(
                    max(0, file - 1),
                    min(7, file + 1) + 1,
                ):
                    mask |= chess.BB_SQUARES[
                        chess.square(f, shield_rank)
                    ]

            shields[color].append(mask)

    return (
        tuple(zones),
        {
            color: tuple(values)
            for color, values in shields.items()
        },
    )


PIECE_SQUARE_TABLES = _make_piece_square_tables()

(
    PASSED_PAWN_MASKS,
    OUTPOST_CHALLENGE_MASKS,
) = _make_passed_pawn_masks()

KING_ZONE_SQUARES, KING_SHIELD_MASKS = _make_king_masks()


class HeuristicEvaluator(PositionEvaluator):
    """Avaliação determinística: positiva para as brancas."""

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

    PASSED_PAWN_BONUS = (
        0, 0, 8, 16, 28, 45, 70, 105
    )

    SUPPORTED_PASSED_PAWN_BONUS = 12
    CONNECTED_PASSED_PAWN_BONUS = 8
    BLOCKED_PASSED_PAWN_PENALTY = 18

    BISHOP_PAIR_BONUS = 30

    ROOK_OPEN_FILE_BONUS = 22
    ROOK_HALF_OPEN_FILE_BONUS = 12
    ROOK_SEVENTH_RANK_BONUS = 12

    KNIGHT_OUTPOST_BONUS = 18

    HANGING_PIECE_PENALTY = {
        chess.KNIGHT: 24,
        chess.BISHOP: 24,
        chess.ROOK: 30,
        chess.QUEEN: 36,
    }

    PAWN_THREAT_PENALTY = {
        chess.KNIGHT: 12,
        chess.BISHOP: 12,
        chess.ROOK: 20,
        chess.QUEEN: 24,
    }

    KING_ENDGAME_PAWN_SUPPORT = 5
    KING_ENDGAME_ENEMY_PAWN_PRESSURE = 3

    KING_ATTACK_WEIGHTS = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 4,
        chess.QUEEN: 6,
    }

    MINOR_TRAPPED_PENALTY = 12
    KING_OPEN_FILE_PENALTY = 10
    CONNECTED_PAWN_BONUS = 3

    def evaluate(self, board: chess.Board) -> int:
        """
        Retorna centipawns da perspectiva das brancas.

        Não altera o tabuleiro nem executa busca.
        """
        phase = self._game_phase(board)

        pawns = {
            color: board.pieces_mask(chess.PAWN, color)
            for color in (chess.WHITE, chess.BLACK)
        }

        pawn_attacks = {
            color: self._pawn_attacks(board, color)
            for color in (chess.WHITE, chess.BLACK)
        }

        white_score = self._side_score(
            board,
            chess.WHITE,
            phase,
            pawn_attacks[chess.BLACK],
        )

        black_score = self._side_score(
            board,
            chess.BLACK,
            phase,
            pawn_attacks[chess.WHITE],
        )

        score = white_score - black_score

        # Um lado com material insuficiente não pode
        # produzir uma vitória apenas por atividade.
        # Mantemos o empate apenas quando o tabuleiro
        # reconhece insuficiência material da posição.
        if not (
            pawns[chess.WHITE] | pawns[chess.BLACK]
        ):
            if board.is_insufficient_material():
                return 0

        return score

    def _side_score(
        self,
        board,
        color,
        phase,
        enemy_pawn_attacks,
    ):
        return (
            self._piece_activity_score(
                board,
                color,
                phase,
                enemy_pawn_attacks,
            )
            + self._pawn_structure(
                board,
                color,
                phase,
            )
            + self._king_safety(
                board,
                color,
                phase,
            )
        )

    @classmethod
    def _game_phase(cls, board):
        return min(
            cls.MAX_PHASE,
            sum(
                (
                    board.pieces_mask(
                        piece_type, chess.WHITE
                    ).bit_count()
                    + board.pieces_mask(
                        piece_type, chess.BLACK
                    ).bit_count()
                ) * weight
                for piece_type, weight
                in cls.PHASE_WEIGHTS.items()
            ),
        )

    @classmethod
    def _piece_square_score(
        cls,
        piece_type,
        square,
        color,
        phase,
    ):
        oriented = (
            square
            if color == chess.WHITE
            else chess.square_mirror(square)
        )

        return PIECE_SQUARE_TABLES[
            piece_type
        ][phase][oriented]

    @classmethod
    def _pawn_attacks(cls, board, color):
        attacks = 0

        pawns = board.pieces_mask(
            chess.PAWN, color
        )

        for square in chess.scan_forward(pawns):
            attacks |= chess.BB_PAWN_ATTACKS[
                color
            ][square]

        return attacks

    @classmethod
    def _piece_activity_score(
        cls,
        board,
        color,
        phase,
        enemy_pawn_attacks=None,
    ):
        enemy = not color

        if enemy_pawn_attacks is None:
            enemy_pawn_attacks = cls._pawn_attacks(
                board, enemy
            )

        own_occupied = board.occupied_co[color]

        own_pawns = board.pieces_mask(
            chess.PAWN, color
        )

        enemy_pawns = board.pieces_mask(
            chess.PAWN, enemy
        )

        score = (
            cls.BISHOP_PAIR_BONUS
            if board.pieces_mask(
                chess.BISHOP, color
            ).bit_count() >= 2
            else 0
        )

        for piece_type, material in cls.PIECE_VALUES.items():
            pieces = board.pieces_mask(
                piece_type, color
            )

            mobility_weight = cls.MOBILITY_WEIGHTS.get(
                piece_type, 0
            )

            for square in chess.scan_forward(pieces):
                score += material

                score += cls._piece_square_score(
                    piece_type,
                    square,
                    color,
                    phase,
                )

                # Mobilidade das peças.
                if mobility_weight:
                    destinations = (
                        board.attacks_mask(square)
                        & ~own_occupied
                    )

                    # Para cavalos e bispos, casas
                    # atacadas por peões são menos úteis.
                    if piece_type in (
                        chess.KNIGHT,
                        chess.BISHOP,
                    ):
                        destinations &= ~enemy_pawn_attacks

                    mobility = min(
                        destinations.bit_count(),
                        cls.MAX_MOBILITY,
                    )

                    score += (
                        mobility * mobility_weight
                    )

                    # Mobilidade extremamente limitada
                    # pode indicar uma peça mal colocada.
                    if (
                        piece_type in (
                            chess.KNIGHT,
                            chess.BISHOP,
                        )
                        and mobility <= 2
                    ):
                        score -= (
                            cls.MINOR_TRAPPED_PENALTY
                            * phase
                            // cls.MAX_PHASE
                        )

                # Atividade das torres.
                if piece_type == chess.ROOK:
                    file = chess.square_file(square)
                    file_mask = chess.BB_FILES[file]

                    if not (own_pawns & file_mask):
                        if enemy_pawns & file_mask:
                            score += (
                                cls.ROOK_HALF_OPEN_FILE_BONUS
                            )
                        else:
                            score += (
                                cls.ROOK_OPEN_FILE_BONUS
                            )

                    rank = chess.square_rank(square)
                    relative_rank = (
                        rank if color == chess.WHITE
                        else 7 - rank
                    )

                    if relative_rank == 6:
                        enemy_king = board.king(enemy)

                        enemy_back_rank = (
                            chess.BB_RANKS[6]
                            if color == chess.WHITE
                            else chess.BB_RANKS[1]
                        )

                        has_pawn_targets = bool(
                            enemy_pawns & enemy_back_rank
                        )

                        king_is_behind = (
                            enemy_king is not None
                            and (
                                chess.square_rank(enemy_king)
                                if color == chess.WHITE
                                else 7 - chess.square_rank(
                                    enemy_king
                                )
                            ) >= 6
                        )

                        if (
                            has_pawn_targets
                            or king_is_behind
                        ):
                            score += (
                                cls.ROOK_SEVENTH_RANK_BONUS
                            )

                # Postos avançados dos cavalos.
                elif piece_type == chess.KNIGHT:
                    score += cls._knight_outpost(
                        board,
                        color,
                        square,
                        own_pawns,
                    )

                # Vulnerabilidade posicional.
                if piece_type in cls.HANGING_PIECE_PENALTY:
                    score += cls._piece_safety(
                        board,
                        color,
                        square,
                        piece_type,
                        enemy_pawn_attacks,
                    )

        return score

    @classmethod
    def _knight_outpost(
        cls,
        board,
        color,
        square,
        own_pawns,
    ):
        rank = chess.square_rank(square)

        relative_rank = (
            rank if color == chess.WHITE
            else 7 - rank
        )

        if not 3 <= relative_rank <= 5:
            return 0

        # Precisa estar protegido por um peão amigo.
        support = (
            board.attackers_mask(color, square)
            & own_pawns
        )

        if not support:
            return 0

        enemy_pawns = board.pieces_mask(
            chess.PAWN, not color
        )

        # Só importam os peões adversários nas
        # colunas vizinhas que podem avançar
        # para atacar o posto.
        if (
            enemy_pawns
            & OUTPOST_CHALLENGE_MASKS[color][square]
        ):
            return 0

        return cls.KNIGHT_OUTPOST_BONUS

    @classmethod
    def _piece_safety(
        cls,
        board,
        color,
        square,
        piece_type,
        enemy_pawn_attacks,
    ):
        square_mask = chess.BB_SQUARES[square]

        # Ameaça de peão contra peça mais valiosa.
        # Não presumimos perda material completa,
        # porque a busca tática deve verificar isso.
        if enemy_pawn_attacks & square_mask:
            return -cls.PAWN_THREAT_PENALTY[
                piece_type
            ]

        attackers = board.attackers_mask(
            not color, square
        )

        if not attackers:
            return 0

        defenders = board.attackers_mask(
            color, square
        )

        if not defenders:
            return -cls.HANGING_PIECE_PENALTY[
                piece_type
            ]

        return 0

    @classmethod
    def _pawn_structure(
        cls,
        board,
        color,
        phase=None,
    ):
        pawns = board.pieces_mask(
            chess.PAWN, color
        )

        enemy_pawns = board.pieces_mask(
            chess.PAWN, not color
        )

        pawns_by_file = [
            (pawns & file_mask).bit_count()
            for file_mask in chess.BB_FILES
        ]

        score = 0

        # Peões dobrados e isolados.
        for file, count in enumerate(pawns_by_file):
            if count > 1:
                score -= (
                    (count - 1)
                    * cls.DOUBLED_PAWN_PENALTY
                )

            if not count:
                continue

            has_neighbor = (
                file > 0
                and pawns_by_file[file - 1] > 0
            ) or (
                file < 7
                and pawns_by_file[file + 1] > 0
            )

            if not has_neighbor:
                score -= (
                    count * cls.ISOLATED_PAWN_PENALTY
                )

        own_king = board.king(color)
        enemy_king = board.king(not color)

        endgame_factor = (
            0
            if phase is None
            else cls.MAX_PHASE - phase
        )

        for square in chess.scan_forward(pawns):
            file = chess.square_file(square)
            rank = chess.square_rank(square)

            relative_rank = (
                rank if color == chess.WHITE
                else 7 - rank
            )

            # Peões conectados, mesmo quando
            # ainda não são passados.
            adjacent_files = (
                chess.BB_FILES[file - 1]
                if file > 0
                else 0
            )

            if file < 7:
                adjacent_files |= chess.BB_FILES[
                    file + 1
                ]

            neighbors = pawns & adjacent_files

            connected = any(
                abs(
                    chess.square_rank(other) - rank
                ) <= 1
                for other in chess.scan_forward(neighbors)
            )

            if connected:
                score += cls.CONNECTED_PAWN_BONUS

            # Peão não passado.
            if (
                enemy_pawns
                & PASSED_PAWN_MASKS[color][square]
            ):
                continue

            bonus = cls.PASSED_PAWN_BONUS[
                relative_rank
            ]

            # Peão passado protegido.
            support = (
                board.attackers_mask(color, square)
                & pawns
            )

            if support:
                bonus += (
                    cls.SUPPORTED_PASSED_PAWN_BONUS
                )

            # Peões passados conectados.
            if connected:
                bonus += (
                    cls.CONNECTED_PASSED_PAWN_BONUS
                )

            next_square = square + (
                8 if color == chess.WHITE else -8
            )

            blocked = (
                0 <= next_square < 64
                and bool(
                    board.occupied
                    & chess.BB_SQUARES[next_square]
                )
            )

            if blocked:
                bonus -= (
                    cls.BLOCKED_PASSED_PAWN_PENALTY
                )

                # Reduz o bônus excessivo de
                # peões avançados, mas bloqueados.
                bonus = min(
                    bonus,
                    cls.PASSED_PAWN_BONUS[
                        relative_rank
                    ] // 2,
                )

            # Apoio do rei nos finais.
            if endgame_factor > 0:
                target = (
                    next_square
                    if 0 <= next_square < 64
                    else square
                )

                if own_king is not None:
                    own_distance = (
                        chess.square_distance(
                            own_king,
                            target,
                        )
                    )

                    bonus += (
                        max(0, 5 - own_distance)
                        * cls.KING_ENDGAME_PAWN_SUPPORT
                        * endgame_factor
                        // cls.MAX_PHASE
                    )

                if enemy_king is not None:
                    promotion_square = chess.square(
                        file,
                        7 if color == chess.WHITE else 0,
                    )

                    enemy_distance = (
                        chess.square_distance(
                            enemy_king,
                            promotion_square,
                        )
                    )

                    bonus += (
                        min(enemy_distance, 6)
                        * cls.KING_ENDGAME_ENEMY_PAWN_PRESSURE
                        * endgame_factor
                        // cls.MAX_PHASE
                    )

            score += bonus

        return score

    @classmethod
    def _king_safety(
        cls,
        board,
        color,
        phase,
    ):
        king = board.king(color)

        if king is None or phase == 0:
            return 0

        enemy = not color

        own_pawns = board.pieces_mask(
            chess.PAWN, color
        )

        shield = (
            own_pawns
            & KING_SHIELD_MASKS[color][king]
        ).bit_count()

        attackers_seen = board.attackers_mask(
            enemy, king
        )

        zone_pressure = 0

        # Pressão sobre as casas próximas ao rei.
        for square in KING_ZONE_SQUARES[king]:
            attackers = board.attackers_mask(
                enemy, square
            )

            if attackers:
                zone_pressure += min(
                    2,
                    attackers.bit_count(),
                )

                attackers_seen |= attackers

        attacking_pieces = 0
        attack_strength = 0

        for piece_type, weight in cls.KING_ATTACK_WEIGHTS.items():
            count = (
                attackers_seen
                & board.pieces_mask(
                    piece_type, enemy
                )
            ).bit_count()

            attack_strength += count * weight

            if piece_type != chess.PAWN:
                attacking_pieces += count

        coordination = min(
            3,
            max(1, attacking_pieces),
        )

        pressure = min(
            160,
            zone_pressure * 3
            + attack_strength * coordination * 3,
        )

        # O rei em uma coluna sem peões próprios
        # pode ficar mais exposto às peças pesadas.
        king_file = chess.square_file(king)
        king_file_mask = chess.BB_FILES[king_file]

        open_file_penalty = (
            0
            if own_pawns & king_file_mask
            else cls.KING_OPEN_FILE_PENALTY
        )

        raw_score = (
            shield * 12
            - pressure
            - open_file_penalty
        )

        # Segurança pesa menos no final.
        return (
            raw_score * phase
            // cls.MAX_PHASE
        )

    @classmethod
    def _mobility(
        cls,
        board,
        color,
    ):
        """Método auxiliar mantido por compatibilidade."""
        own_occupied = board.occupied_co[color]

        enemy_pawn_attacks = cls._pawn_attacks(
            board, not color
        )

        score = 0

        for piece_type, weight in cls.MOBILITY_WEIGHTS.items():
            pieces = board.pieces_mask(
                piece_type, color
            )

            for square in chess.scan_forward(pieces):
                destinations = (
                    board.attacks_mask(square)
                    & ~own_occupied
                )

                if piece_type in (
                    chess.KNIGHT,
                    chess.BISHOP,
                ):
                    destinations &= ~enemy_pawn_attacks

                mobility = min(
                    destinations.bit_count(),
                    cls.MAX_MOBILITY,
                )

                score += mobility * weight

        return score
