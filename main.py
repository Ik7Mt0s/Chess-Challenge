
import csv
import json
import queue
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import chess
import chess.pgn

from chess_engine.engine import ChessEngine
from chess_engine.evaluation.heuristic import HeuristicEvaluator
from chess_engine.evaluation.neural import HybridEvaluator, NeuralEvaluator


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "competition_logs"
MODEL_PATH = BASE_DIR / "weights" / "simple_chess_net.pth"

COMPETITION_DEPTH = 4
COMPETITION_TIME = 5.0
NEURAL_WEIGHT = 0.40
NEURAL_BUDGET = 128
NEURAL_LAZY_THRESHOLD = 300
NEURAL_CACHE_SIZE = 4096
TT_MAX_ENTRIES = 20_000

LIGHT = "#EEEED2"
DARK = "#769656"
SELECTED = "#F6F669"
LAST_MOVE = "#BACA44"
TARGET = "#4D8754"

CHECK_SQUARE = "#E76F6F"
CHECKMATE_SQUARE = "#BD3434"
CHECK_BORDER = "#8B1E1E"

WHITE_FILL = "#FFFDF5"
WHITE_OUTLINE = "#242A30"
BLACK_FILL = "#202428"
BLACK_OUTLINE = "#F5F0DD"

PIECE_FONT = ("Segoe UI Symbol", 46)

OUTLINE_OFFSETS = [
    (-2, -2), (-2, 0), (-2, 2),
    (0, -2),           (0, 2),
    (2, -2),  (2, 0),  (2, 2),
]

PIECES = dict(zip(
    "KQRBNPkqrbnp",
    "♚♛♜♝♞♟♚♛♜♝♞♟",
))


def create_competition_engine(
    depth=COMPETITION_DEPTH,
):
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Modelo neural nao encontrado: {MODEL_PATH}"
        )

    evaluator = HybridEvaluator(
        heuristic=HeuristicEvaluator(),
        neural=NeuralEvaluator(model_path=MODEL_PATH),
        weight_neural=NEURAL_WEIGHT,
        lazy_threshold=NEURAL_LAZY_THRESHOLD,
        max_neural_inferences=NEURAL_BUDGET,
        neural_cache_size=NEURAL_CACHE_SIZE,
        use_king_safety=False,
    )

    return ChessEngine(
        evaluator=evaluator,
        max_depth=depth,
        use_full_time=True,
        early_stop_enabled=True,
        use_transposition_table=True,
        tt_max_entries=TT_MAX_ENTRIES,
        use_advanced_ordering=True,
        score_quiet_checks=True,
    )


def replay_moves(moves):
    """
    Reconstrói o tabuleiro desde a posição inicial.

    Todos os movimentos são validados antes da
    recuperação da partida.
    """
    board = chess.Board()

    for number, uci in enumerate(moves, start=1):
        move = chess.Move.from_uci(uci)

        if move not in board.legal_moves:
            raise ValueError(
                f"Lance {number} invalido no log: {uci}"
            )

        board.push(move)

    return board


def reconstruct_records(board, our_color):
    """
    Reconstrói o histórico de movimentos para
    recuperação a partir de PGN ou logs antigos.
    """
    temporary = board.root()
    records = []

    for move in board.move_stack:
        color = temporary.turn
        fen_before = temporary.fen()
        san = temporary.san(move)

        temporary.push(move)

        records.append({
            "ply": temporary.ply(),
            "player": (
                "engine"
                if color == our_color
                else "opponent"
            ),
            "color": (
                "white"
                if color == chess.WHITE
                else "black"
            ),
            "san": san,
            "uci": move.uci(),
            "fen_before": fen_before,
            "fen_after": temporary.fen(),
            "score_cp": "",
            "depth": "",
            "elapsed_seconds": "",
            "search_status": "",
            "total_nodes": "",
            "quiescence_nodes": "",
            "neural_inferences": "",
        })

    return records


def load_saved_game(path):
    """
    Carrega e valida uma partida salva.

    Aceita state.json e game.pgn.
    Não altera os arquivos durante a leitura.
    """
    path = Path(path)

    if path.name == "state.json":
        with path.open("r", encoding="utf-8") as stream:
            state = json.load(stream)

        if (
            not isinstance(state, dict)
            or state.get("our_color") not in (
                "white",
                "black",
            )
        ):
            raise ValueError(
                "state.json nao possui cor valida."
            )

        moves = state.get("moves")

        if (
            not isinstance(moves, list)
            or not all(
                isinstance(move, str)
                for move in moves
            )
        ):
            raise ValueError(
                "state.json nao possui lista "
                "de lances valida."
            )

        board = replay_moves(moves)

        if state.get("fen") != board.fen():
            raise ValueError(
                "FEN salvo nao confere com os lances. "
                "Escolha game.pgn para recuperar."
            )

        color = (
            chess.WHITE
            if state["our_color"] == "white"
            else chess.BLACK
        )

        depth = int(
            state.get("depth", COMPETITION_DEPTH)
        )

        think_time = float(
            state.get("think_time", COMPETITION_TIME)
        )

        if (
            not 1 <= depth <= 30
            or not 0 < think_time <= 3600
        ):
            raise ValueError(
                "Profundidade ou tempo invalido "
                "no arquivo."
            )

        records = state.get("records")

        if (
            not isinstance(records, list)
            or len(records) != len(moves)
            or any(
                not isinstance(record, dict)
                or record.get("uci") != uci
                for record, uci in zip(records, moves)
            )
        ):
            records = reconstruct_records(
                board,
                color,
            )
        else:
            # Reconstrói os campos obrigatórios
            # e preserva as métricas do log.
            base_records = reconstruct_records(
                board,
                color,
            )

            protected_fields = {
                "ply",
                "player",
                "color",
                "san",
                "uci",
                "fen_before",
                "fen_after",
            }

            records = [
                {
                    **base,
                    **{
                        key: old.get(key, "")
                        for key in base
                        if key not in protected_fields
                    },
                }
                for base, old in zip(
                    base_records,
                    records,
                )
            ]

        return (
            board,
            color,
            depth,
            think_time,
            records,
        )

    if path.suffix.lower() == ".pgn":
        with path.open(
            "r",
            encoding="utf-8-sig",
        ) as stream:
            game = chess.pgn.read_game(stream)

        if game is None or game.errors:
            raise ValueError(
                "PGN invalido ou vazio."
            )

        if game.headers.get("White") == "ChessEngine":
            color = chess.WHITE

        elif game.headers.get("Black") == "ChessEngine":
            color = chess.BLACK

        else:
            raise ValueError(
                "PGN nao identifica a cor do ChessEngine."
            )

        board = replay_moves([
            move.uci()
            for move in game.mainline_moves()
        ])

        depth = int(
            game.headers.get(
                "OurDepth",
                COMPETITION_DEPTH,
            )
        )

        think_time = float(
            game.headers.get(
                "OurTimePerMove",
                COMPETITION_TIME,
            )
        )

        if (
            not 1 <= depth <= 30
            or not 0 < think_time <= 3600
        ):
            raise ValueError(
                "Profundidade ou tempo invalido no PGN."
            )

        return (
            board,
            color,
            depth,
            think_time,
            reconstruct_records(board, color),
        )

    raise ValueError(
        "Selecione state.json ou game.pgn."
    )


class ChessCompetitionApp:
    def __init__(self, root):
        self.root = root
        self.root.title(
            "Chess Challenge III — Competicao"
        )
        self.root.geometry("1000x760")
        self.root.minsize(900, 690)

        self.board = chess.Board()
        self.engine = None

        self.our_color = chess.WHITE
        self.started = False
        self.thinking = False
        self.selected = None
        self.last_move = None

        self.depth = COMPETITION_DEPTH
        self.think_time = COMPETITION_TIME

        self.generation = 0
        self.results = queue.Queue()

        self.records = []
        self.log_dir = None
        self.finished_notified = False

        self.color_var = tk.StringVar(
            value="white"
        )
        self.depth_var = tk.StringVar(
            value=str(COMPETITION_DEPTH)
        )
        self.time_var = tk.StringVar(
            value=str(int(COMPETITION_TIME))
        )

        self.status_var = tk.StringVar(
            value="Configure a partida ou retome um log."
        )
        self.analysis_var = tk.StringVar(
            value="Nenhuma analise."
        )
        self.turn_var = tk.StringVar(
            value="Partida nao iniciada"
        )
        self.game_alert_var = tk.StringVar(
            value="Aguardando inicio da partida"
        )

        self.square_size = 70

        self.build_ui()
        self.refresh()

        self.root.after(
            100,
            self.poll_results,
        )

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close,
        )

    def build_ui(self):
        main = ttk.Frame(
            self.root,
            padding=15,
        )
        main.pack(
            fill=tk.BOTH,
            expand=True,
        )

        board_area = ttk.Frame(main)
        board_area.pack(
            side=tk.LEFT,
            anchor=tk.N,
        )

        self.canvas = tk.Canvas(
            board_area,
            width=560,
            height=560,
            highlightthickness=0,
        )
        self.canvas.pack()
        self.canvas.bind(
            "<Button-1>",
            self.on_board_click,
        )

        self.game_alert = tk.Label(
            board_area,
            textvariable=self.game_alert_var,
            font=("Segoe UI", 13, "bold"),
            fg="#333333",
            bg="#E5E7EB",
            pady=9,
            anchor="center",
        )
        self.game_alert.pack(
            fill=tk.X,
            pady=(10, 4),
        )

        ttk.Label(
            board_area,
            textvariable=self.turn_var,
            font=("Segoe UI", 12, "bold"),
        ).pack(pady=5)

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
        ).pack(
            anchor="w",
            pady=(0, 10),
        )

        ttk.Label(
            panel,
            text=(
                "Competicao: HybridEvaluator | "
                "Rede 40% | Orcamento 128"
            ),
            wraplength=330,
        ).pack(
            anchor="w",
            pady=(0, 12),
        )

        config = ttk.LabelFrame(
            panel,
            text="Configuracao da partida",
            padding=12,
        )
        config.pack(fill=tk.X)

        ttk.Label(
            config,
            text="Nossa cor:",
        ).grid(
            row=0,
            column=0,
            sticky="w",
        )

        ttk.Radiobutton(
            config,
            text="Brancas",
            variable=self.color_var,
            value="white",
        ).grid(
            row=0,
            column=1,
            sticky="w",
        )

        ttk.Radiobutton(
            config,
            text="Pretas",
            variable=self.color_var,
            value="black",
        ).grid(
            row=0,
            column=2,
            sticky="w",
        )

        ttk.Label(
            config,
            text="Profundidade inicial:",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            pady=10,
        )

        ttk.Spinbox(
            config,
            from_=1,
            to=30,
            textvariable=self.depth_var,
            width=8,
        ).grid(
            row=1,
            column=1,
            sticky="w",
        )

        ttk.Label(
            config,
            text="Tempo por lance (s):",
        ).grid(
            row=2,
            column=0,
            sticky="w",
        )

        ttk.Entry(
            config,
            textvariable=self.time_var,
            width=10,
        ).grid(
            row=2,
            column=1,
            sticky="w",
        )

        ttk.Label(
            config,
            text="Busca iterativa com limite de tempo.",
            wraplength=320,
        ).grid(
            row=3,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(10, 0),
        )

        ttk.Button(
            panel,
            text="Iniciar nova partida",
            command=self.start_game,
        ).pack(
            fill=tk.X,
            pady=(15, 5),
        )

        # NOVO: recuperacao de partida
        ttk.Button(
            panel,
            text="Retomar partida salva",
            command=self.resume_game,
        ).pack(
            fill=tk.X,
            pady=5,
        )

        self.calculate_button = ttk.Button(
            panel,
            text="Calcular jogada do motor",
            command=self.calculate,
        )
        self.calculate_button.pack(
            fill=tk.X,
            pady=5,
        )

        ttk.Button(
            panel,
            text="Desfazer ultima jogada",
            command=self.undo,
        ).pack(
            fill=tk.X,
            pady=5,
        )

        ttk.Label(
            panel,
            text="Analise do motor",
            font=("Segoe UI", 12, "bold"),
        ).pack(
            anchor="w",
            pady=(15, 5),
        )

        ttk.Label(
            panel,
            textvariable=self.analysis_var,
            wraplength=320,
            justify=tk.LEFT,
        ).pack(anchor="w")

        ttk.Label(
            panel,
            text="Historico de movimentos",
            font=("Segoe UI", 12, "bold"),
        ).pack(
            anchor="w",
            pady=(15, 5),
        )

        history_frame = ttk.Frame(panel)
        history_frame.pack(
            fill=tk.BOTH,
            expand=True,
        )

        scrollbar = ttk.Scrollbar(
            history_frame
        )
        scrollbar.pack(
            side=tk.RIGHT,
            fill=tk.Y,
        )

        self.history = tk.Text(
            history_frame,
            font=("Consolas", 11),
            state=tk.DISABLED,
            height=10,
            yscrollcommand=scrollbar.set,
        )
        self.history.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
        )

        scrollbar.configure(
            command=self.history.yview
        )

        ttk.Label(
            panel,
            textvariable=self.status_var,
            wraplength=330,
        ).pack(
            anchor="w",
            pady=10,
        )

    def square_from_display(
        self,
        row,
        col,
    ):
        if self.our_color == chess.WHITE:
            return chess.square(
                col,
                7 - row,
            )

        return chess.square(
            7 - col,
            row,
        )

    def draw_piece(
        self,
        square,
        x,
        y,
    ):
        piece = self.board.piece_at(square)

        if piece is None:
            return

        symbol = PIECES[piece.symbol()]

        if piece.color == chess.WHITE:
            fill = WHITE_FILL
            outline = WHITE_OUTLINE
        else:
            fill = BLACK_FILL
            outline = BLACK_OUTLINE

        cx = x + 35
        cy = y + 35

        for dx, dy in OUTLINE_OFFSETS:
            self.canvas.create_text(
                cx + dx,
                cy + dy,
                text=symbol,
                font=PIECE_FONT,
                fill=outline,
            )

        self.canvas.create_text(
            cx,
            cy,
            text=symbol,
            font=PIECE_FONT,
            fill=fill,
        )

    def draw_board(self):
        self.canvas.delete("all")

        legal_targets = set()

        if self.selected is not None:
            legal_targets = {
                move.to_square
                for move in self.board.legal_moves
                if move.from_square == self.selected
            }

        checked_king = (
            self.board.king(self.board.turn)
            if self.board.is_check()
            else None
        )

        for row in range(8):
            for col in range(8):
                square = self.square_from_display(
                    row,
                    col,
                )

                x = col * 70
                y = row * 70

                file = chess.square_file(square)
                rank = chess.square_rank(square)

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

                if square == self.selected:
                    color = SELECTED

                if square == checked_king:
                    color = (
                        CHECKMATE_SQUARE
                        if self.board.is_checkmate()
                        else CHECK_SQUARE
                    )

                self.canvas.create_rectangle(
                    x,
                    y,
                    x + 70,
                    y + 70,
                    fill=color,
                    outline=color,
                )

                if square == checked_king:
                    self.canvas.create_rectangle(
                        x + 3,
                        y + 3,
                        x + 67,
                        y + 67,
                        outline=CHECK_BORDER,
                        width=3,
                    )

                if square in legal_targets:
                    self.canvas.create_oval(
                        x + 26,
                        y + 26,
                        x + 44,
                        y + 44,
                        fill=TARGET,
                        outline="",
                    )

                self.draw_piece(
                    square,
                    x,
                    y,
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
                        x + 60,
                        y + 60,
                        text=chess.FILE_NAMES[file],
                        font=("Segoe UI", 9, "bold"),
                    )

    def game_result(self):
        outcome = self.board.outcome(
            claim_draw=True
        )

        if outcome is None:
            return None

        if outcome.winner is None:
            return (
                "EMPATE",
                "A partida terminou empatada.",
                "#D9A441",
                "#181818",
                "draw",
            )

        if outcome.winner == self.our_color:
            return (
                "VITORIA DO CHESSENGINE!",
                "Nosso motor venceu a partida!",
                "#237A4B",
                "#FFFFFF",
                "win",
            )

        return (
            "DERROTA DO CHESSENGINE",
            "O adversario venceu a partida.",
            "#B83232",
            "#FFFFFF",
            "loss",
        )

    def update_game_alert(self):
        if not self.started:
            label = "Aguardando inicio da partida"
            bg = "#E5E7EB"
            fg = "#333333"

        elif (result := self.game_result()) is not None:
            label, _, bg, fg, _ = result

        elif self.board.is_check():
            who = (
                "NOSSO REI"
                if self.board.turn == self.our_color
                else "REI ADVERSARIO"
            )

            label = f"XEQUE! {who} AMEACADO"
            bg = "#C63D3D"
            fg = "#FFFFFF"

        elif self.board.turn == self.our_color:
            label = "VEZ DO CHESSENGINE"
            bg = "#285F8F"
            fg = "#FFFFFF"

        else:
            label = "VEZ DO ADVERSARIO"
            bg = "#455466"
            fg = "#FFFFFF"

        self.game_alert_var.set(label)

        self.game_alert.configure(
            bg=bg,
            fg=fg,
        )

    def notify_game_over(self):
        if self.finished_notified:
            return

        result = self.game_result()

        if result is None:
            return

        title, message, _, _, kind = result

        self.finished_notified = True

        self.status_var.set(
            f"{message} Resultado: "
            f"{self.board.result(claim_draw=True)}"
        )

        show = (
            messagebox.showwarning
            if kind == "loss"
            else messagebox.showinfo
        )

        show(
            title,
            (
                f"{message}\n\n"
                f"Resultado: "
                f"{self.board.result(claim_draw=True)}"
            ),
            parent=self.root,
        )

    def start_game(self):
        if self.thinking:
            messagebox.showwarning(
                "Aguarde",
                "O motor ainda esta calculando.",
            )
            return

        if self.started:
            if not messagebox.askyesno(
                "Nova partida",
                "Deseja iniciar uma nova partida?",
            ):
                return

        try:
            depth = int(
                self.depth_var.get()
            )
            think_time = float(
                self.time_var.get()
            )

            if (
                not 1 <= depth <= 30
                or not 0 < think_time <= 3600
            ):
                raise ValueError(
                    "Profundidade ou tempo "
                    "fora dos limites."
                )

            engine = create_competition_engine(
                depth
            )

        except Exception as exc:
            messagebox.showerror(
                "Nao foi possivel iniciar",
                str(exc),
            )
            return

        self.engine = engine
        self.depth = depth
        self.think_time = think_time

        self.our_color = (
            chess.WHITE
            if self.color_var.get() == "white"
            else chess.BLACK
        )

        self.board = chess.Board()
        self.records = []

        self.selected = None
        self.last_move = None
        self.finished_notified = False

        self.started = True
        self.generation += 1

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        self.log_dir = (
            LOG_DIR / f"game_{timestamp}"
        )

        self.log_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.analysis_var.set(
            "Nenhuma analise."
        )

        self.status_var.set(
            "Partida iniciada; estado "
            "salvo automaticamente."
        )

        self.refresh()
        self.save_logs()

    def resume_game(self):
        """
        Recupera uma partida inacabada a partir
        do state.json ou do game.pgn.

        Somente substitui a partida atual quando
        o arquivo e o modelo forem carregados
        com sucesso.
        """
        if self.thinking:
            messagebox.showwarning(
                "Aguarde",
                "O motor ainda esta calculando.",
            )
            return

        if self.started:
            if not messagebox.askyesno(
                "Retomar partida",
                (
                    "Substituir a partida aberta "
                    "por uma partida salva?"
                ),
            ):
                return

        filename = filedialog.askopenfilename(
            parent=self.root,
            title="Escolha state.json ou game.pgn",
            initialdir=str(LOG_DIR),
            filetypes=[
                (
                    "Logs de partida",
                    "state.json game.pgn",
                ),
                ("JSON", "*.json"),
                ("PGN", "*.pgn"),
            ],
        )

        if not filename:
            return

        try:
            path = Path(filename)

            (
                board,
                color,
                depth,
                think_time,
                records,
            ) = load_saved_game(path)

            if board.is_game_over(claim_draw=True):
                raise ValueError(
                    "Essa partida ja terminou. "
                    "Selecione uma partida inacabada."
                )

            engine = create_competition_engine(
                depth
            )

            log_dir = path.parent

        except Exception as exc:
            messagebox.showerror(
                "Falha ao recuperar partida",
                str(exc),
                parent=self.root,
            )
            return

        # Somente agora aplicamos a recuperacao.
        self.board = board
        self.engine = engine
        self.our_color = color

        self.depth = depth
        self.think_time = think_time
        self.records = records

        # Continua salvando na mesma pasta.
        self.log_dir = log_dir

        self.started = True
        self.thinking = False
        self.selected = None

        self.last_move = (
            board.peek()
            if board.move_stack
            else None
        )

        self.finished_notified = False
        self.generation += 1

        self.color_var.set(
            "white"
            if color == chess.WHITE
            else "black"
        )
        self.depth_var.set(str(depth))
        self.time_var.set(str(think_time))

        self.analysis_var.set(
            "Partida recuperada. "
            "Calcule o proximo lance quando "
            "for a vez do motor."
        )

        self.status_var.set(
            f"Recuperados {len(board.move_stack)} "
            f"meios-lances de {path.name}."
        )

        self.refresh()

        # Recria ou atualiza os logs para
        # permitir novas recuperacoes.
        self.save_logs()

    def on_board_click(self, event):
        if (
            not self.started
            or self.thinking
            or self.board.is_game_over(
                claim_draw=True
            )
        ):
            return

        if self.board.turn == self.our_color:
            self.status_var.set(
                "E a vez do motor. "
                "Clique em Calcular jogada."
            )
            return

        col = event.x // 70
        row = event.y // 70

        if not (
            0 <= row < 8
            and 0 <= col < 8
        ):
            return

        square = self.square_from_display(
            row,
            col,
        )

        piece = self.board.piece_at(square)

        if (
            piece
            and piece.color == self.board.turn
        ):
            self.selected = square
            self.draw_board()
            return

        if self.selected is None:
            return

        moves = [
            move
            for move in self.board.legal_moves
            if move.from_square == self.selected
            and move.to_square == square
        ]

        self.selected = None

        if not moves:
            self.status_var.set(
                "Movimento ilegal. "
                "Se houver xeque, proteja o rei."
            )
            self.draw_board()
            return

        if len(moves) > 1:
            move = self.choose_promotion(
                moves
            )

            if move is None:
                self.draw_board()
                return
        else:
            move = moves[0]

        self.apply_move(
            move,
            "opponent",
        )

    def choose_promotion(self, moves):
        dialog = tk.Toplevel(self.root)
        dialog.title("Promocao")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        result = {"move": None}

        ttk.Label(
            dialog,
            text="Escolha a peca para promocao:",
            padding=12,
        ).pack()

        frame = ttk.Frame(
            dialog,
            padding=10,
        )
        frame.pack()

        options = [
            ("Dama", chess.QUEEN),
            ("Torre", chess.ROOK),
            ("Bispo", chess.BISHOP),
            ("Cavalo", chess.KNIGHT),
        ]

        for label, piece_type in options:
            def choose(kind=piece_type):
                result["move"] = next(
                    (
                        move
                        for move in moves
                        if move.promotion == kind
                    ),
                    None,
                )

                dialog.destroy()

            ttk.Button(
                frame,
                text=label,
                command=choose,
            ).pack(
                side=tk.LEFT,
                padx=4,
            )

        dialog.wait_window()

        return result["move"]

    def calculate(self):
        if (
            not self.started
            or self.thinking
            or self.board.is_game_over(
                claim_draw=True
            )
        ):
            return

        if self.board.turn != self.our_color:
            self.status_var.set(
                "Registre a jogada adversaria "
                "no tabuleiro."
            )
            return

        self.thinking = True

        self.calculate_button.configure(
            state=tk.DISABLED
        )

        self.status_var.set(
            "Motor pensando..."
        )

        board_copy = self.board.copy(
            stack=True
        )

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
                (
                    generation,
                    result,
                    error,
                ) = self.results.get_nowait()

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
                    or result.move
                    not in self.board.legal_moves
                ):
                    self.status_var.set(
                        "O motor nao retornou "
                        "um lance legal."
                    )
                    continue

                metrics = result.metrics or {}

                if metrics.get("early_stopped"):
                    reason = "Jogada estabilizada"

                elif result.status == "forced":
                    reason = "Unico lance legal"

                elif result.status == "timeout":
                    reason = "Limite de tempo"

                else:
                    reason = "Busca concluida"

                san = self.board.san(
                    result.move
                )

                self.analysis_var.set(
                    f"Jogada: {san} "
                    f"({result.move.uci()})\n"
                    f"Avaliacao: {result.score:+} cp\n"
                    f"Profundidade: {result.depth}\n"
                    f"Tempo: {result.elapsed:.3f}s\n"
                    f"Nos: "
                    f"{metrics.get('total_nodes', 0)}\n"
                    f"Inferencias neurais: "
                    f"{metrics.get('neural_inferences', 0)}\n"
                    f"Parada: {reason}"
                )

                self.apply_move(
                    result.move,
                    "engine",
                    result,
                )

        except queue.Empty:
            pass

        self.root.after(
            100,
            self.poll_results,
        )

    def apply_move(
        self,
        move,
        player,
        result=None,
    ):
        if move not in self.board.legal_moves:
            return

        color = self.board.turn
        san = self.board.san(move)
        fen_before = self.board.fen()

        self.board.push(move)
        self.last_move = move

        metrics = (
            result.metrics or {}
            if result
            else {}
        )

        record = {
            "ply": self.board.ply(),
            "player": player,
            "color": (
                "white"
                if color == chess.WHITE
                else "black"
            ),
            "san": san,
            "uci": move.uci(),
            "fen_before": fen_before,
            "fen_after": self.board.fen(),
            "score_cp": (
                result.score
                if result
                else ""
            ),
            "depth": (
                result.depth
                if result
                else ""
            ),
            "elapsed_seconds": (
                round(result.elapsed, 4)
                if result
                else ""
            ),
            "search_status": (
                result.status
                if result
                else ""
            ),
            "total_nodes": metrics.get(
                "total_nodes",
                "",
            ),
            "quiescence_nodes": metrics.get(
                "quiescence_nodes",
                "",
            ),
            "neural_inferences": metrics.get(
                "neural_inferences",
                "",
            ),
        }

        self.records.append(record)

        if self.board.is_checkmate():
            self.status_var.set(
                "XEQUE-MATE! Partida encerrada."
            )

        elif self.board.is_check():
            if self.board.turn == self.our_color:
                self.status_var.set(
                    "XEQUE! Nosso rei ameacado."
                )
            else:
                self.status_var.set(
                    "XEQUE! Rei adversario ameacado."
                )

        elif player == "engine":
            self.status_var.set(
                f"Nosso motor jogou {san}. "
                "Reproduza no tabuleiro fisico."
            )

        else:
            self.status_var.set(
                f"Adversario jogou {san}. "
                "Calcule nossa resposta."
            )

        self.refresh()
        self.save_logs()

        if self.board.is_game_over(
            claim_draw=True
        ):
            self.root.after(
                50,
                self.notify_game_over,
            )

    def undo(self):
        if (
            not self.started
            or self.thinking
            or not self.board.move_stack
        ):
            return

        if not messagebox.askyesno(
            "Desfazer jogada",
            "Deseja desfazer a ultima jogada?",
        ):
            return

        self.board.pop()

        if self.records:
            self.records.pop()

        self.last_move = (
            self.board.peek()
            if self.board.move_stack
            else None
        )

        self.selected = None
        self.finished_notified = False

        self.analysis_var.set(
            "Ultima jogada desfeita."
        )

        self.status_var.set(
            "Jogada desfeita. "
            "Confira o tabuleiro fisico."
        )

        if self.engine:
            self.engine.clear_cache()

        self.refresh()
        self.save_logs()

    def refresh(self):
        self.draw_board()
        self.update_game_alert()

        if not self.started:
            self.turn_var.set(
                "Partida nao iniciada"
            )

        elif (
            result := self.game_result()
        ) is not None:
            self.turn_var.set(
                result[0]
            )

        else:
            color = (
                "Brancas"
                if self.board.turn == chess.WHITE
                else "Pretas"
            )

            player = (
                "Nosso motor"
                if self.board.turn == self.our_color
                else "Adversario"
            )

            suffix = (
                " — XEQUE!"
                if self.board.is_check()
                else ""
            )

            self.turn_var.set(
                f"Vez: {color} — {player}{suffix}"
            )

        self.history.configure(
            state=tk.NORMAL
        )

        self.history.delete(
            "1.0",
            tk.END,
        )

        for record in self.records:
            number = (
                record["ply"] + 1
            ) // 2

            prefix = (
                f"{number}."
                if record["color"] == "white"
                else f"{number}..."
            )

            player = (
                "Motor"
                if record["player"] == "engine"
                else "Adversario"
            )

            self.history.insert(
                tk.END,
                f"{prefix:<6} "
                f"{record['san']:<8} "
                f"{player}\n",
            )

        self.history.see(tk.END)

        self.history.configure(
            state=tk.DISABLED
        )

    def save_logs(self):
        if self.log_dir is None:
            return

        self.log_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        game = chess.pgn.Game()

        game.headers["Event"] = (
            "Chess Challenge III - Competicao"
        )

        game.headers["White"] = (
            "ChessEngine"
            if self.our_color == chess.WHITE
            else "Adversario"
        )

        game.headers["Black"] = (
            "ChessEngine"
            if self.our_color == chess.BLACK
            else "Adversario"
        )

        game.headers["Result"] = (
            self.board.result(claim_draw=True)
        )

        game.headers["OurEvaluator"] = (
            "HybridEvaluator"
        )
        game.headers["NeuralModel"] = (
            MODEL_PATH.name
        )
        game.headers["NeuralWeight"] = str(
            NEURAL_WEIGHT
        )
        game.headers["NeuralBudget"] = str(
            NEURAL_BUDGET
        )
        game.headers["OurDepth"] = str(
            self.depth
        )
        game.headers["OurTimePerMove"] = str(
            self.think_time
        )

        node = game

        for move in self.board.move_stack:
            node = node.add_variation(move)

        state = {
            "our_color": (
                "white"
                if self.our_color == chess.WHITE
                else "black"
            ),
            "depth": self.depth,
            "think_time": self.think_time,
            "neural_model": str(MODEL_PATH),
            "neural_weight": NEURAL_WEIGHT,
            "neural_budget": NEURAL_BUDGET,
            "use_full_time": True,
            "early_stop_enabled": True,
            "fen": self.board.fen(),
            "moves": [
                move.uci()
                for move in self.board.move_stack
            ],
            "records": self.records,
        }

        # Primeiro salvamos o estado em um arquivo
        # temporario e depois fazemos a substituicao.
        # Isso evita deixar um JSON parcialmente escrito.
        state_temp = (
            self.log_dir / "state.tmp"
        )

        with state_temp.open(
            "w",
            encoding="utf-8",
        ) as stream:
            json.dump(
                state,
                stream,
                indent=2,
                ensure_ascii=False,
            )
            stream.flush()

        state_temp.replace(
            self.log_dir / "state.json"
        )

        # O PGN tambem usa substituicao atomica.
        pgn_temp = (
            self.log_dir / "game.pgn.tmp"
        )

        with pgn_temp.open(
            "w",
            encoding="utf-8",
        ) as stream:
            print(
                game,
                file=stream,
            )

        pgn_temp.replace(
            self.log_dir / "game.pgn"
        )

        if self.records:
            csv_temp = (
                self.log_dir / "moves.csv.tmp"
            )

            with csv_temp.open(
                "w",
                newline="",
                encoding="utf-8",
            ) as stream:
                writer = csv.DictWriter(
                    stream,
                    fieldnames=list(
                        self.records[0].keys()
                    ),
                )

                writer.writeheader()
                writer.writerows(
                    self.records
                )

            csv_temp.replace(
                self.log_dir / "moves.csv"
            )

    def close(self):
        if self.started and not self.thinking:
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
