import argparse
import queue
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import chess
import chess.pgn

from chess_engine.engine import ChessEngine


PIECES = {
    "K": "♔", "Q": "♕", "R": "♖",
    "B": "♗", "N": "♘", "P": "♙",
    "k": "♚", "q": "♛", "r": "♜",
    "b": "♝", "n": "♞", "p": "♟",
}

LIGHT = "#F0D9B5"
DARK = "#B58863"
LAST_MOVE = "#CDD26A"
CHECK_COLOR = "#E57373"
SQUARE_SIZE = 68
BOARD_SIZE = SQUARE_SIZE * 8


class VisualSelfPlay:
    def __init__(
        self,
        root: tk.Tk,
        depth: int,
        time_limit: float,
        max_plies: int,
    ):
        self.root = root
        self.depth = depth
        self.time_limit = time_limit
        self.max_plies = max_plies

        self.board = chess.Board()
        self.white_engine = ChessEngine(max_depth=depth)
        self.black_engine = ChessEngine(max_depth=depth)

        self.messages = queue.Queue()
        self.generation = 0
        self.thinking = False
        self.pending_result = None

        self.running = False
        self.step_requested = False
        self.finished = False
        self.last_move = None

        self.moves_played = 0
        self.next_move_at = 0
        self.elapsed_total = 0.0

        self.game = chess.pgn.Game()
        self.game.headers["Event"] = (
            "Chess Challenge III - Visual Self Play"
        )
        self.game.headers["White"] = "ChessEngine"
        self.game.headers["Black"] = "ChessEngine"
        self.game.headers["Date"] = (
            datetime.now().strftime("%Y.%m.%d")
        )
        self.game_node = self.game

        self.root.title(
            "Chess Challenge III - Self-Play Visual"
        )
        self.root.geometry("1050x690")
        self.root.minsize(900, 650)

        self.status_var = tk.StringVar(
            value="Pronto para iniciar."
        )
        self.turn_var = tk.StringVar(
            value="Brancas jogam"
        )
        self.info_var = tk.StringVar(
            value="Profundidade: - | Avaliação: -"
        )
        self.time_var = tk.StringVar(
            value="Tempo acumulado: 0.00s"
        )
        self.speed_var = tk.DoubleVar(value=0.5)

        self.build_interface()
        self.draw_board()

        self.root.after(50, self.update_loop)

    def build_interface(self):
        container = ttk.Frame(
            self.root,
            padding=15,
        )
        container.pack(
            fill=tk.BOTH,
            expand=True,
        )

        left = ttk.Frame(container)
        left.pack(
            side=tk.LEFT,
            padx=(0, 20),
            anchor=tk.N,
        )

        right = ttk.Frame(container)
        right.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
        )

        ttk.Label(
            left,
            text="Chess Challenge III",
            font=("Segoe UI", 18, "bold"),
        ).pack(pady=(0, 12))

        self.canvas = tk.Canvas(
            left,
            width=BOARD_SIZE,
            height=BOARD_SIZE,
            highlightthickness=0,
        )
        self.canvas.pack()

        ttk.Label(
            left,
            textvariable=self.turn_var,
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=(12, 3))

        ttk.Label(
            left,
            textvariable=self.info_var,
        ).pack()

        ttk.Label(
            left,
            textvariable=self.time_var,
        ).pack(pady=(4, 0))

        ttk.Label(
            right,
            text="Controle da partida",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor=tk.W, pady=(0, 12))

        controls = ttk.Frame(right)
        controls.pack(
            fill=tk.X,
            pady=(0, 12),
        )

        self.start_button = ttk.Button(
            controls,
            text="Iniciar / Continuar",
            command=self.start,
        )
        self.start_button.grid(
            row=0,
            column=0,
            padx=3,
            pady=3,
            sticky="ew",
        )

        self.pause_button = ttk.Button(
            controls,
            text="Pausar",
            command=self.pause,
        )
        self.pause_button.grid(
            row=0,
            column=1,
            padx=3,
            pady=3,
            sticky="ew",
        )

        self.step_button = ttk.Button(
            controls,
            text="Próximo lance",
            command=self.step,
        )
        self.step_button.grid(
            row=1,
            column=0,
            padx=3,
            pady=3,
            sticky="ew",
        )

        self.reset_button = ttk.Button(
            controls,
            text="Reiniciar",
            command=self.reset,
        )
        self.reset_button.grid(
            row=1,
            column=1,
            padx=3,
            pady=3,
            sticky="ew",
        )

        for column in range(2):
            controls.columnconfigure(
                column,
                weight=1,
            )

        ttk.Label(
            right,
            text="Intervalo entre lances",
        ).pack(anchor=tk.W)

        speed_frame = ttk.Frame(right)
        speed_frame.pack(
            fill=tk.X,
            pady=(3, 12),
        )

        ttk.Scale(
            speed_frame,
            from_=0,
            to=3,
            variable=self.speed_var,
            orient=tk.HORIZONTAL,
        ).pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
        )

        ttk.Label(
            speed_frame,
            text="0 a 3s",
        ).pack(side=tk.RIGHT, padx=(10, 0))

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
        history_frame.pack(
            fill=tk.BOTH,
            expand=True,
        )

        scrollbar = ttk.Scrollbar(history_frame)
        scrollbar.pack(
            side=tk.RIGHT,
            fill=tk.Y,
        )

        self.history = tk.Text(
            history_frame,
            wrap=tk.WORD,
            font=("Consolas", 11),
            state=tk.DISABLED,
            yscrollcommand=scrollbar.set,
        )
        self.history.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
        )

        scrollbar.config(
            command=self.history.yview,
        )

        ttk.Label(
            right,
            textvariable=self.status_var,
            wraplength=360,
            font=("Segoe UI", 10),
        ).pack(
            anchor=tk.W,
            pady=(12, 8),
        )

        ttk.Button(
            right,
            text="Salvar PGN",
            command=self.save_pgn,
        ).pack(
            fill=tk.X,
            pady=(0, 5),
        )

    def draw_board(self):
        self.canvas.delete("all")

        for row in range(8):
            for col in range(8):
                square = chess.square(
                    col,
                    7 - row,
                )

                x1 = col * SQUARE_SIZE
                y1 = row * SQUARE_SIZE
                x2 = x1 + SQUARE_SIZE
                y2 = y1 + SQUARE_SIZE

                color = (
                    LIGHT
                    if (row + col) % 2 == 0
                    else DARK
                )

                if self.last_move is not None:
                    if square in (
                        self.last_move.from_square,
                        self.last_move.to_square,
                    ):
                        color = LAST_MOVE

                piece = self.board.piece_at(square)

                if (
                    piece is not None
                    and piece.piece_type == chess.KING
                    and piece.color == self.board.turn
                    and self.board.is_check()
                ):
                    color = CHECK_COLOR

                self.canvas.create_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill=color,
                    outline=color,
                )

                if piece is not None:
                    symbol = PIECES[piece.symbol()]

                    self.canvas.create_text(
                        x1 + SQUARE_SIZE / 2,
                        y1 + SQUARE_SIZE / 2,
                        text=symbol,
                        font=(
                            "Segoe UI Symbol",
                            42,
                        ),
                        fill=(
                            "#FFFFFF"
                            if piece.color == chess.WHITE
                            else "#161616"
                        ),
                    )

                if col == 0:
                    self.canvas.create_text(
                        x1 + 9,
                        y1 + 10,
                        text=str(8 - row),
                        font=("Segoe UI", 9, "bold"),
                        fill="#333333",
                    )

                if row == 7:
                    self.canvas.create_text(
                        x2 - 10,
                        y2 - 10,
                        text="abcdefgh"[col],
                        font=("Segoe UI", 9, "bold"),
                        fill="#333333",
                    )

    def append_history(self, text: str):
        self.history.config(state=tk.NORMAL)
        self.history.insert(tk.END, text + "\n")
        self.history.see(tk.END)
        self.history.config(state=tk.DISABLED)

    def start(self):
        if self.finished:
            return

        self.running = True
        self.step_requested = False
        self.status_var.set("Partida em execução.")

    def pause(self):
        if self.finished:
            return

        self.running = False
        self.step_requested = False
        self.status_var.set(
            "Pausado. A busca atual pode terminar "
            "antes de a pausa ser aplicada."
        )

    def step(self):
        if self.finished:
            return

        self.running = False
        self.step_requested = True
        self.status_var.set(
            "Calculando próximo lance..."
        )

    def reset(self):
        # Resultados de threads antigas serão ignorados.
        self.generation += 1

        self.board = chess.Board()

        self.white_engine = ChessEngine(
            max_depth=self.depth
        )
        self.black_engine = ChessEngine(
            max_depth=self.depth
        )

        self.thinking = False
        self.pending_result = None

        self.running = False
        self.step_requested = False
        self.finished = False

        self.last_move = None
        self.moves_played = 0
        self.next_move_at = 0
        self.elapsed_total = 0.0

        self.game = chess.pgn.Game()
        self.game.headers["Event"] = (
            "Chess Challenge III - Visual Self Play"
        )
        self.game.headers["White"] = "ChessEngine"
        self.game.headers["Black"] = "ChessEngine"
        self.game.headers["Date"] = (
            datetime.now().strftime("%Y.%m.%d")
        )
        self.game_node = self.game

        self.history.config(state=tk.NORMAL)
        self.history.delete("1.0", tk.END)
        self.history.config(state=tk.DISABLED)

        self.turn_var.set("Brancas jogam")
        self.info_var.set(
            "Profundidade: - | Avaliação: -"
        )
        self.time_var.set(
            "Tempo acumulado: 0.00s"
        )
        self.status_var.set(
            "Partida reiniciada."
        )

        self.draw_board()

    def start_search(self):
        if self.thinking or self.pending_result is not None:
            return

        self.thinking = True

        generation = self.generation
        board_copy = self.board.copy(stack=True)

        engine = (
            self.white_engine
            if board_copy.turn == chess.WHITE
            else self.black_engine
        )

        self.status_var.set(
            "Brancas pensando..."
            if board_copy.turn == chess.WHITE
            else "Pretas pensando..."
        )

        def worker():
            try:
                result = engine.best_move(
                    board_copy,
                    time_limit=self.time_limit,
                )

                self.messages.put(
                    (
                        generation,
                        "result",
                        result,
                    )
                )

            except Exception as exc:
                self.messages.put(
                    (
                        generation,
                        "error",
                        str(exc),
                    )
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def apply_result(self, result):
        if self.finished:
            return

        move = result.move

        if move not in self.board.legal_moves:
            self.running = False
            self.step_requested = False
            self.status_var.set(
                "Erro: o motor retornou um lance ilegal."
            )
            return

        move_number = self.board.fullmove_number
        white_turn = self.board.turn == chess.WHITE

        san = self.board.san(move)

        notation = (
            f"{move_number}. {san}"
            if white_turn
            else f"{move_number}... {san}"
        )

        self.game_node = self.game_node.add_variation(
            move
        )

        self.board.push(move)
        self.last_move = move
        self.moves_played += 1

        self.elapsed_total += result.elapsed

        self.append_history(
            f"{notation:<15} "
            f"prof={result.depth}  "
            f"score={result.score:+d} cp  "
            f"tempo={result.elapsed:.3f}s"
        )

        self.info_var.set(
            f"Último lance: {san} | "
            f"Profundidade: {result.depth} | "
            f"Avaliação: {result.score:+d} cp"
        )

        self.time_var.set(
            f"Tempo acumulado: "
            f"{self.elapsed_total:.2f}s"
        )

        self.turn_var.set(
            "Brancas jogam"
            if self.board.turn == chess.WHITE
            else "Pretas jogam"
        )

        self.draw_board()

        if self.board.is_game_over(claim_draw=True):
            self.finish_game()

        elif self.moves_played >= self.max_plies:
            self.finish_game(
                reached_limit=True
            )

        elif self.step_requested:
            self.step_requested = False
            self.status_var.set(
                "Lance concluído. Partida pausada."
            )

        else:
            self.status_var.set(
                f"Último lance: {notation}"
            )

    def finish_game(self, reached_limit=False):
        self.finished = True
        self.running = False
        self.step_requested = False

        if reached_limit:
            result = "*"
            reason = "Limite de meios-lances atingido."
        else:
            outcome = self.board.outcome(
                claim_draw=True
            )

            result = (
                outcome.result()
                if outcome is not None
                else "*"
            )

            reason = (
                outcome.termination.name
                if outcome is not None
                else "UNKNOWN"
            )

        self.game.headers["Result"] = result

        self.status_var.set(
            f"Partida encerrada: {result} | {reason}"
        )

        self.append_history("")
        self.append_history(
            f"RESULTADO: {result} | {reason}"
        )

        messagebox.showinfo(
            "Fim da partida",
            f"Resultado: {result}\n"
            f"Motivo: {reason}\n"
            f"Meios-lances: {self.moves_played}",
        )

    def save_pgn(self):
        default_name = (
            "self_play_visual_"
            + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            + ".pgn"
        )

        path = filedialog.asksaveasfilename(
            title="Salvar partida",
            defaultextension=".pgn",
            initialdir=str(Path("benchmarks").resolve()),
            initialfile=default_name,
            filetypes=[
                ("Partidas PGN", "*.pgn"),
            ],
        )

        if not path:
            return

        try:
            with open(
                path,
                "w",
                encoding="utf-8",
            ) as file:
                print(
                    self.game,
                    file=file,
                    end="\n\n",
                )

            self.status_var.set(
                f"PGN salvo: {path}"
            )

        except OSError as exc:
            messagebox.showerror(
                "Erro ao salvar PGN",
                str(exc),
            )

    def update_loop(self):
        import time

        while True:
            try:
                generation, kind, payload = (
                    self.messages.get_nowait()
                )
            except queue.Empty:
                break

            if generation != self.generation:
                continue

            self.thinking = False

            if kind == "error":
                self.running = False
                self.step_requested = False
                self.status_var.set(
                    f"Erro na busca: {payload}"
                )
                continue

            self.pending_result = payload

        if not self.finished:
            if self.pending_result is not None:
                if (
                    self.running
                    or self.step_requested
                ):
                    if time.monotonic() >= self.next_move_at:
                        result = self.pending_result
                        self.pending_result = None

                        self.apply_result(result)

                        self.next_move_at = (
                            time.monotonic()
                            + self.speed_var.get()
                        )

            elif (
                not self.thinking
                and (
                    self.running
                    or self.step_requested
                )
                and time.monotonic() >= self.next_move_at
            ):
                self.start_search()

        self.root.after(
            50,
            self.update_loop,
        )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Partida visual entre dois motores de xadrez."
        )
    )

    parser.add_argument(
        "--depth",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--time",
        type=float,
        default=1.0,
    )

    parser.add_argument(
        "--max-plies",
        type=int,
        default=1000,
    )

    args = parser.parse_args()

    if args.depth < 1:
        parser.error(
            "--depth deve ser pelo menos 1."
        )

    if args.time <= 0:
        parser.error(
            "--time deve ser positivo."
        )

    if args.max_plies < 1:
        parser.error(
            "--max-plies deve ser pelo menos 1."
        )

    root = tk.Tk()

    VisualSelfPlay(
        root=root,
        depth=args.depth,
        time_limit=args.time,
        max_plies=args.max_plies,
    )

    root.mainloop()


if __name__ == "__main__":
    main()
