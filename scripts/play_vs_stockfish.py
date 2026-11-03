from pathlib import Path
import chess
import chess.engine

# 1. Importa ChessEngine em vez de Engine
from chess_engine.engine import ChessEngine


def play_match():
    # 1. Caminho do binário do Stockfish
    stockfish_path = Path("engines/stockfish/stockfish-windows-x86-64-avx2.exe")
    if not stockfish_path.exists():
        executables = list(Path("engines/stockfish").glob("*.exe"))
        if executables:
            stockfish_path = executables[0]
        else:
            print("Executável do Stockfish não encontrado em engines/stockfish/")
            return

    # 2. Inicializa os motores (usa max_depth=3 e o HybridEvaluator padrão)
    sf_engine = chess.engine.SimpleEngine.popen_uci(str(stockfish_path))
    my_engine = ChessEngine(max_depth=3)

    board = chess.Board()
    print("--- Iniciando Partida: Nosso Motor (Brancas) vs Stockfish (Pretas) ---")

    while not board.is_game_over():
        if board.turn == chess.WHITE:
            # 3. Chama o método best_move e extrai o lance da classe SearchResult
            search_result = my_engine.best_move(board, time_limit=2.0)
            move = search_result.move
            print(f"Nosso Motor jogou: {move} | Avaliação: {search_result.score} cp (prof. {search_result.depth})")
        else:
            # Jogada do Stockfish (limitado a 0.1s para testes rápidos)
            result = sf_engine.play(board, chess.engine.Limit(time=0.1))
            move = result.move
            print(f"Stockfish jogou:   {move}")

        board.push(move)

    print("\nFim de jogo!")
    print(f"Resultado: {board.result()}")
    sf_engine.quit()


if __name__ == "__main__":
    play_match()