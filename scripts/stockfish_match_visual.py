
import argparse
import queue
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import chess
import chess.engine
import chess.pgn

from chess_engine.engine import ChessEngine


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STOCKFISH = (
    ROOT / "engines" / "stockfish"
    / "stockfish-windows-x86-64-universal.exe"
)

PIECES = {
    "K": "♔", "Q": "♕", "R": "♖",
    "B": "♗", "N": "♘", "P": "♙",
    "k": "♚", "q": "♛", "r": "♜",
    "b": "♝", "n": "♞", "p": "♟",
}

LIGHT = "#F0D9B5"
DARK = "#B58863"
LAST_MOVE = "#CDD26A"
CHECK = "#E57373"
SQUARE = 68


class StockfishMatchVisual:
    def __init__(
        self,
        root: tk.Tk,
        stockfish_path: Path,
        depth: int,
        our_time: float,
        stockfish_time: float,
        elo: int,
        our_color: str,
        max_plies: int,
    ):
        self.root = root
        self.stockfish_path = stockfish_path
        self.depth = depth
        self.our_time = our_time
        self.stockfish_time = stockfish_time
        self.elo = elo
        self.max_plies = max_plies

        self.our_color = (
            chess.WHITE if our_color == "white"
            else chess.BLACK
        )

        self.board = chess.Board()
        self.our_engine = ChessEngine(max_depth=depth)

        self.messages = queue.Queue()
        self.generation = 0
        self.thinking = False
        self.pending_result = None
        self.running = False
        self.step_requested = False
        self.finished = False
        self.last_move = None
        self.elapsed_total = 0.0
        self.next_move_at = 0.0

        self.speed_var = tk.DoubleVar(value=0.5)
        self.status_var = tk.StringVar(value="Pronto para iniciar.")
        self.turn_var = tk.StringVar(value="")
        self.info_var = tk.StringVar(value="Aguardando primeiro lance.")
        self.time_var = tk.StringVar(value="Tempo total: 0.00s")

        self.game = None
        self.game_node = None
        self.new_game()

        self.root.title("Chess Challenge III vs Stockfish 19")
        self.root.geometry("1050x710")
        self.root.minsize(900, 650)

        self.build_interface()
        self.draw_board()
        self.update_turn()

        self.root.after(50, self.update_loop)

    def new_game(self):
        self.board.reset()
        self.our_engine.clear_cache()

        self.game = chess.pgn.Game()
        self.game.headers["Event"] = "Chess Challenge III vs Stockfish"
        self.game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
        self.game.headers["White"] = (
            "ChessEngine" if self.our_color == chess.WHITE
            else "Stockfish 19"
        )
        self.game.headers["Black"] = (
            "Stockfish 19" if self.our_color == chess.WHITE
            else "ChessEngine"
        )
        self.game.headers["Result"] = "*"
        self.game_node = self.game

    def build_interface(self):
        container = ttk.Frame(self.root, padding=15)
        container.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(container)
        left.pack(side=tk.LEFT, anchor=tk.N, padx=(0, 20))

        right = ttk.Frame(container)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(
            left,
            text="Chess Challenge III",
            font=("Segoe UI", 18, "bold"),
        ).pack(pady=(0, 12))

        self.canvas = tk.Canvas(
            left,
            width=SQUARE * 8,
            height=SQUARE * 8,
            highlightthickness=0,
        )
        self.canvas.pack()

        ttk.Label(
            left,
            textvariable=self.turn_var,
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=(12, 4))

        ttk.Label(
            left,
            textvariable=self.info_var,
            wraplength=540,
        ).pack()

        ttk.Label(
            left,
            textvariable=self.time_var,
        ).pack(pady=5)

        ttk.Label(
            right,
            text="Controle da partida",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor=tk.W, pady=(0, 12))

        controls = ttk.Frame(right)
        controls.pack(fill=tk.X, pady=(0, 12))

        buttons = [
            ("Iniciar / Continuar", self.start),
            ("Pausar", self.pause),
            ("Próximo lance", self.step),
            ("Reiniciar", self.reset),
            ("Salvar PGN", self.save_pgn),
        ]

        for index, (label, command) in enumerate(buttons):
            ttk.Button(
                controls,
                text=label,
                command=command,
            ).grid(
                row=index // 2,
                column=index % 2,
                sticky="ew",
                padx=3,
                pady=3,
            )

        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)

        ttk.Label(
            right,
            text=f"Stockfish: Elo configurado {self.elo}",
        ).pack(anchor=tk.W, pady=(0, 8))

        ttk.Label(
            right,
            text=f"ChessEngine: profundidade máxima {self.depth}",
        ).pack(anchor=tk.W, pady=(0, 8))

        ttk.Label(
            right,
            text="Intervalo entre movimentos",
        ).pack(anchor=tk.W)

        ttk.Scale(
            right,
            from_=0,
            to=3,
            variable=self.speed_var,
            orient=tk.HORIZONTAL,
        ).pack(fill=tk.X, pady=(4, 12))

        ttk.Separator(
            right,
            orient=tk.HORIZONTAL,
        ).pack(fill=tk.X, pady=8)

        ttk.Label(
            right,
            text="Histórico de movimentos",
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor=tk.W, pady=(0, 8))

        history_frame = ttk.Frame(right)
        history_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(history_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.history = tk.Text(
            history_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            state=tk.DISABLED,
            yscrollcommand=scrollbar.set,
        )
        self.history.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.history.yview)

        ttk.Label(
            right,
            textvariable=self.status_var,
            wraplength=370,
        ).pack(anchor=tk.W, pady=(12, 0))

    def draw_board(self):
        self.canvas.delete("all")

        for rank in range(7, -1, -1):
            for file in range(8):
                square = chess.square(file, rank)

                # A perspectiva acompanha a cor do nosso motor.
                if self.our_color == chess.WHITE:
                    display_file = file
                    display_rank = 7 - rank
                else:
                    display_file = 7 - file
                    display_rank = rank

                x = display_file * SQUARE
                y = display_rank * SQUARE

                color = LIGHT if (file + rank) % 2 else DARK

                if self.last_move and square in (
                    self.last_move.from_square,
                    self.last_move.to_square,
                ):
                    color = LAST_MOVE

                if self.board.is_check():
                    king = self.board.king(self.board.turn)
                    if square == king:
                        color = CHECK

                self.canvas.create_rectangle(
                    x, y, x + SQUARE, y + SQUARE,
                    fill=color,
                    outline=color,
                )

                piece = self.board.piece_at(square)
                if piece:
                    symbol = PIECES[piece.symbol()]
                    self.canvas.create_text(
                        x + SQUARE / 2,
                        y + SQUARE / 2,
                        text=symbol,
                        font=("Segoe UI Symbol", 44),
                        fill="#FFFFFF" if piece.color else "#111111",
                    )

                if display_file == 0:
                    self.canvas.create_text(
                        x + 9, y + 10,
                        text=str(rank + 1),
                        font=("Segoe UI", 9),
                        fill="#333333",
                    )

                if display_rank == 7:
                    self.canvas.create_text(
                        x + SQUARE - 9,
                        y + SQUARE - 10,
                        text=chess.FILE_NAMES[file],
                        font=("Segoe UI", 9),
                        fill="#333333",
                    )

    def update_turn(self):
        color = "Brancas" if self.board.turn else "Pretas"
        player = (
            "ChessEngine"
            if self.board.turn == self.our_color
            else "Stockfish 19"
        )
        self.turn_var.set(f"{color}: {player}")

    def append_history(self, text):
        self.history.config(state=tk.NORMAL)
        self.history.insert(tk.END, text + "\n")
        self.history.see(tk.END)
        self.history.config(state=tk.DISABLED)

    def start(self):
        if self.finished:
            return
        self.running = True
        self.step_requested = False
        self.status_var.set("Partida em andamento.")

    def pause(self):
        self.running = False
        self.step_requested = False
        self.status_var.set(
            "Pausado. A busca atual pode terminar antes da pausa."
        )

    def step(self):
        if self.finished:
            return
        self.running = False
        self.step_requested = True
        self.status_var.set("Executando próximo lance.")

    def reset(self):
        if self.thinking:
            messagebox.showinfo(
                "Busca em andamento",
                "Aguarde a busca atual terminar antes de reiniciar.",
            )
            return

        self.generation += 1
        self.running = False
        self.step_requested = False
        self.finished = False
        self.pending_result = None
        self.last_move = None
        self.elapsed_total = 0.0
        self.next_move_at = 0.0

        self.new_game()

        self.history.config(state=tk.NORMAL)
        self.history.delete("1.0", tk.END)
        self.history.config(state=tk.DISABLED)

        self.info_var.set("Aguardando primeiro lance.")
        self.time_var.set("Tempo total: 0.00s")
        self.status_var.set("Partida reiniciada.")

        self.update_turn()
        self.draw_board()

    def start_search(self):
        self.thinking = True
        generation = self.generation
        board = self.board.copy(stack=True)
        is_ours = board.turn == self.our_color

        self.status_var.set(
            "ChessEngine pensando..."
            if is_ours else "Stockfish pensando..."
        )

        def worker():
            try:
                if is_ours:
                    result = self.our_engine.best_move(
                        board,
                        time_limit=self.our_time,
                    )
                    move = result.move
                    details = (
                        f"Profundidade {result.depth} | "
                        f"Avaliação {result.score:+} cp | "
                        f"Status {result.status} | "
                        f"Nós {result.metrics.get('total_nodes', 0)}"
                    )
                    elapsed = result.elapsed
                else:
                    start = time.monotonic()

                    # Processo independente por lance: facilita
                    # o isolamento da integração com o Stockfish.
                    with chess.engine.SimpleEngine.popen_uci(
                        str(self.stockfish_path)
                    ) as stockfish:
                        stockfish.configure({
                            "Threads": 1,
                            "Hash": 16,
                            "UCI_LimitStrength": True,
                            "UCI_Elo": self.elo,
                        })

                        result = stockfish.play(
                            board,
                            chess.engine.Limit(
                                time=self.stockfish_time
                            ),
                        )
                        move = result.move

                    elapsed = time.monotonic() - start
                    details = (
                        f"Stockfish Elo {self.elo} | "
                        f"Tempo {elapsed:.2f}s"
                    )

                self.messages.put(
                    (generation, move, details, elapsed, None)
                )

            except Exception as exc:
                self.messages.put(
                    (generation, None, "", 0.0, str(exc))
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def apply_result(self, move, details, elapsed):
        if move not in self.board.legal_moves:
            self.finished = True
            self.running = False
            self.status_var.set(
                f"Erro: movimento ilegal retornado: {move}"
            )
            return

        color = self.board.turn
        san = self.board.san(move)
        move_number = self.board.fullmove_number

        notation = (
            f"{move_number}. {san}"
            if color == chess.WHITE
            else f"{move_number}... {san}"
        )

        player = (
            "ChessEngine"
            if color == self.our_color
            else "Stockfish"
        )

        self.game_node = self.game_node.add_variation(move)
        self.board.push(move)
        self.last_move = move
        self.elapsed_total += elapsed

        self.append_history(
            f"{notation:14} {player:12} {elapsed:.2f}s"
        )

        self.info_var.set(details)
        self.time_var.set(
            f"Tempo total: {self.elapsed_total:.2f}s"
        )

        self.draw_board()
        self.update_turn()

        if self.board.is_game_over(claim_draw=True):
            self.finish_game()
        elif self.board.ply() >= self.max_plies:
            self.finished = True
            self.running = False
            self.step_requested = False
            self.status_var.set(
                "Limite de meios-lances atingido. "
                "Partida inconclusiva."
            )
        else:
            self.status_var.set("Aguardando próximo lance.")

        self.next_move_at = (
            time.monotonic() + self.speed_var.get()
        )

    def finish_game(self):
        self.finished = True
        self.running = False
        self.step_requested = False

        outcome = self.board.outcome(claim_draw=True)
        result = self.board.result(claim_draw=True)
        self.game.headers["Result"] = result

        reason = (
            outcome.termination.name
            if outcome is not None
            else "DESCONHECIDO"
        )

        self.status_var.set(
            f"Partida encerrada: {result} | {reason}"
        )

        self.append_history(
            f"\nResultado: {result} | {reason}"
        )

    def update_loop(self):
        try:
            while True:
                generation, move, details, elapsed, error = (
                    self.messages.get_nowait()
                )

                if generation != self.generation:
                    continue

                self.thinking = False

                if error:
                    self.running = False
                    self.step_requested = False
                    self.status_var.set(f"Erro: {error}")
                    continue

                self.pending_result = (
                    move, details, elapsed
                )

        except queue.Empty:
            pass

        if (
            self.pending_result is not None
            and (self.running or self.step_requested)
        ):
            move, details, elapsed = self.pending_result
            self.pending_result = None
            self.apply_result(move, details, elapsed)
            self.step_requested = False

        if (
            not self.finished
            and not self.thinking
            and self.pending_result is None
            and (self.running or self.step_requested)
            and time.monotonic() >= self.next_move_at
        ):
            self.start_search()

        self.root.after(50, self.update_loop)

    def save_pgn(self):
        initial_dir = ROOT / "benchmarks"
        initial_dir.mkdir(parents=True, exist_ok=True)

        path = filedialog.asksaveasfilename(
            title="Salvar partida",
            initialdir=str(initial_dir),
            initialfile="stockfish_match.pgn",
            defaultextension=".pgn",
            filetypes=[("Partidas PGN", "*.pgn")],
        )

        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as file:
                print(self.game, file=file)
            self.status_var.set(f"PGN salvo em: {path}")
        except OSError as exc:
            messagebox.showerror("Erro ao salvar", str(exc))


def main():
    parser = argparse.ArgumentParser(
        description="ChessEngine vs Stockfish - interface visual."
    )
    parser.add_argument(
        "--stockfish",
        type=Path,
        default=DEFAULT_STOCKFISH,
    )
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--our-time", type=float, default=1.0)
    parser.add_argument("--stockfish-time", type=float, default=0.1)
    parser.add_argument("--elo", type=int, default=1320)
    parser.add_argument(
        "--our-color",
        choices=("white", "black"),
        default="white",
    )
    parser.add_argument("--max-plies", type=int, default=300)
    args = parser.parse_args()

    if not args.stockfish.is_file():
        parser.error(
            f"Executável do Stockfish não encontrado: {args.stockfish}"
        )
    if args.depth < 1:
        parser.error("--depth deve ser pelo menos 1")
    if args.our_time <= 0 or args.stockfish_time <= 0:
        parser.error("Os limites de tempo devem ser positivos")
    if not 1320 <= args.elo <= 3190:
        parser.error("--elo deve estar entre 1320 e 3190")
    if args.max_plies < 1:
        parser.error("--max-plies deve ser pelo menos 1")

    root = tk.Tk()
    StockfishMatchVisual(
        root=root,
        stockfish_path=args.stockfish,
        depth=args.depth,
        our_time=args.our_time,
        stockfish_time=args.stockfish_time,
        elo=args.elo,
        our_color=args.our_color,
        max_plies=args.max_plies,
    )
    root.mainloop()


if __name__ == "__main__":
    main()
