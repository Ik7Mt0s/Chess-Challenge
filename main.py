import chess


def main():
    board = chess.Board()

    print("=== Chess Challenge III ===")
    print("Tabuleiro inicial:")
    print(board)

    print("\nJogadas legais:")
    for move in board.legal_moves:
        print(move.uci())


if __name__ == "__main__":
    main()
