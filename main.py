import chess

from chess_engine.board import ChessBoard
from chess_engine.engine import ChessEngine


def main():
    game = ChessBoard()
    engine = ChessEngine(max_depth=3)

    print("=== Chess Challenge III ===")
    print("Você joga com as brancas.")
    print("Digite 'sair' para encerrar a partida.")
    print("Digite 'desfazer' para voltar um turno completo.")

    while not game.is_game_over():
        print()
        print(game)
        print()

        if game.board.turn == chess.WHITE:
            notation = input("Sua jogada: ").strip()

            if notation.lower() == "sair":
                print("Partida encerrada.")
                return

            if notation.lower() == "desfazer":
                if len(game.board.move_stack) >= 2:
                    game.undo()
                    game.undo()
                else:
                    print("Não há um turno completo para desfazer.")
                continue

            try:
                game.play(notation)
            except ValueError as exc:
                print(exc)

            continue

        print("Motor pensando...")

        try:
            result = engine.best_move(
                game.board,
                time_limit=2.0,
            )

            san = game.board.san(result.move)
            game.board.push(result.move)

            print(f"Motor jogou: {san}")
            print(f"Profundidade: {result.depth}")
            print(f"Avaliação: {result.score} cp")
            print(f"Tempo: {result.elapsed:.3f}s")

        except Exception as exc:
            print(f"Erro no motor: {exc}")
            return

    print()
    print(game)
    print(f"\nResultado: {game.result()}")


if __name__ == "__main__":
    main()