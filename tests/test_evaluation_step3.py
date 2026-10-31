import chess

from chess_engine.evaluation.heuristic import HeuristicEvaluator


def bare_board() -> chess.Board:
    board = chess.Board(None)
    board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
    return board


def test_evaluation_is_color_mirror_symmetric():
    board = chess.Board()

    for move in ("e4", "e5", "Nf3", "Nf6", "Bc4", "Bc5"):
        board.push_san(move)

    evaluator = HeuristicEvaluator()

    assert evaluator.evaluate(board) == -evaluator.evaluate(board.mirror())


def test_opening_and_endgame_king_tables_prefer_different_squares():
    evaluator = HeuristicEvaluator()

    opening_home = evaluator._piece_square_score(
        chess.KING, chess.E1, chess.WHITE, phase=24
    )
    opening_center = evaluator._piece_square_score(
        chess.KING, chess.E4, chess.WHITE, phase=24
    )
    endgame_home = evaluator._piece_square_score(
        chess.KING, chess.E1, chess.WHITE, phase=0
    )
    endgame_center = evaluator._piece_square_score(
        chess.KING, chess.E4, chess.WHITE, phase=0
    )

    assert opening_home > opening_center
    assert endgame_center > endgame_home


def test_king_pawn_shield_improves_middle_game_safety():
    evaluator = HeuristicEvaluator()
    exposed = bare_board()
    exposed.set_piece_at(chess.G1, chess.Piece(chess.KING, chess.WHITE))

    sheltered = exposed.copy()
    for square in (chess.F2, chess.G2, chess.H2):
        sheltered.set_piece_at(square, chess.Piece(chess.PAWN, chess.WHITE))

    assert evaluator._king_safety(sheltered, chess.WHITE, phase=24) > (
        evaluator._king_safety(exposed, chess.WHITE, phase=24)
    )


def test_attacked_king_and_neighbor_squares_reduce_safety():
    evaluator = HeuristicEvaluator()
    safe = bare_board()
    safe.set_piece_at(chess.G1, chess.Piece(chess.KING, chess.WHITE))

    exposed = safe.copy()
    exposed.set_piece_at(chess.G7, chess.Piece(chess.ROOK, chess.BLACK))

    assert evaluator._king_safety(exposed, chess.WHITE, phase=24) < (
        evaluator._king_safety(safe, chess.WHITE, phase=24)
    )


def test_doubled_and_isolated_pawns_are_penalized():
    evaluator = HeuristicEvaluator()
    connected = bare_board()
    connected.set_piece_at(chess.D2, chess.Piece(chess.PAWN, chess.WHITE))
    connected.set_piece_at(chess.E2, chess.Piece(chess.PAWN, chess.WHITE))

    doubled = bare_board()
    doubled.set_piece_at(chess.D2, chess.Piece(chess.PAWN, chess.WHITE))
    doubled.set_piece_at(chess.D3, chess.Piece(chess.PAWN, chess.WHITE))

    assert evaluator._pawn_structure(connected, chess.WHITE) > (
        evaluator._pawn_structure(doubled, chess.WHITE)
    )


def test_passed_pawn_bonus_drops_when_enemy_pawn_blocks_its_path():
    evaluator = HeuristicEvaluator()
    passed = bare_board()
    passed.set_piece_at(chess.E6, chess.Piece(chess.PAWN, chess.WHITE))

    blocked = passed.copy()
    blocked.set_piece_at(chess.F7, chess.Piece(chess.PAWN, chess.BLACK))

    assert evaluator._pawn_structure(passed, chess.WHITE) > (
        evaluator._pawn_structure(blocked, chess.WHITE)
    )


def test_open_knight_has_more_mobility_than_corner_knight():
    evaluator = HeuristicEvaluator()
    open_position = bare_board()
    open_position.set_piece_at(
        chess.D4,
        chess.Piece(chess.KNIGHT, chess.WHITE),
    )

    corner_position = bare_board()
    corner_position.set_piece_at(
        chess.A1,
        chess.Piece(chess.KNIGHT, chess.WHITE),
    )

    assert evaluator._mobility(open_position, chess.WHITE) > (
        evaluator._mobility(corner_position, chess.WHITE)
    )


def test_phase_decreases_as_major_and_minor_pieces_are_removed():
    board = chess.Board()
    evaluator = HeuristicEvaluator()

    opening_phase = evaluator._game_phase(board)
    board.remove_piece_at(chess.B1)
    board.remove_piece_at(chess.G1)
    board.remove_piece_at(chess.C1)
    board.remove_piece_at(chess.F1)

    assert opening_phase == evaluator.MAX_PHASE
    assert evaluator._game_phase(board) < opening_phase
