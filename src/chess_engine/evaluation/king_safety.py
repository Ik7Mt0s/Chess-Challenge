
import chess

from chess_engine.evaluation.heuristic import HeuristicEvaluator


class KingSafetyHeuristicEvaluator(HeuristicEvaluator):
    """
    Variante experimental da heurística existente.

    Penaliza enfraquecimentos de peões próximos ao
    abrigo do rei, principalmente durante a abertura.

    Mantém a avaliação original e acrescenta apenas
    um componente de segurança.
    """

    EARLY_PHASE_MIN = 12

    # Custo por casa avançada além da posição inicial.
    WING_PAWN_ADVANCE_PENALTY = 12

    # Rei sem roque, ainda exposto no centro.
    UNCASTLED_EXPOSURE_PENALTY = 12

    # Perda de direitos de roque com rei no centro.
    LOST_CASTLING_RIGHTS_PENALTY = 28

    def evaluate(self, board: chess.Board) -> int:
        base = super().evaluate(board)
        phase = self._game_phase(board)

        if phase < self.EARLY_PHASE_MIN:
            return base

        white_penalty = self._king_exposure(
            board, chess.WHITE, phase
        )
        black_penalty = self._king_exposure(
            board, chess.BLACK, phase
        )

        return base - white_penalty + black_penalty

    @classmethod
    def _king_exposure(
        cls,
        board: chess.Board,
        color: bool,
        phase: int,
    ) -> int:
        king = board.king(color)

        if king is None:
            return 0

        king_file = chess.square_file(king)
        king_rank = chess.square_rank(king)
        home_rank = 0 if color == chess.WHITE else 7

        phase_factor = (
            phase - cls.EARLY_PHASE_MIN
        ) / (cls.MAX_PHASE - cls.EARLY_PHASE_MIN)

        phase_factor = max(0.0, min(1.0, phase_factor))

        on_home_rank = king_rank == home_rank
        king_central = king_file in (3, 4)

        if king_file >= 5:
            relevant_files = (5, 6, 7)
        elif king_file <= 2:
            relevant_files = (0, 1, 2)
        else:
            # Com o rei centralizado, olhamos a ala
            # em que ele ainda poderia rocar.
            kingside = board.has_kingside_castling_rights(color)
            queenside = board.has_queenside_castling_rights(color)

            if kingside:
                relevant_files = (5, 6, 7)
            elif queenside:
                relevant_files = (0, 1, 2)
            else:
                relevant_files = (5, 6, 7)

        penalty = 0

        own_pawns = board.pieces(chess.PAWN, color)

        for file in relevant_files:
            pawns_on_file = [
                square
                for square in own_pawns
                if chess.square_file(square) == file
            ]

            if not pawns_on_file:
                # Não duplicamos integralmente a
                # penalidade de coluna aberta já
                # presente na heurística original.
                penalty += 8
                continue

            if color == chess.WHITE:
                most_protective = min(
                    chess.square_rank(sq)
                    for sq in pawns_on_file
                )
                advanced = max(0, most_protective - 1)
            else:
                most_protective = max(
                    chess.square_rank(sq)
                    for sq in pawns_on_file
                )
                advanced = max(0, 6 - most_protective)

            penalty += (
                advanced
                * cls.WING_PAWN_ADVANCE_PENALTY
            )

        if king_central and on_home_rank:
            penalty += cls.UNCASTLED_EXPOSURE_PENALTY

            if not (
                board.has_kingside_castling_rights(color)
                or board.has_queenside_castling_rights(color)
            ):
                penalty += cls.LOST_CASTLING_RIGHTS_PENALTY

        return int(penalty * phase_factor)
