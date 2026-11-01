import argparse
import csv
import queue
import sys
import threading
import time
import tkinter as tk

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import chess
import chess.engine
import chess.pgn

try:
    from chess_engine.engine import ChessEngine
except ModuleNotFoundError:
    sys.path.insert(
        0,
        str(Path(__file__).resolve().parents[1] / "src"),
    )
    from chess_engine.engine import ChessEngine


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_STOCKFISH = (
    ROOT
    / "engines"
    / "stockfish"
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
SQUARE = 64

MOVE_FIELDS = [
    "game_id", "elo", "strategy", "ply",
    "fullmove", "color", "player", "san", "uci",
    "fen_before", "fen_after", "score_cp",
    "depth", "status", "elapsed_seconds",
    "negamax_nodes", "quiescence_nodes",
    "total_nodes", "alpha_beta_cutoffs",
    "tt_hits", "tt_misses", "tt_stores",
    "tt_hit_rate",
]

SUMMARY_FIELDS = [
    "game_id", "elo", "strategy", "our_color",
    "result", "our_result", "termination",
    "plies", "our_moves", "stockfish_moves",
    "our_total_seconds", "stockfish_total_seconds",
    "our_average_depth", "our_total_nodes",
    "our_timeouts", "pgn_file", "moves_file",
]


@dataclass(frozen=True)
class GameConfig:
    game_id: int
    elo: int
    our_color: chess.Color


class MatchRecorder:
    def __init__(self, output: Path):
        self.output = output
        self.output.mkdir(parents=True, exist_ok=True)
        self.summaries = []
        self.summary_path = output / "summary.csv"

    def paths(self, config: GameConfig):
        color = "white" if config.our_color else "black"
        prefix = (
            f"game_{config.game_id:03d}_"
            f"elo_{config.elo}_{color}"
        )
        return (
            self.output / f"{prefix}.pgn",
            self.output / f"{prefix}_moves.csv",
        )

    @staticmethod
    def write_csv(path, fields, rows):
        with path.open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fields,
            )
            writer.writeheader()
            writer.writerows(rows)

    def save_game(self, config, game, moves):
        pgn_path, csv_path = self.paths(config)

        with pgn_path.open(
            "w", encoding="utf-8"
        ) as file:
            print(game, file=file)

        self.write_csv(
            csv_path,
            MOVE_FIELDS,
            moves,
        )

        return pgn_path, csv_path

    def save_summary(self, summary):
        self.summaries.append(summary)
        self.write_csv(
            self.summary_path,
            SUMMARY_FIELDS,
            self.summaries,
        )


def build_schedule(levels, games_per_level, first_color):
    schedule = []

    initial_color = (
        chess.WHITE
        if first_color == "white"
        else chess.BLACK
    )

    for elo in levels:
        for index in range(games_per_level):
            color = (
                initial_color
                if index % 2 == 0
                else not initial_color
            )

            schedule.append(
                GameConfig(
                    game_id=len(schedule) + 1,
                    elo=elo,
                    our_color=color,
                )
            )

    return schedule


class StockfishMatchVisual:
    def __init__(
        self,
        root,
        stockfish_path,
        depth,
        our_time,
        stockfish_time,
        levels,
        games_per_level,
        first_color,
        max_plies,
        output,
        score_quiet_checks=True,
    ):
        self.root = root
        self.stockfish_path = stockfish_path
        self.depth = depth
        self.our_time = our_time
        self.stockfish_time = stockfish_time
        self.max_plies = max_plies

        self.score_quiet_checks = score_quiet_checks
        self.strategy = (
            "original"
            if score_quiet_checks
            else "optimized"
        )

        self.schedule = build_schedule(
            levels,
            games_per_level,
            first_color,
        )

        self.recorder = MatchRecorder(output)

        self.game_index = 0
        self.config = self.schedule[0]

        self.our_engine = ChessEngine(
            max_depth=depth,
            score_quiet_checks=score_quiet_checks,
        )

        self.messages = queue.Queue()
        self.generation = 0
        self.thinking = False
        self.pending_result = None
        self.running = False
        self.step_requested = False
        self.finished = False
        self.series_finished = False
        self.next_move_at = 0.0
        self.next_game_at = None

        self.speed_var = tk.DoubleVar(value=0.3)
        self.status_var = tk.StringVar(
            value="Pronto para iniciar."
        )
        self.turn_var = tk.StringVar()
        self.info_var = tk.StringVar(
            value="Aguardando primeiro lance."
        )
        self.progress_var = tk.StringVar()
        self.stats_var = tk.StringVar()
        self.path_var = tk.StringVar(
            value=f"Logs: {output}"
        )

        self.root.title(
            f"Chess Challenge III vs Stockfish "
            f"— {self.strategy}"
        )
        self.root.geometry("1100x740")
        self.root.minsize(930, 650)

        self.build_interface()
        self.prepare_game()

        self.root.after(
            50,
            self.update_loop,
        )

    def prepare_game(self):
        self.config = self.schedule[self.game_index]
        self.board = chess.Board()

        self.our_engine.clear_cache()

        self.game = chess.pgn.Game()
        self.game.headers["Event"] = (
            "Chess Challenge III vs Stockfish"
        )
        self.game.headers["Date"] = (
            datetime.now().strftime("%Y.%m.%d")
        )
        self.game.headers["Round"] = str(
            self.config.game_id
        )
        self.game.headers["White"] = (
            "ChessEngine"
            if self.config.our_color
            else "Stockfish 19"
        )
        self.game.headers["Black"] = (
            "Stockfish 19"
            if self.config.our_color
            else "ChessEngine"
        )
        self.game.headers["Result"] = "*"
        self.game.headers["StockfishElo"] = str(
            self.config.elo
        )
        self.game.headers["OurDepth"] = str(
            self.depth
        )
        self.game.headers["OrderingStrategy"] = (
            self.strategy
        )
        self.game.headers["ScoreQuietChecks"] = str(
            self.score_quiet_checks
        )
        self.game.headers["OurTimePerMove"] = str(
            self.our_time
        )
        self.game.headers["StockfishTimePerMove"] = str(
            self.stockfish_time
        )

        self.game_node = self.game
        self.moves = []
        self.last_move = None
        self.finished = False
        self.next_game_at = None
        self.pending_result = None

        self.our_seconds = 0.0
        self.stockfish_seconds = 0.0
        self.our_depth_sum = 0
        self.our_nodes = 0
        self.our_moves = 0
        self.stockfish_moves = 0
        self.our_timeouts = 0

        self.clear_history()
        self.draw_board()
        self.update_turn()
        self.update_progress()

        self.info_var.set(
            "Aguardando primeiro lance."
        )
        self.status_var.set(
            "Partida preparada."
        )

        self.recorder.save_game(
            self.config,
            self.game,
            self.moves,
        )

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
            anchor=tk.N,
            padx=(0, 20),
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
            width=SQUARE * 8,
            height=SQUARE * 8,
            highlightthickness=0,
        )
        self.canvas.pack()

        ttk.Label(
            left,
            textvariable=self.turn_var,
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=(12, 5))

        ttk.Label(
            left,
            textvariable=self.info_var,
            wraplength=520,
        ).pack(pady=5)

        ttk.Label(
            right,
            text="Bateria de partidas",
            font=("Segoe UI", 16, "bold"),
        ).pack(
            anchor=tk.W,
            pady=(0, 12),
        )

        ttk.Label(
            right,
            textvariable=self.progress_var,
            font=("Segoe UI", 11, "bold"),
        ).pack(
            anchor=tk.W,
            pady=4,
        )

        ttk.Label(
            right,
            textvariable=self.stats_var,
        ).pack(
            anchor=tk.W,
            pady=4,
        )

        controls = ttk.Frame(right)
        controls.pack(
            fill=tk.X,
            pady=12,
        )

        buttons = [
            ("Iniciar / Continuar", self.start),
            ("Pausar", self.pause),
            ("Próximo lance", self.step),
            ("Salvar PGN", self.save_pgn),
            ("Abrir pasta de logs", self.show_log_path),
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

        controls.columnconfigure(
            0,
            weight=1,
        )
        controls.columnconfigure(
            1,
            weight=1,
        )

        ttk.Label(
            right,
            text="Intervalo visual entre lances",
        ).pack(anchor=tk.W)

        ttk.Scale(
            right,
            from_=0,
            to=3,
            variable=self.speed_var,
            orient=tk.HORIZONTAL,
        ).pack(
            fill=tk.X,
            pady=(5, 12),
        )

        ttk.Label(
            right,
            text="Histórico da partida",
            font=("Segoe UI", 13, "bold"),
        ).pack(
            anchor=tk.W,
            pady=(8, 6),
        )

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
            font=("Consolas", 10),
            state=tk.DISABLED,
            yscrollcommand=scrollbar.set,
        )
        self.history.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
        )
        scrollbar.config(
            command=self.history.yview
        )

        ttk.Label(
            right,
            textvariable=self.status_var,
            wraplength=430,
        ).pack(
            anchor=tk.W,
            pady=(10, 5),
        )

        ttk.Label(
            right,
            textvariable=self.path_var,
            wraplength=430,
        ).pack(anchor=tk.W)

    def draw_board(self):
        self.canvas.delete("all")

        for rank in range(7, -1, -1):
            for file in range(8):
                square = chess.square(
                    file,
                    rank,
                )

                if self.config.our_color == chess.WHITE:
                    display_file = file
                    display_rank = 7 - rank
                else:
                    display_file = 7 - file
                    display_rank = rank

                x = display_file * SQUARE
                y = display_rank * SQUARE

                color = (
                    LIGHT
                    if (file + rank) % 2
                    else DARK
                )

                if (
                    self.last_move
                    and square in (
                        self.last_move.from_square,
                        self.last_move.to_square,
                    )
                ):
                    color = LAST_MOVE

                if self.board.is_check():
                    king = self.board.king(
                        self.board.turn
                    )
                    if square == king:
                        color = CHECK

                self.canvas.create_rectangle(
                    x,
                    y,
                    x + SQUARE,
                    y + SQUARE,
                    fill=color,
                    outline=color,
                )

                piece = self.board.piece_at(square)

                if piece:
                    self.canvas.create_text(
                        x + SQUARE / 2,
                        y + SQUARE / 2,
                        text=PIECES[piece.symbol()],
                        font=("Segoe UI Symbol", 42),
                        fill=(
                            "#FFFFFF"
                            if piece.color
                            else "#111111"
                        ),
                    )

                if display_file == 0:
                    self.canvas.create_text(
                        x + 9,
                        y + 10,
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
        color = (
            "Brancas"
            if self.board.turn
            else "Pretas"
        )
        player = (
            "ChessEngine"
            if self.board.turn == self.config.our_color
            else "Stockfish 19"
        )

        self.turn_var.set(
            f"{color}: {player}"
        )

    def update_progress(self):
        color = (
            "brancas"
            if self.config.our_color == chess.WHITE
            else "pretas"
        )

        self.progress_var.set(
            f"Partida {self.game_index + 1}/"
            f"{len(self.schedule)} "
            f"| Stockfish Elo {self.config.elo} "
            f"| ChessEngine de {color} "
            f"| Estratégia: {self.strategy}"
        )

        wins = sum(
            row["our_result"] == "win"
            for row in self.recorder.summaries
        )
        draws = sum(
            row["our_result"] == "draw"
            for row in self.recorder.summaries
        )
        losses = sum(
            row["our_result"] == "loss"
            for row in self.recorder.summaries
        )
        unfinished = sum(
            row["our_result"] == "unfinished"
            for row in self.recorder.summaries
        )

        self.stats_var.set(
            f"Resultados: {wins}V / {draws}E / "
            f"{losses}D / {unfinished} inconclusivas"
        )

    def append_history(self, text):
        self.history.config(state=tk.NORMAL)
        self.history.insert(
            tk.END,
            text + "\n",
        )
        self.history.see(tk.END)
        self.history.config(state=tk.DISABLED)

    def clear_history(self):
        self.history.config(state=tk.NORMAL)
        self.history.delete(
            "1.0",
            tk.END,
        )
        self.history.config(state=tk.DISABLED)

    def start(self):
        if self.series_finished:
            self.status_var.set(
                "A bateria já terminou."
            )
            return

        self.running = True
        self.step_requested = False
        self.status_var.set(
            "Bateria em andamento."
        )

    def pause(self):
        self.running = False
        self.step_requested = False
        self.status_var.set(
            "Pausado. A busca atual terminará normalmente."
        )

    def step(self):
        if self.series_finished or self.finished:
            return

        self.running = False
        self.step_requested = True
        self.status_var.set(
            "Executando um lance."
        )

    def show_log_path(self):
        messagebox.showinfo(
            "Logs da bateria",
            str(self.recorder.output),
        )

    def start_search(self):
        self.thinking = True

        generation = self.generation
        board = self.board.copy(stack=True)

        is_ours = (
            board.turn == self.config.our_color
        )
        elo = self.config.elo

        self.status_var.set(
            "ChessEngine pensando..."
            if is_ours
            else "Stockfish pensando..."
        )

        def worker():
            try:
                if is_ours:
                    result = self.our_engine.best_move(
                        board,
                        time_limit=self.our_time,
                    )

                    payload = {
                        "move": result.move,
                        "elapsed": result.elapsed,
                        "score_cp": result.score,
                        "depth": result.depth,
                        "status": result.status,
                        "metrics": result.metrics,
                        "cache": result.cache,
                    }

                else:
                    start = time.monotonic()

                    with chess.engine.SimpleEngine.popen_uci(
                        str(self.stockfish_path)
                    ) as stockfish:
                        stockfish.configure({
                            "Threads": 1,
                            "Hash": 16,
                            "UCI_LimitStrength": True,
                            "UCI_Elo": elo,
                        })

                        result = stockfish.play(
                            board,
                            chess.engine.Limit(
                                time=self.stockfish_time
                            ),
                        )

                    payload = {
                        "move": result.move,
                        "elapsed": (
                            time.monotonic() - start
                        ),
                        "score_cp": "",
                        "depth": "",
                        "status": "completed",
                        "metrics": {},
                        "cache": {},
                    }

                self.messages.put(
                    (generation, payload, None)
                )

            except Exception as exc:
                self.messages.put(
                    (generation, None, str(exc))
                )

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()

    def apply_result(self, payload):
        move = payload["move"]

        if move not in self.board.legal_moves:
            self.running = False
            self.status_var.set(
                f"Erro: movimento ilegal: {move}"
            )
            return

        is_ours = (
            self.board.turn == self.config.our_color
        )

        color = self.board.turn
        player = (
            "ChessEngine"
            if is_ours
            else "Stockfish"
        )

        san = self.board.san(move)
        fen_before = self.board.fen()
        fullmove = self.board.fullmove_number

        metrics = payload["metrics"]
        cache = payload["cache"]
        elapsed = payload["elapsed"]

        self.game_node = (
            self.game_node.add_variation(move)
        )

        self.board.push(move)
        self.last_move = move

        row = {
            "game_id": self.config.game_id,
            "elo": self.config.elo,
            "strategy": self.strategy,
            "ply": self.board.ply(),
            "fullmove": fullmove,
            "color": (
                "white" if color else "black"
            ),
            "player": player,
            "san": san,
            "uci": move.uci(),
            "fen_before": fen_before,
            "fen_after": self.board.fen(),
            "score_cp": payload["score_cp"],
            "depth": payload["depth"],
            "status": payload["status"],
            "elapsed_seconds": round(
                elapsed, 4
            ),
            "negamax_nodes": metrics.get(
                "negamax_nodes", ""
            ),
            "quiescence_nodes": metrics.get(
                "quiescence_nodes", ""
            ),
            "total_nodes": metrics.get(
                "total_nodes", ""
            ),
            "alpha_beta_cutoffs": metrics.get(
                "alpha_beta_cutoffs", ""
            ),
            "tt_hits": cache.get("hits", ""),
            "tt_misses": cache.get("misses", ""),
            "tt_stores": cache.get("stores", ""),
            "tt_hit_rate": cache.get("hit_rate", ""),
        }

        self.moves.append(row)

        if is_ours:
            self.our_seconds += elapsed
            self.our_moves += 1
            self.our_depth_sum += payload["depth"]
            self.our_nodes += metrics.get(
                "total_nodes", 0
            )

            if payload["status"] in (
                "timeout",
                "fallback",
            ):
                self.our_timeouts += 1
        else:
            self.stockfish_seconds += elapsed
            self.stockfish_moves += 1

        notation = (
            f"{fullmove}. {san}"
            if color == chess.WHITE
            else f"{fullmove}... {san}"
        )

        self.append_history(
            f"{notation:14} "
            f"{player:12} "
            f"{elapsed:.2f}s"
        )

        if is_ours:
            self.info_var.set(
                f"Prof. {payload['depth']} | "
                f"Avaliação {payload['score_cp']:+} cp | "
                f"Nós {metrics.get('total_nodes', 0)} | "
                f"{payload['status']}"
            )
        else:
            self.info_var.set(
                f"Stockfish Elo {self.config.elo} | "
                f"Tempo {elapsed:.2f}s"
            )

        self.draw_board()
        self.update_turn()

        self.recorder.save_game(
            self.config,
            self.game,
            self.moves,
        )

        if self.board.is_game_over(
            claim_draw=True
        ):
            self.finish_game()
        elif self.board.ply() >= self.max_plies:
            self.finish_game(move_limit=True)
        else:
            self.status_var.set(
                "Aguardando próximo lance."
            )

        self.next_move_at = (
            time.monotonic()
            + self.speed_var.get()
        )

    def finish_game(self, move_limit=False):
        self.finished = True
        self.step_requested = False

        outcome = self.board.outcome(
            claim_draw=True
        )

        result = (
            outcome.result()
            if outcome is not None
            else "*"
        )

        termination = (
            "move_limit"
            if move_limit and outcome is None
            else outcome.termination.name
            if outcome is not None
            else "unfinished"
        )

        if outcome is None:
            our_result = "unfinished"
        elif outcome.winner is None:
            our_result = "draw"
        elif outcome.winner == self.config.our_color:
            our_result = "win"
        else:
            our_result = "loss"

        self.game.headers["Result"] = result
        self.game.headers["Termination"] = termination

        pgn_path, moves_path = (
            self.recorder.save_game(
                self.config,
                self.game,
                self.moves,
            )
        )

        summary = {
            "game_id": self.config.game_id,
            "elo": self.config.elo,
            "strategy": self.strategy,
            "our_color": (
                "white"
                if self.config.our_color
                else "black"
            ),
            "result": result,
            "our_result": our_result,
            "termination": termination,
            "plies": self.board.ply(),
            "our_moves": self.our_moves,
            "stockfish_moves": self.stockfish_moves,
            "our_total_seconds": round(
                self.our_seconds, 3
            ),
            "stockfish_total_seconds": round(
                self.stockfish_seconds, 3
            ),
            "our_average_depth": (
                round(
                    self.our_depth_sum
                    / self.our_moves,
                    2,
                )
                if self.our_moves
                else 0
            ),
            "our_total_nodes": self.our_nodes,
            "our_timeouts": self.our_timeouts,
            "pgn_file": pgn_path.name,
            "moves_file": moves_path.name,
        }

        self.recorder.save_summary(summary)
        self.update_progress()

        self.append_history(
            f"\nResultado: {result} | {termination}"
        )

        if self.game_index + 1 >= len(self.schedule):
            self.series_finished = True
            self.running = False
            self.status_var.set(
                "Bateria concluída! "
                "Consulte summary.csv."
            )
        else:
            self.status_var.set(
                f"Partida {self.config.game_id} concluída. "
                "Preparando próxima partida..."
            )

            self.next_game_at = (
                time.monotonic()
                + max(
                    1.0,
                    self.speed_var.get(),
                )
            )

    def advance_game(self):
        if self.game_index + 1 >= len(self.schedule):
            return

        self.game_index += 1
        self.prepare_game()

        self.next_move_at = (
            time.monotonic() + 0.5
        )

    def save_pgn(self):
        destination = filedialog.asksaveasfilename(
            title="Exportar partida atual",
            initialdir=str(
                self.recorder.output
            ),
            initialfile=(
                f"game_{self.config.game_id:03d}.pgn"
            ),
            defaultextension=".pgn",
            filetypes=[
                ("Partidas PGN", "*.pgn")
            ],
        )

        if not destination:
            return

        try:
            with open(
                destination,
                "w",
                encoding="utf-8",
            ) as file:
                print(self.game, file=file)

            self.status_var.set(
                "PGN exportado."
            )
        except OSError as exc:
            messagebox.showerror(
                "Erro",
                str(exc),
            )

    def update_loop(self):
        try:
            while True:
                generation, payload, error = (
                    self.messages.get_nowait()
                )

                if generation != self.generation:
                    continue

                self.thinking = False

                if error:
                    self.running = False
                    self.step_requested = False
                    self.status_var.set(
                        f"Erro: {error}"
                    )
                else:
                    self.pending_result = payload

        except queue.Empty:
            pass

        if (
            self.pending_result is not None
            and (
                self.running
                or self.step_requested
            )
        ):
            payload = self.pending_result
            self.pending_result = None

            self.apply_result(payload)
            self.step_requested = False

        now = time.monotonic()

        if (
            self.finished
            and not self.series_finished
            and self.running
            and self.next_game_at is not None
            and now >= self.next_game_at
        ):
            self.advance_game()

        if (
            not self.finished
            and not self.thinking
            and self.pending_result is None
            and (
                self.running
                or self.step_requested
            )
            and now >= self.next_move_at
        ):
            self.start_search()

        self.root.after(
            50,
            self.update_loop,
        )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Bateria visual de partidas "
            "ChessEngine vs Stockfish, "
            "com logs CSV e PGN automáticos."
        )
    )

    parser.add_argument(
        "--stockfish",
        type=Path,
        default=DEFAULT_STOCKFISH,
    )

    parser.add_argument(
        "--depth",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--score-quiet-checks",
        choices=("true", "false"),
        default="true",
        help=(
            "true: ordenação original; "
            "false: ordenação otimizada."
        ),
    )

    parser.add_argument(
        "--our-time",
        type=float,
        default=1.0,
    )

    parser.add_argument(
        "--stockfish-time",
        type=float,
        default=0.1,
    )

    parser.add_argument(
        "--elo-levels",
        type=int,
        nargs="+",
        default=[1320],
    )

    parser.add_argument(
        "--games-per-level",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--our-color",
        choices=("white", "black"),
        default="white",
    )

    parser.add_argument(
        "--max-plies",
        type=int,
        default=300,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )

    args = parser.parse_args()

    if not args.stockfish.is_file():
        parser.error(
            f"Stockfish não encontrado: "
            f"{args.stockfish}"
        )

    if args.depth < 1:
        parser.error(
            "--depth deve ser pelo menos 1"
        )

    if (
        args.our_time <= 0
        or args.stockfish_time <= 0
    ):
        parser.error(
            "Os tempos devem ser positivos"
        )

    if args.games_per_level < 1:
        parser.error(
            "--games-per-level deve ser pelo menos 1"
        )

    if args.max_plies < 1:
        parser.error(
            "--max-plies deve ser pelo menos 1"
        )

    if any(
        not 1320 <= elo <= 3190
        for elo in args.elo_levels
    ):
        parser.error(
            "Todos os níveis Elo devem estar "
            "entre 1320 e 3190"
        )

    score_quiet_checks = (
        args.score_quiet_checks == "true"
    )

    strategy = (
        "original"
        if score_quiet_checks
        else "optimized"
    )

    output = args.output

    if output is None:
        timestamp = (
            datetime.now().strftime(
                "%Y%m%d_%H%M%S_%f"
            )
        )

        output = (
            ROOT
            / "benchmarks"
            / "stockfish_matches"
            / strategy
            / f"run_{timestamp}"
        )

    root = tk.Tk()

    StockfishMatchVisual(
        root=root,
        stockfish_path=args.stockfish,
        depth=args.depth,
        our_time=args.our_time,
        stockfish_time=args.stockfish_time,
        levels=args.elo_levels,
        games_per_level=args.games_per_level,
        first_color=args.our_color,
        max_plies=args.max_plies,
        output=output,
        score_quiet_checks=score_quiet_checks,
    )

    root.mainloop()


if __name__ == "__main__":
    main()