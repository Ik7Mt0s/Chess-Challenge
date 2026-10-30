import chess


class ChessBoard:
    def __init__(self, fen: str | None = None):
        self.board = chess.Board(fen) if fen else chess.Board()

    def legal_moves(self) -> list[chess.Move]:
        return list(self.board.legal_moves)

    def play(self, notation: str) -> chess.Move:
        notation = notation.strip()

        try:
            move = self.board.parse_san(notation)
        except ValueError:
            try:
                move = self.board.parse_uci(notation)
            except ValueError as exc:
                raise ValueError(
                    f"Movimento inválido ou ilegal: {notation}"
                ) from exc

        self.board.push(move)
        return move

    def undo(self) -> chess.Move:
        if not self.board.move_stack:
            raise ValueError("Não há movimentos para desfazer.")

        return self.board.pop()

    def is_game_over(self) -> bool:
        return self.board.is_game_over(claim_draw=True)

    def result(self) -> str:
        return self.board.result(claim_draw=True)

    def fen(self) -> str:
        return self.board.fen()

    def reset(self) -> None:
        self.board.reset()

    def __str__(self) -> str:
        return str(self.board)