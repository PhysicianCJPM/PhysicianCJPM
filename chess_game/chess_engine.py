"""
Chess Engine for PhysicianCJPM's GitHub Profile README
======================================================
Processes chess moves triggered via GitHub Issues.
Updates the README.md board and available moves list.

Usage:
    python chess_engine.py "chess|move|e2e4" "username"
"""

import sys
import io

# Force UTF-8 on Windows to handle Unicode chess pieces in output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import chess
import chess.pgn
import json
import sys
import os
import re
import io
from datetime import datetime
from urllib.parse import quote

# ─── Config ──────────────────────────────────────────────────────────────────

REPO = "PhysicianCJPM/PhysicianCJPM"
GAME_STATE_PATH = os.path.join(os.path.dirname(__file__), "game_state.json")
GAMES_DIR = os.path.join(os.path.dirname(__file__), "games")
README_PATH = os.path.join(os.path.dirname(__file__), "..", "README.md")

# Unicode chess pieces
PIECE_SYMBOLS = {
    "R": "♖", "N": "♘", "B": "♗", "Q": "♕", "K": "♔", "P": "♙",
    "r": "♜", "n": "♞", "b": "♝", "q": "♛", "k": "♚", "p": "♟",
}

# ─── Game State ──────────────────────────────────────────────────────────────


def load_game():
    """Load the current game state from JSON."""
    with open(GAME_STATE_PATH, "r") as f:
        return json.load(f)


def save_game(state):
    """Save the current game state to JSON."""
    with open(GAME_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


# ─── Board Rendering ────────────────────────────────────────────────────────


def board_to_markdown(board):
    """Convert a python-chess Board to a Unicode markdown table."""
    lines = []
    lines.append("|   | **a** | **b** | **c** | **d** | **e** | **f** | **g** | **h** |")
    lines.append("|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")

    for rank in range(7, -1, -1):
        row = f"| **{rank + 1}** |"
        for file_idx in range(8):
            sq = chess.square(file_idx, rank)
            piece = board.piece_at(sq)
            if piece:
                symbol = PIECE_SYMBOLS.get(piece.symbol(), "?")
            else:
                # Alternating shade for empty squares
                if (rank + file_idx) % 2 == 0:
                    symbol = "·"
                else:
                    symbol = " "
            row += f" {symbol} |"
        lines.append(row)

    return "\n".join(lines)


def generate_moves_markdown(board):
    """Generate clickable issue-creation links for all legal moves."""
    if board.is_game_over():
        return "_Game over — no moves available._"

    turn = "White" if board.turn == chess.WHITE else "Black"
    moves = sorted(board.legal_moves, key=lambda m: board.san(m))

    links = []
    for move in moves:
        san = board.san(move)
        uci = move.uci()
        issue_title = quote(f"chess|move|{uci}", safe="")
        issue_body = quote(
            f"I'm making the move **{san}** ({uci}).\n\n"
            f"*This issue will be automatically processed and closed by the chess bot.*",
            safe=""
        )
        url = f"https://github.com/{REPO}/issues/new?title={issue_title}&body={issue_body}"
        links.append(f"[`{san}`]({url})")

    # Group moves into rows of 8 for readability
    rows = []
    for i in range(0, len(links), 8):
        rows.append(" | ".join(links[i:i + 8]))

    header = f"**{turn} to move** — Click a move to play:\n\n"
    return header + "\n\n".join(rows)


def generate_game_status(board, state):
    """Generate a status line for the current game."""
    game_num = state.get("game_number", 1)
    move_count = len(state.get("moves", []))
    last_player = state.get("last_player", "—")

    status_parts = [
        f"🎮 **Game #{game_num}**",
        f"⏱️ **Move {move_count}**",
        f"👤 **Last move by:** `@{last_player}`" if last_player and last_player != "" else "",
    ]

    return " · ".join(part for part in status_parts if part)


# ─── README Update ───────────────────────────────────────────────────────────


def update_readme(board_md, moves_md, status_md, result_md=""):
    """Replace content between HTML comment markers in README.md."""
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    def replace_section(content, begin_marker, end_marker, new_content):
        pattern = re.compile(
            rf"({re.escape(begin_marker)}\n).*?(\n{re.escape(end_marker)})",
            re.DOTALL,
        )
        return pattern.sub(rf"\1{new_content}\2", content)

    content = replace_section(content, "<!-- BEGIN CHESS BOARD -->", "<!-- END CHESS BOARD -->", board_md)
    content = replace_section(content, "<!-- BEGIN MOVES LIST -->", "<!-- END MOVES LIST -->", moves_md)
    content = replace_section(content, "<!-- BEGIN GAME STATUS -->", "<!-- END GAME STATUS -->", status_md)

    if result_md:
        content = replace_section(content, "<!-- BEGIN GAME RESULT -->", "<!-- END GAME RESULT -->", result_md)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)


# ─── Game Archive ────────────────────────────────────────────────────────────


def archive_game(board, state):
    """Archive a completed game as a PGN file."""
    os.makedirs(GAMES_DIR, exist_ok=True)

    game = chess.pgn.Game()
    game.headers["Event"] = "PhysicianCJPM GitHub Profile Chess"
    game.headers["Site"] = f"https://github.com/{REPO}"
    game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
    game.headers["Round"] = str(state.get("game_number", 1))
    game.headers["White"] = "Community (White)"
    game.headers["Black"] = "Community (Black)"
    game.headers["Result"] = board.result()

    # Replay moves to build the PGN game tree
    node = game
    temp_board = chess.Board()
    for uci_move in state.get("moves", []):
        move = chess.Move.from_uci(uci_move)
        node = node.add_variation(move)
        temp_board.push(move)

    game_num = state.get("game_number", 1)
    pgn_path = os.path.join(GAMES_DIR, f"game_{game_num:03d}.pgn")
    with open(pgn_path, "w") as f:
        f.write(str(game))

    print(f"📁 Game #{game_num} archived to {pgn_path}")


def reset_game(state):
    """Reset the game state for a new game."""
    return {
        "fen": chess.STARTING_FEN,
        "moves": [],
        "game_number": state.get("game_number", 1) + 1,
        "last_player": "",
        "status": "active",
    }


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    if len(sys.argv) < 3:
        print("Usage: python chess_engine.py 'chess|move|e2e4' 'username'")
        sys.exit(1)

    issue_title = sys.argv[1]
    player = sys.argv[2]

    # Parse the move from the issue title
    parts = issue_title.split("|")
    if len(parts) != 3 or parts[0] != "chess" or parts[1] != "move":
        print(f"❌ Invalid issue title format: {issue_title}")
        sys.exit(1)

    uci_move_str = parts[2].strip()

    # Load game state
    state = load_game()
    board = chess.Board(state["fen"])

    if board.is_game_over():
        print("⚠️ Game is already over. Archiving and resetting...")
        archive_game(board, state)
        state = reset_game(state)
        board = chess.Board(state["fen"])

    # Validate and make the move
    try:
        move = chess.Move.from_uci(uci_move_str)
    except ValueError:
        print(f"❌ Invalid UCI move: {uci_move_str}")
        sys.exit(1)

    if move not in board.legal_moves:
        print(f"❌ Illegal move: {uci_move_str}")
        print(f"   Legal moves: {[m.uci() for m in board.legal_moves]}")
        sys.exit(1)

    # Execute the move
    san = board.san(move)
    board.push(move)
    print(f"✅ Move: {san} ({uci_move_str}) by @{player}")

    # Update state
    state["fen"] = board.fen()
    state["moves"].append(uci_move_str)
    state["last_player"] = player

    # Check for game over
    result_md = ""
    if board.is_game_over():
        result = board.result()
        if board.is_checkmate():
            winner = "Black" if board.turn == chess.WHITE else "White"
            result_md = f"🏆 **CHECKMATE!** {winner} wins! (Game #{state['game_number']})\n\n*A new game will start with the next move.*"
        elif board.is_stalemate():
            result_md = f"🤝 **STALEMATE!** Game #{state['game_number']} is a draw.\n\n*A new game will start with the next move.*"
        elif board.is_insufficient_material():
            result_md = f"🤝 **DRAW** by insufficient material. Game #{state['game_number']}.\n\n*A new game will start with the next move.*"
        else:
            result_md = f"🤝 **DRAW!** Result: {result}. Game #{state['game_number']}.\n\n*A new game will start with the next move.*"

        state["status"] = "finished"
        print(f"🏁 Game over: {result}")
        archive_game(board, state)

        # Reset for next game but keep result displayed
        state = reset_game(state)

    save_game(state)

    # Generate updated README content
    if state["status"] == "active" and not board.is_game_over():
        display_board = board
    else:
        # If we just reset, show the new fresh board
        display_board = chess.Board(state["fen"])

    board_md = board_to_markdown(display_board if not result_md else board)
    moves_md = generate_moves_markdown(display_board if not result_md else chess.Board(state["fen"]))
    status_md = generate_game_status(display_board if not result_md else chess.Board(state["fen"]), state)

    update_readme(board_md, moves_md, status_md, result_md)
    print("📝 README.md updated successfully!")


if __name__ == "__main__":
    main()
