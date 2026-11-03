
import csv
import json
import queue
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

import chess
import chess.pgn

from chess_engine.engine import ChessEngine


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "competition_logs"

LIGHT = "#EEEED2"
DARK = "#769656"
SELECTED = "#F6F669"
LAST_MOVE = "#BACA44"
TARGET = "#4D8754"

PIECES = {
    "K": "♔", "Q": "♕", "R": "♖",
    "B": "♗", "N": "♘", "P": "♙",
    "k": "♚", "q": "♛", "r": "♜",
    "b": "♝", "n": "♞", "p": "♟",
}


class ChessCompetitionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chess Challenge III")
        self.root.geometry("1000x730")
        self.root.minsize(900, 650)

        self.board = chess.Board()
        self.engine = None

        self.our_color = chess.WHITE
        self.started = False
        self.thinking = False
        self.selected = None
        self.last_move = None

        self.depth = 3
        self.think_time = 5.0

        self.generation = 0
        self.results = queue.Queue()

        self.records = []
        self.log_dir = None

        self.color_var = tk.StringVar(value="white")
        self.depth_var = tk.StringVar(value="3")
        self.time_var = tk.StringVar(value="5")

        self.status_var = tk.StringVar(
            value="Configure a partida e clique em Iniciar."
        )
        self.analysis_var = tk.StringVar(value="Nenhuma análise.")
        self.turn_var = tk.StringVar(value="Partida não iniciada")

        self.square_size = 70
        self.build_ui()
        self.draw_board()

        self.root.after(100, self.poll_results)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def build_ui(self):
        main = ttk.Frame(self.root, padding=15)
        main.pack(fill=tk.BOTH, expand=True)

        board_area = ttk.Frame(main)
        board_area.pack(side=tk.LEFT, anchor=tk.N)

        self.canvas = tk.Canvas(
            board_area,
            width=self.square_size * 8,
            height=self.square_size * 8,
            highlightthickness=0,
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_board_click)

        ttk.Label(
            board_area,
            textvariable=self.turn_var,
            font=("Segoe UI", 13, "bold"),
        ).pack(pady=12)

        panel = ttk.Frame(main)
        panel.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
            padx=(25, 0),
        )

        ttk.Label(
            panel,
            text="Chess Challenge III",
            font=("Segoe UI", 22, "bold"),
        ).pack(anchor="w", pady=(0, 20))

        config = ttk.LabelFrame(
            panel,
            text="Configuração da partida",
            padding=12,
        )
        config.pack(fill=tk.X)

        ttk.Label(
            config, text="Nossa cor:"
        ).grid(row=0, column=0, sticky="w")

        ttk.Radiobutton(
            config,
            text="Brancas",
            variable=self.color_var,
            value="white",
        ).grid(row=0, column=1, sticky="w")

        ttk.Radiobutton(
            config,
            text="Pretas",
            variable=self.color_var,
            value="black",
        ).grid(row=0, column=2, sticky="w")

        ttk.Label(
            config, text="Profundidade:"
        ).grid(row=1, column=0, sticky="w", pady=10)

        ttk.Spinbox(
            config,
            from_=1,
            to=30,
            textvariable=self.depth_var,
            width=8,
        ).grid(row=1, column=1, sticky="w")

        ttk.Label(
            config, text="Tempo por lance (s):"
        ).grid(row=2, column=0, sticky="w")

        ttk.Entry(
            config,
            textvariable=self.time_var,
            width=10,
        ).grid(row=2, column=1, sticky="w")

        ttk.Button(
            panel,
            text="Iniciar nova partida",
            command=self.start_game,
        ).pack(fill=tk.X, pady=(15, 5))

        self.calculate_button = ttk.Button(
            panel,
            text="Calcular jogada do motor",
            command=self.calculate,
        )
        self.calculate_button.pack(fill=tk.X, pady=5)

        ttk.Button(
            panel,
            text="Desfazer última jogada",
            command=self.undo,
        ).pack(fill=tk.X, pady=5)

        ttk.Label(
            panel,
            text="Análise do motor",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", pady=(25, 5))

        ttk.Label(
            panel,
            textvariable=self.analysis_var,
            wraplength=320,
            justify=tk.LEFT,
        ).pack(anchor="w")

        ttk.Label(
            panel,
            text="Histórico de movimentos",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", pady=(25, 5))

        history_frame = ttk.Frame(panel)
        history_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(history_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.history = tk.Text(
            history_frame,
            font=("Consolas", 11),
            state=tk.DISABLED,
            height=12,
            yscrollcommand=scrollbar.set,
        )
        self.history.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
        )

        scrollbar.configure(command=self.history.yview)

        ttk.Label(
            panel,
            textvariable=self.status_var,
            wraplength=330,
        ).pack(anchor="w", pady=12)

    def square_from_display(self, row, col):
        if self.our_color == chess.WHITE:
            return chess.square(col, 7 - row)

        return chess.square(7 - col, row)

    def draw_board(self):
        self.canvas.delete("all")

        legal_targets = set()

        if self.selected is not None:
            legal_targets = {
                move.to_square
                for move in self.board.legal_moves
                if move.from_square == self.selected
            }

        for row in range(8):
            for col in range(8):
                square = self.square_from_display(row, col)

                x = col * self.square_size
                y = row * self.square_size

                file = chess.square_file(square)
                rank = chess.square_rank(square)

                color = (
                    LIGHT if (file + rank) % 2 else DARK
                )

                if self.last_move and square in (
                    self.last_move.from_square,
                    self.last_move.to_square,
                ):
                    color = LAST_MOVE

                if square == self.selected:
                    color = SELECTED

                self.canvas.create_rectangle(
                    x,
                    y,
                    x + self.square_size,
                    y + self.square_size,
                    fill=color,
                    outline=color,
                )

                if square in legal_targets:
                    radius = 9
                    cx = x + self.square_size / 2
                    cy = y + self.square_size / 2

                    self.canvas.create_oval(
                        cx - radius,
                        cy - radius,
                        cx + radius,
                        cy + radius,
                        fill=TARGET,
                        outline="",
                    )

                piece = self.board.piece_at(square)

                if piece:
                    self.canvas.create_text(
                        x + self.square_size / 2,
                        y + self.square_size / 2,
                        text=PIECES[piece.symbol()],
                        font=("Segoe UI Symbol", 46),
                        fill=(
                            "#FFFFFF"
                            if piece.color == chess.WHITE
                            else "#181818"
                        ),
                    )

                if col == 0:
                    self.canvas.create_text(
                        x + 9,
                        y + 11,
                        text=str(rank + 1),
                        font=("Segoe UI", 9, "bold"),
                    )

                if row == 7:
                    self.canvas.create_text(
                        x + self.square_size - 10,
                        y + self.square_size - 10,
                        text=chess.FILE_NAMES[file],
                        font=("Segoe UI", 9, "bold"),
                    )

    def start_game(self):
        if self.thinking:
            messagebox.showwarning(
                "Aguarde",
                "O motor ainda está calculando.",
            )
            return

        if self.started:
            if not messagebox.askyesno(
                "Nova partida",
                "Deseja iniciar uma nova partida?",
            ):
                return

        try:
            depth = int(self.depth_var.get())
            think_time = float(self.time_var.get())

            if depth < 1 or think_time <= 0:
                raise ValueError

        except ValueError:
            messagebox.showerror(
                "Configuração inválida",
                "Informe profundidade e tempo válidos.",
            )
            return

        self.depth = depth
        self.think_time = think_time

        self.our_color = (
            chess.WHITE
            if self.color_var.get() == "white"
            else chess.BLACK
        )

        try:
            self.engine = ChessEngine(max_depth=depth)
        except Exception as exc:
            messagebox.showerror(
                "Erro ao iniciar motor",
                str(exc),
            )
            return

        self.board = chess.Board()
        self.records = []

        self.selected = None
        self.last_move = None

        self.started = True
        self.generation += 1

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        self.log_dir = LOG_DIR / f"game_{timestamp}"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.analysis_var.set("Nenhuma análise.")
        self.status_var.set("Partida iniciada.")

        self.refresh()
        self.save_logs()

    def on_board_click(self, event):
        if not self.started or self.thinking:
            return

        if self.board.is_game_over(claim_draw=True):
            return

        if self.board.turn == self.our_color:
            self.status_var.set(
                "É a vez do motor. Clique em Calcular jogada."
            )
            return

        col = event.x // self.square_size
        row = event.y // self.square_size

        if not (0 <= row < 8 and 0 <= col < 8):
            return

        square = self.square_from_display(row, col)
        piece = self.board.piece_at(square)

        if self.selected is None:
            if piece and piece.color == self.board.turn:
                self.selected = square
                self.draw_board()
            return

        if piece and piece.color == self.board.turn:
            self.selected = square
            self.draw_board()
            return

        from_square = self.selected
        self.selected = None

        moves = [
            move
            for move in self.board.legal_moves
            if move.from_square == from_square
            and move.to_square == square
        ]

        if not moves:
            self.status_var.set("Movimento ilegal.")
            self.draw_board()
            return

        if len(moves) > 1:
            move = self.choose_promotion(moves)
            if move is None:
                self.draw_board()
                return
        else:
            move = moves[0]

        self.apply_move(move, "opponent")

    def choose_promotion(self, moves):
        dialog = tk.Toplevel(self.root)
        dialog.title("Promoção")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        result = {"move": None}

        ttk.Label(
            dialog,
            text="Escolha a peça para promoção:",
            padding=12,
        ).pack()

        frame = ttk.Frame(dialog, padding=10)
        frame.pack()

        options = [
            ("Dama", chess.QUEEN),
            ("Torre", chess.ROOK),
            ("Bispo", chess.BISHOP),
            ("Cavalo", chess.KNIGHT),
        ]

        def select(piece_type):
            result["move"] = next(
                (
                    move
                    for move in moves
                    if move.promotion == piece_type
                ),
                None,
            )
            dialog.destroy()

        for label, piece_type in options:
            ttk.Button(
                frame,
                text=label,
                command=lambda p=piece_type: select(p),
            ).pack(side=tk.LEFT, padx=4)

        dialog.wait_window()
        return result["move"]

    def calculate(self):
        if not self.started or self.thinking:
            return

        if self.board.is_game_over(claim_draw=True):
            self.status_var.set("A partida terminou.")
            return

        if self.board.turn != self.our_color:
            self.status_var.set(
                "Registre a jogada adversária no tabuleiro."
            )
            return

        self.thinking = True
        self.calculate_button.configure(state=tk.DISABLED)
        self.status_var.set("Motor pensando...")

        board_copy = self.board.copy(stack=True)
        generation = self.generation

        def worker():
            try:
                result = self.engine.best_move(
                    board_copy,
                    time_limit=self.think_time,
                )
                self.results.put(
                    (generation, result, None)
                )
            except Exception as exc:
                self.results.put(
                    (generation, None, str(exc))
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def poll_results(self):
        try:
            while True:
                generation, result, error = (
                    self.results.get_nowait()
                )

                if generation != self.generation:
                    continue

                self.thinking = False
                self.calculate_button.configure(
                    state=tk.NORMAL
                )

                if error:
                    self.status_var.set(
                        f"Erro no motor: {error}"
                    )
                    continue

                if (
                    result.move is None
                    or result.move not in self.board.legal_moves
                ):
                    self.status_var.set(
                        "O motor não retornou um lance legal."
                    )
                    continue

                san = self.board.san(result.move)

                self.analysis_var.set(
                    f"Jogada: {san} ({result.move.uci()})\n"
                    f"Avaliação: {result.score:+} cp\n"
                    f"Profundidade: {result.depth}\n"
                    f"Tempo: {result.elapsed:.3f}s"
                )

                self.apply_move(
                    result.move,
                    "engine",
                    result,
                )

        except queue.Empty:
            pass

        self.root.after(100, self.poll_results)

    def apply_move(self, move, player, result=None):
        if move not in self.board.legal_moves:
            return

        color = self.board.turn
        san = self.board.san(move)
        fen_before = self.board.fen()

        self.board.push(move)
        self.last_move = move

        record = {
            "ply": self.board.ply(),
            "player": player,
            "color": "white" if color else "black",
            "san": san,
            "uci": move.uci(),
            "fen_before": fen_before,
            "fen_after": self.board.fen(),
            "score_cp": (
                result.score if result else ""
            ),
            "depth": (
                result.depth if result else ""
            ),
            "elapsed_seconds": (
                round(result.elapsed, 4)
                if result else ""
            ),
        }

        self.records.append(record)

        if player == "engine":
            self.status_var.set(
                f"Nosso motor jogou {san}. "
                "Reproduza no tabuleiro físico."
            )
        else:
            self.status_var.set(
                f"Adversário jogou {san}. "
                "Calcule nossa resposta."
            )

        if self.board.is_game_over(claim_draw=True):
            self.status_var.set(
                f"Partida encerrada: "
                f"{self.board.result(claim_draw=True)}"
            )

        self.refresh()
        self.save_logs()

    def undo(self):
        if (
            not self.started
            or self.thinking
            or not self.board.move_stack
        ):
            return

        if not messagebox.askyesno(
            "Desfazer jogada",
            "Deseja desfazer a última jogada?",
        ):
            return

        self.board.pop()
        self.records.pop()

        self.last_move = (
            self.board.peek()
            if self.board.move_stack
            else None
        )

        self.selected = None
        self.analysis_var.set(
            "Última jogada desfeita."
        )
        self.status_var.set(
            "Jogada desfeita. "
            "Confira o tabuleiro físico."
        )

        self.refresh()
        self.save_logs()

    def refresh(self):
        self.draw_board()

        if not self.started:
            self.turn_var.set("Partida não iniciada")
        elif self.board.is_game_over(claim_draw=True):
            self.turn_var.set("Partida encerrada")
        else:
            color = (
                "Brancas"
                if self.board.turn == chess.WHITE
                else "Pretas"
            )
            player = (
                "Nosso motor"
                if self.board.turn == self.our_color
                else "Adversário"
            )
            self.turn_var.set(
                f"Vez: {color} — {player}"
            )

        self.history.configure(state=tk.NORMAL)
        self.history.delete("1.0", tk.END)

        for record in self.records:
            number = (record["ply"] + 1) // 2
            prefix = (
                f"{number}."
                if record["color"] == "white"
                else f"{number}..."
            )

            player = (
                "Motor"
                if record["player"] == "engine"
                else "Adversário"
            )

            self.history.insert(
                tk.END,
                f"{prefix:<6} {record['san']:<8} "
                f"{player}\n",
            )

        self.history.see(tk.END)
        self.history.configure(state=tk.DISABLED)

    def save_logs(self):
        if self.log_dir is None:
            return

        game = chess.pgn.Game()
        game.headers["Event"] = (
            "Chess Challenge III — Competição"
        )
        game.headers["White"] = (
            "ChessEngine"
            if self.our_color == chess.WHITE
            else "Adversário"
        )
        game.headers["Black"] = (
            "ChessEngine"
            if self.our_color == chess.BLACK
            else "Adversário"
        )
        game.headers["Result"] = (
            self.board.result(claim_draw=True)
        )

        node = game

        for move in self.board.move_stack:
            node = node.add_variation(move)

        with (self.log_dir / "game.pgn").open(
            "w", encoding="utf-8"
        ) as file:
            print(game, file=file)

        if self.records:
            with (self.log_dir / "moves.csv").open(
                "w", newline="", encoding="utf-8"
            ) as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=list(self.records[0].keys()),
                )
                writer.writeheader()
                writer.writerows(self.records)

        state = {
            "our_color": (
                "white" if self.our_color else "black"
            ),
            "depth": self.depth,
            "think_time": self.think_time,
            "fen": self.board.fen(),
            "moves": [
                record["uci"]
                for record in self.records
            ],
            "records": self.records,
        }

        temporary = self.log_dir / "state.tmp"

        with temporary.open(
            "w", encoding="utf-8"
        ) as file:
            json.dump(
                state,
                file,
                indent=2,
                ensure_ascii=False,
            )

        temporary.replace(
            self.log_dir / "state.json"
        )

    def close(self):
        if self.started:
            self.save_logs()
        self.root.destroy()


def main():
    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    root = tk.Tk()
    ChessCompetitionApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
