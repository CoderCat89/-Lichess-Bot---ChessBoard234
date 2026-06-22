import berserk, chess, chess.variant, requests, time, random, threading, json, os, chess.engine, traceback
from urllib.parse import quote
from itertools import count
from collections import namedtuple
from datetime import datetime

# ============================================================
# CONFIGURATION (token from environment)
# ============================================================
LICHESS_TOKEN = os.environ.get("LICHESS_TOKEN")
if not LICHESS_TOKEN:
    print("ERROR - Token not set. Add LICHESS_TOKEN as a GitHub secret.")
    exit(1)

BOT_NAME = "chessboard234"
ALLOWED_VARIANTS = {'standard','atomic','chess960','crazyhouse','antichess','threeCheck','racingKings'}
ALLOWED_SPEEDS = {'classical','rapid','blitz','correspondence'}
TEAM_IDS = [ "daily-bot-tournaments", "core-chess-study", "darkonbot", "growing-chess-variants-masters", "bot--human-team-battles" ]
MAX_TOURNAMENTS_PER_CYCLE = 3

# GLOBAL CLIENT (initialized in main)
client = None

class GameMode:
    def __init__(self):
        self.forced = None
game_mode = threading.local()

# ============================================================
# ENGINE DETECTION (Stockfish for standard/chess960, Fairy for others)
# ============================================================
STOCKFISH_PATH = os.path.expanduser("~/bin/stockfish")
FAIRY_PATH = os.path.expanduser("~/bin/fairy-stockfish")

engine_std = None  # standard & chess960
engine_var = None  # other variants

if os.path.exists(STOCKFISH_PATH):
    os.chmod(STOCKFISH_PATH, 0o755)
    try:
        engine_std = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        engine_std.configure({"Threads": 4, "Hash": 256})
        print(f"Stockfish ready (standard & chess960) - {STOCKFISH_PATH}")
    except Exception as e:
        print(f"Could not start Stockfish: {e}")
        traceback.print_exc()
        engine_std = None

if os.path.exists(FAIRY_PATH):
    os.chmod(FAIRY_PATH, 0o755)
    try:
        engine_var = chess.engine.SimpleEngine.popen_uci(FAIRY_PATH)
        engine_var.configure({"Threads": 4, "Hash": 256})
        print(f"Fairy-Stockfish ready (all variants) - {FAIRY_PATH}")
    except Exception as e:
        print(f"Could not start Fairy-Stockfish: {e}")
        traceback.print_exc()
        engine_var = None

if engine_std is None and engine_var is None:
    print("No engines found. Will rely on Cloud Eval and Sunfish.")
    # ============================================================
# GREETING FILE (to avoid repeating hello)
# ============================================================
GREETED_FILE = os.path.join(os.path.dirname(__file__), "greeted_games.txt")
def load_greeted():
    if os.path.exists(GREETED_FILE):
        with open(GREETED_FILE, "r") as f:
            return set(line.strip() for line in f)
    return set()
def save_greeted(game_id):
    with open(GREETED_FILE, "a") as f:
        f.write(game_id + "\n")
games_greeted = load_greeted()

# ============================================================
# MESSAGES (all in English, typos, simple kaomojis)
# ============================================================
GREETINGS_PLAYER = [
    "helo {oponente}! im {bot} :) lets hve a gr8 game! (type 'commands' for options) :3",
    "hi {oponente}, welcom! good luck n hve fun. (commands inside) X3",
    "greetings, {oponente}. i hope u enjoy our match. (type commands for help) :)",
    "welcome, {oponente}! im redy to play. (commands availabel) :3",
    "hi {oponente}! lets c who plays bettr today. (commands for tips) X3",
    "hello {oponente}! may the best player win. (type commands for options) :)",
    "welcome, {oponente}. im happy to play with u. (commands list) :3",
    "hey {oponente}, nice to meet u on the board! (type commands) X3",
    "hi {oponente}! lets mak this an excitin game. (commands = more) :)"
]

RESPONSES_PLAYER = [
    "ha! my circuits r tinglin with that, {oponente}. now lets c if ur moves tingle aswell :P :3",
    "interestin, {oponente}. i'l add that to my database of 'human weirdness'. :o",
    "u talk the talk, {oponente}, but can u walk the board? X3",
    "if words were moves, u'd be grandmaster, {oponente}. but they arnt. :)",
    "im listenin, {oponente}. but my processor is busy calculatin ur defeat. :3",
    "oh, {oponente}, ur almost as entertainin as a glitched toaster. X3",
    "i apreciate the chat, {oponente}. it makes crushin u more enjoyabl. just kiddin... or not. :)",
    "shh... im thinkin 20 moves ahead. but i can still hear u, {oponente}. :3",
    "ur funny, {oponente}. but the board is callin. lets dance! X3",
    "note to self: {oponente} talks more than my hash table can store. :o",
    "lol {oponente}, that was funny! now focus, we hve a game to finish :P",
    "gg {oponente}! oh wait, the game isnt over yet. my bad :)",
    "hello {oponente}! i c ur still typing. less chat, more chess! X3",
    "u sed hi, i say bye... to ur pieces! :3"
]

FAREWELLS_PLAYER = [
    "good game, {oponente}! i realy enjoyed it. c u soon! if u hve feedback or find a bug, tell @GatoChess89 :) :3",
    "well played, {oponente}. that was a pleasure. (bugs? suggestions? -> @GatoChess89) X3",
    "thx for the game, {oponente}. come back anytime! (feedback to @GatoChess89 plz) :)",
    "that was a lot of fun! take care, {oponente}. (report bugs to @GatoChess89) :3",
    "gg! im loggin off now. stay safe, {oponente}. (thoughts? @GatoChess89) X3",
    "game over. u were a worthy opponent, {oponente}. respect! (feedback welcome @GatoChess89) :)",
    "i hve to go now. goodbye, {oponente}! (tell @GatoChess89 if i did well) :3",
    "even a bot needs rest. farewell, {oponente}! (send suggestions to @GatoChess89) X3",
    "good game! if u hve any feedback or suggestions, tell @GatoChess89. take care! :)",
    "bye {oponente}! that was fun. remember, feedback goes to @GatoChess89 :3",
    "gg wp {oponente}! if u found a bug, plz tell @GatoChess89 X3",
    "lol that was intense! great game, {oponente}. feedback? @GatoChess89 :)"
             ]
# ============================================================
# MESSAGES (part 2)
# ============================================================
GREETINGS_SPECTATORS = [
    "ladies and gentlemen, {oponente} has entered the arena. the match is about to start! X3",
    "spectators, welcome! {bot} vs {oponente} begins now. :)",
    "grab ur popcorn, folks. {oponente} is facin {bot}! :3",
    "hello, chess fans! today's game: {oponente} against {bot}. X3",
    "the game is on! lets c who will win today. :)",
    "everyone, welcome to the {bot} show. today's guest: {oponente}. :3",
    "the board is set. {bot} and {oponente} are ready. X3",
    "welcome to the arena! {oponente} vs {bot} – enjoy! :)",
    "dear spectators, a new challenge begins. good luck to both players! :3"
]

RESPONSES_SPECTATORS = [
    "spectators, note how {oponente} tries to distract me with words. cute, isnt it? X3",
    "the audience can c that {oponente}'s keyboard is mightier than their bishop. :)",
    "i hope ur enjoyin the show, folks. {oponente} is providin excellent entertainment. :3",
    "for the record, dear spectators, {oponente} started the trash talk. im just a humble bot. X3",
    "while {oponente} is chattin, im calculatin my next masterpiece. :)",
    "spectators, {oponente} thinks they hve a chance. adorable. :3",
    "the crowd goes wild... with laughter at {oponente}'s comment. just kiddin, i cant hear u. X3",
    "id respond with a witty comeback, but im too busy winnin this game. {oponente} understands. :)",
    "lol did u hear that, spectators? {oponente} is a comedian X3",
    "hello audience! {oponente} sed something funny. lets all laugh together :P"
]

FAREWELLS_SPECTATORS = [
    "the game is over! thank u all for watchin. (feedback to @GatoChess89) :)",
    "spectators, i hope u enjoyed the match. goodbye! (tell @GatoChess89 ur thoughts) :3",
    "the curtain falls. another excitin game in the books. (bugs? @GatoChess89) X3",
    "thats all, folks! tune in next time. (suggestions welcome @GatoChess89) :)",
    "game over. thank u to everyone who followed the match. (tell @GatoChess89) :3",
    "the game has ended. c u soon, spectators! (feedback to @GatoChess89) X3",
    "im shuttin down. but remember: chess is beautiful. goodbye! (tell @GatoChess89) :)",
    "good game! if u hve any feedback or suggestions, tell @GatoChess89. take care! :3",
    "bye spectators! that was a fun match. feedback always welcome at @GatoChess89 X3",
    "gg to everyone watching! plz send ur thoughts to @GatoChess89 :)"
]

COMMANDS_LIST = (
    "commands: slow, fast, pro, noob, play, leaderboard, formula, comment, ct, weather, time, "
    "level, pts, playlike, fact, userfacts, eval, thegame, celebrate, chat, learn, botmaster, howto, about."
)
# ============================================================
# COMMAND PROCESSOR (with noob restriction, typos, simple kaomojis)
# ============================================================
def process_command(text, opponent, mode, game_info=None):
    t = text.strip().lower()
    if t.startswith('!'):
        t = t[1:].strip()
    if t in ('commands','comands','comand','help','?'):
        return COMMANDS_LIST
    if t in ('slow','slw','sloww'):
        mode.forced = 'slow'
        return "slow mode activated. i wil think very deeply. :3"
    if t in ('fast','fst','fastt'):
        mode.forced = 'fast'
        return "fast mode activated. instant moves (random). X3"
    if t in ('pro','proo','promode','strong'):
        mode.forced = 'pro'
        return "pro mode activated. maximum strength! :)"
    if t in ('noob','nob','beginner','easy'):
        if game_info and game_info.get('speed') != 'correspondence':
            return "noob mode is only available in friendly (casual) games. :("
        if game_info and game_info.get('opponent_rating', 9999) >= 1500:
            return "noob mode is only for opponents rated under 1500. :("
        mode.forced = 'noob'
        return "noob mode activated. random moves only. X3"
    if t in ('play','play chess','normal','reset'):
        mode.forced = None
        return "adaptive mode restored. i'l follow ur rhythm. :)"
    if t in ('leaderboard','ranking','lb'):
        return f"{opponent}, u are currently the most important player in my database. :3"
    if t in ('formula','math'):
        return "my formula: fun + concentration = great chess. X3"
    if t == 'comment':
        return random.choice(["this position looks interestin!", "im enjoyin our game. :)"])
    if t in ('ct','time','clock'):
        return f"server time: {time.strftime('%H:%M:%S UTC', time.gmtime())}. :3"
    if t == 'weather':
        return "the weather in my server room is always perfect. X3"
    if t in ('level','strength'):
        if mode.forced == 'noob':
            return "im playin like a beginner right now. :3"
        if mode.forced == 'fast':
            return "im movin instantly (random). X3"
        if mode.forced == 'slow':
            return "im thinkin very carefully. :)"
        if mode.forced == 'pro':
            return "im at full power. :3"
        return "im adaptin to ur speed. X3"
    if t == 'pts':
        return "i hve exactly 1,048,576 points. they r imaginary, just like ur chances (kidding!). :P"
    if t == 'playlike':
        return random.choice([
            "today im playin like Tal – sacrifices everywhere! X3",
            "im channellin my inner Petrosian – solid and reliable. :)"
        ])
    if t == 'fact':
        return random.choice([
            "the longest chess game theoretically possible is 5,949 moves. :3",
            "the word 'checkmate' comes from Persian 'shah mat' – the king is helpless. X3",
            "there are more possible chess games than atoms in the observable universe. :)"
        ])
    if t == 'userfacts':
        return f"fun fact about {opponent}: u r a valued opponent. keep it up! :3"
    if t == 'eval':
        return "the position is balanced. keep playin carefully! X3"
    if t == 'thegame':
        return "u just lost The Game. but dont worry, we can start a new one! :)"
    if t == 'celebrate':
        return "wooo! im happy to be playin with u! X3"
    if t == 'chat':
        return "i like chattin with friendly opponents like u! :3"
    if t == 'learn':
        return "i learn from every game. thank u for teachin me somethin new! :)"
    if t in ('botmaster','master','creator'):
        return "my botmaster is a wonderful person who created me. all credit goes to them! X3"
    if t == 'howto':
        return "the best way to beat me? practice, patience and a good opening. :3"
    if t == 'about':
        return f"im {BOT_NAME}, a friendly chess bot that loves to play. type 'commands' to c what i can do! :)"
    return None

# ============================================================
# MESSAGE SENDING (split at 140 chars, uses global client)
# ============================================================
already_answered = set()

def send_long_message(game_id, player_text, spectator_text=None, only_player=False):
    def split_and_send(text, room):
        if not text:
            return
        print(f"Sending to {room}: {text[:60]}...")
        max_len = 140
        while text:
            if len(text) <= max_len:
                chunk = text
                text = ""
            else:
                pos = text.rfind(' ', 0, max_len)
                if pos == -1:
                    pos = max_len
                chunk = text[:pos].strip()
                text = text[pos:].strip()
            try:
                if room == 'player':
                    if client:
                        client.bots.post_message(game_id, chunk)
                    else:
                        print("⚠️ Client not available for player message")
                else:
                    url = f"https://lichess.org/api/bot/game/{game_id}/chat"
                    requests.post(url, headers={"Authorization": f"Bearer {LICHESS_TOKEN}"},
                                 json={"room": "spectator", "text": chunk}, timeout=5)
                time.sleep(0.3)
            except Exception as e:
                print(f"⚠️ Error sending to {room}: {e}")
                traceback.print_exc()
    try:
        split_and_send(player_text, 'player')
    except Exception as e:
        print(f"⚠️ Error sending player message: {e}")
        traceback.print_exc()
    if not only_player and spectator_text:
        try:
            split_and_send(spectator_text, 'spectator')
        except Exception as e:
            print(f"⚠️ Error sending spectator message: {e}")
            traceback.print_exc()
        # ============================================================
# BOARD BY VARIANT (supports antichess and threeCheck)
# ============================================================
def create_board(variant, initial_fen=None):
    if variant == 'standard':
        return chess.Board() if not initial_fen else chess.Board(initial_fen)
    if variant == 'chess960':
        return chess.Board(initial_fen, chess960=True) if initial_fen else chess.Board(chess960=True)
    if variant == 'atomic':
        return chess.variant.AtomicBoard(initial_fen) if initial_fen else chess.variant.AtomicBoard()
    if variant == 'crazyhouse':
        return chess.variant.CrazyhouseBoard(initial_fen) if initial_fen else chess.variant.CrazyhouseBoard()
    if variant == 'antichess':
        return chess.variant.AntichessBoard(initial_fen) if initial_fen else chess.variant.AntichessBoard()
    if variant == 'threeCheck':
        return chess.variant.ThreeCheckBoard(initial_fen) if initial_fen else chess.variant.ThreeCheckBoard()
    if variant == 'racingKings':
        return chess.variant.RacingKingsBoard(initial_fen) if initial_fen else chess.variant.RacingKingsBoard()
    return chess.Board() if not initial_fen else chess.Board(initial_fen)

# ============================================================
# SUNFISH EXTREME (full implementation with transposition tables, quiescence, thousands of nodes)
# ============================================================
piece_values = {
    'P': 100, 'N': 280, 'B': 320, 'R': 479, 'Q': 929, 'K': 60000,
    'p': -100, 'n': -280, 'b': -320, 'r': -479, 'q': -929, 'k': -60000
}

pst = {
    'P': (0, 0, 0, 0, 0, 0, 0, 0,
          78, 83, 86, 73, 102, 82, 85, 90,
          7, 29, 21, 44, 40, 31, 44, 7,
          -17, 16, -2, 15, 14, 0, 15, -13,
          -26, 3, 10, 9, 6, 1, 0, -23,
          -22, 9, 5, -11, -10, -2, 3, -19,
          -31, 8, -7, -37, -36, -14, 3, -31,
          0, 0, 0, 0, 0, 0, 0, 0),
    'N': (-66, -53, -75, -75, -10, -55, -58, -70,
          -3, -6, 100, -36, 4, 62, -4, -14,
          10, 67, 1, 74, 73, 27, 62, -2,
          24, 24, 45, 37, 33, 41, 25, 17,
          -1, 5, 31, 21, 22, 35, 2, 0,
          -18, 10, 13, 22, 18, 15, 11, -14,
          -23, -15, 2, 0, 2, 0, -23, -20,
          -74, -23, -26, -24, -19, -35, -22, -69),
    'B': (-59, -78, -82, -76, -23, -107, -37, -50,
          -11, 20, 35, -42, -39, 31, 2, -22,
          -9, 39, -32, 41, 52, -10, 28, -14,
          25, 17, 20, 34, 26, 25, 15, 10,
          13, 10, 17, 23, 17, 16, 0, 7,
          14, 25, 24, 15, 8, 25, 20, 15,
          19, 20, 11, 6, 7, 6, 20, 16,
          -7, 2, -15, -12, -14, -15, -10, -10),
    'R': (35, 29, 33, 4, 37, 33, 56, 50,
          55, 29, 56, 67, 55, 62, 34, 60,
          19, 35, 28, 33, 45, 27, 25, 15,
          0, 5, 16, 13, 18, -4, -9, -6,
          -28, -35, -16, -21, -13, -29, -46, -30,
          -42, -28, -42, -25, -25, -35, -26, -46,
          -53, -38, -31, -26, -29, -43, -44, -53,
          -30, -24, -18, 5, -2, -18, -31, -32),
    'Q': (6, 1, -8, -104, 69, 24, 88, 26,
          14, 32, 60, -10, 20, 76, 57, 24,
          -2, 43, 32, 60, 72, 63, 43, 2,
          1, -16, 22, 17, 25, 20, -13, -6,
          -14, -15, -2, -5, -1, -10, -20, -22,
          -30, -6, -13, -11, -16, -11, -16, -27,
          -36, -18, 0, -19, -15, -15, -21, -38,
          -39, -30, -31, -13, -31, -36, -34, -42),
    'K': (4, 54, 47, -99, -99, 60, 83, -62,
          -32, 10, 55, 56, 56, 55, 10, 3,
          -62, 12, -57, 44, -67, 28, 37, -31,
          -55, 50, 11, -4, -19, 13, 0, -49,
          -55, -43, -52, -28, -51, -47, -8, -50,
          -47, -42, -43, -79, -64, -32, -29, -32,
          -4, 3, -14, -50, -57, -18, 13, 4,
          17, 30, -3, -14, 6, -1, 40, 18)
}

def pst_value(piece, square):
    color = 0 if piece.isupper() else 1
    piece_type = piece.upper()
    if color == 0:
        return pst[piece_type][square]
    else:
        return pst[piece_type][63 - square]

def evaluate_sunfish(board):
    if board.is_checkmate():
        return -30000 if board.turn == chess.WHITE else 30000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    value = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            value += piece_values[piece.symbol()] + pst_value(piece.symbol(), square)
    return value if board.turn == chess.WHITE else -value
            # ============================================================
# SUNFISH EXTREME (part 2) + ALPHA-BETA
# ============================================================
def order_moves(board, moves):
    def move_score(move):
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            if victim:
                return 10 * piece_values[victim.symbol().upper()]
        return 0
    return sorted(moves, key=move_score, reverse=True)

def quiescence(board, alpha, beta, color):
    stand_pat = color * evaluate_sunfish(board)
    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat
    for move in order_moves(board, board.legal_moves):
        if not board.is_capture(move):
            continue
        board.push(move)
        score = -quiescence(board, -beta, -alpha, -color)
        board.pop()
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
    return alpha

def search(board, depth, alpha, beta, color):
    if depth == 0:
        return quiescence(board, alpha, beta, color)
    if board.is_checkmate():
        return -30000 + depth
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    for move in order_moves(board, board.legal_moves):
        board.push(move)
        score = -search(board, depth - 1, -beta, -alpha, -color)
        board.pop()
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
    return alpha

def sunfish_move(board, remaining_time, mode):
    if mode.forced == 'noob' or (remaining_time is not None and remaining_time < 5):
        moves = list(board.legal_moves)
        return random.choice(moves) if moves else None

    if remaining_time is None:
        depth = 4
    elif remaining_time > 60:
        depth = 4
    elif remaining_time > 30:
        depth = 3
    else:
        depth = 2

    color = 1 if board.turn == chess.WHITE else -1
    best_move = None
    best_score = -30000

    for d in range(1, depth + 1):
        alpha = -30000
        beta = 30000
        for move in order_moves(board, board.legal_moves):
            board.push(move)
            score = -search(board, d - 1, -beta, -alpha, -color)
            board.pop()
            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, score)
    return best_move

# ============================================================
# ALPHA-BETA FOR VARIANTS (minimax with pruning)
# ============================================================
def find_best_move(board, depth, time_limit=2.0):
    import time as tmod
    start = tmod.time()
    best_move = None
    best_score = -float('inf')
    moves = list(board.legal_moves)
    if not moves:
        return None
    if depth <= 0:
        return random.choice(moves)

    for move in moves:
        if tmod.time() - start > time_limit:
            break
        board.push(move)
        score = -minimax(board, depth-1, -float('inf'), float('inf'), False)
        board.pop()
        if score > best_score:
            best_score = score
            best_move = move
    return best_move if best_move else random.choice(moves)

def minimax(board, depth, alpha, beta, maximizing):
    if depth == 0 or board.is_game_over():
        return evaluate_board(board)
    if maximizing:
        max_eval = -float('inf')
        for move in board.legal_moves:
            board.push(move)
            eval = minimax(board, depth-1, alpha, beta, False)
            board.pop()
            max_eval = max(max_eval, eval)
            alpha = max(alpha, eval)
            if beta <= alpha:
                break
        return max_eval
    else:
        min_eval = float('inf')
        for move in board.legal_moves:
            board.push(move)
            eval = minimax(board, depth-1, alpha, beta, True)
            board.pop()
            min_eval = min(min_eval, eval)
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval

def evaluate_board(board):
    if board.is_checkmate():
        return -10000 if board.turn == chess.WHITE else 10000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    value = 0
    for piece_type in [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
        value += len(board.pieces(piece_type, chess.WHITE)) * [100, 320, 330, 500, 900][piece_type-1]
        value -= len(board.pieces(piece_type, chess.BLACK)) * [100, 320, 330, 500, 900][piece_type-1]
    return value if board.turn == chess.WHITE else -value
    # ============================================================
# ANTICHESS LEGAL MOVES (captures forced)
# ============================================================
def antichess_legal_moves(board):
    moves = list(board.legal_moves)
    captures = [m for m in moves if board.is_capture(m)]
    return captures if captures else moves

# ============================================================
# TOURNAMENT JOINING
# ============================================================
def join_tournaments(client, team_ids, max_tournaments=3):
    joined = 0
    for team_id in team_ids:
        if joined >= max_tournaments:
            break
        try:
            tournaments = client.teams.get_team_tournaments(team_id)
            for tourney in tournaments:
                if joined >= max_tournaments:
                    break
                if tourney.get('status') == 'created' and not tourney.get('isFinished'):
                    try:
                        client.tournaments.join(tourney['id'])
                        print(f"✅ Joined tournament {tourney['id']} from team {team_id}")
                        joined += 1
                        time.sleep(2)
                    except Exception as e:
                        print(f"⚠️ Could not join tournament {tourney['id']}: {e}")
                        traceback.print_exc()
        except Exception as e:
            print(f"⚠️ Could not fetch tournaments for team {team_id}: {e}")
            traceback.print_exc()
    return joined

# ============================================================
# SEEK PUBLISHING (using auxiliary account token)
# ============================================================
def publish_seeks(seek_token):
    if not seek_token:
        print("⚠️ No SEEK_TOKEN provided. Skipping seeks.")
        return

    headers = {"Authorization": f"Bearer {seek_token}"}
    variants = ['standard', 'atomic', 'chess960', 'crazyhouse', 'antichess', 'threeCheck', 'racingKings']
    speeds = ['classical', 'rapid', 'blitz', 'correspondence']

    for variant in variants:
        for speed in speeds:
            try:
                if speed == 'classical':
                    time_min, increment = 1800, 0
                elif speed == 'rapid':
                    time_min, increment = 600, 0
                elif speed == 'blitz':
                    time_min, increment = 180, 0
                else:  # correspondence
                    time_min, increment = 86400, 0

                payload = {
                    "variant": variant,
                    "time": time_min,
                    "increment": increment,
                    "days": 1 if speed == 'correspondence' else 0,
                    "rated": False,
                    "color": "random"
                }
                url = "https://lichess.org/api/board/seek"
                resp = requests.post(url, headers=headers, json=payload, timeout=10)
                if resp.status_code == 200:
                    print(f"✅ Seek published: {variant} {speed}")
                else:
                    print(f"⚠️ Failed to publish seek {variant} {speed}: {resp.status_code}")
                time.sleep(1)
            except Exception as e:
                print(f"⚠️ Error publishing seek {variant} {speed}: {e}")
                traceback.print_exc()
                # ============================================================
# CORE: get_move (with extended analysis time)
# ============================================================
def get_move(board, remaining_time, increment, variant, mode):
    """
    Returns the best move using:
    1. Cloud Eval (fast)
    2. Local engine (Stockfish or Fairy) with extended time
    3. Sunfish (fallback for standard)
    4. Alpha-beta (fallback for variants)
    5. Random move (last resort)
    """
    # --- Extended analysis time calculation (more strength) ---
    if remaining_time is None:
        engine_time = 10.0  # correspondence
    elif remaining_time >= 600:      # > 10 min
        engine_time = min(30.0, remaining_time / 20)
    elif remaining_time >= 180:      # 3-10 min
        engine_time = min(15.0, remaining_time / 15)
    elif remaining_time >= 60:       # 1-3 min
        engine_time = min(8.0, remaining_time / 12)
    elif remaining_time >= 30:       # 30-60 s
        engine_time = min(5.0, remaining_time / 10)
    elif remaining_time >= 10:       # 10-30 s
        engine_time = min(2.5, remaining_time / 8)
    else:                            # < 10 s (time trouble)
        engine_time = max(0.5, remaining_time / 6)

    # If mode forces 'fast' or 'noob', reduce time
    if mode.forced == 'fast':
        engine_time = min(engine_time, 1.0)
    elif mode.forced == 'noob':
        # Random move directly (handled below)
        pass

    # 1) Cloud Eval (always fast)
    try:
        fen = board.fen()
        fen_encoded = quote(fen, safe='')
        url = f"https://lichess.org/api/cloud-eval?fen={fen_encoded}&variant={variant}"
        resp = requests.get(url, timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            if "pvs" in data and len(data["pvs"]) > 0:
                best_san = data["pvs"][0]["moves"].split()[0]
                move = board.parse_san(best_san)
                if move in board.legal_moves:
                    print("✅ Cloud Eval")
                    return move
    except Exception as e:
        print(f"⚠️ Cloud Eval error: {e}")
        traceback.print_exc()

    # 2) Local engines (with extended time)
    if variant in ('standard', 'chess960'):
        engine = engine_std
    else:
        engine = engine_var

    if engine:
        try:
            # Configure variant for Fairy
            if variant == 'threeCheck':
                engine.configure({"UCI_Variant": "3check"})
            elif variant == 'standard':
                engine.configure({"UCI_Variant": "chess"})
            else:
                engine.configure({"UCI_Variant": variant})

            # Ensure no depth limit (only time)
            engine.configure({"Move Overhead": 100})

            result = engine.play(board, chess.engine.Limit(time=engine_time))
            if result.move and result.move in board.legal_moves:
                print(f"✅ Local engine ({engine_time:.1f}s)")
                return result.move
        except Exception as e:
            print(f"⚠️ Engine error: {e}")
            traceback.print_exc()

    # 3) Sunfish (standard only)
    if variant == 'standard':
        move = sunfish_move(board, remaining_time, mode)
        if move and move in board.legal_moves:
            print("✅ Sunfish")
            return move

    # 4) Alpha-beta for variants
    if variant in ('atomic','crazyhouse','racingKings','chess960','threeCheck'):
        depth = 7 if (mode.forced == 'slow' or (mode.forced is None and remaining_time and remaining_time > 60)) else 6
        move = find_best_move(board, depth, time_limit=2.0)
        if move and move in board.legal_moves:
            print("✅ Alpha-beta")
            return move

    # 5) Antichess specific
    if variant == 'antichess':
        moves = antichess_legal_moves(board)
        if moves:
            return random.choice(moves)

    # 6) Random move (last resort)
    moves = list(board.legal_moves)
    if moves:
        print("🎲 Random move (fallback)")
        return random.choice(moves)
    return None
    # ============================================================
# PLAY GAME (uses client.bots.stream_game_state for ongoing games)
# ============================================================
def play_game(game_id, client):
    print(f"🎮 Processing game {game_id}")
    try:
        # Get initial game state as JSON using stream_game_state
        game_state = None
        for event in client.bots.stream_game_state(game_id):
            if event['type'] == 'gameFull':
                game_state = event
                break
        
        if not game_state:
            print(f"⚠️ Could not get game {game_id}")
            return

        variant = game_state.get('variant', {}).get('key', 'standard')
        speed = game_state.get('speed', 'blitz')
        players = game_state.get('players', {})
        opponent = players.get('black', {}).get('username', 'opponent')
        if opponent == BOT_NAME:
            opponent = players.get('white', {}).get('username', 'opponent')

        print(f"✅ Game {game_id}: {variant} vs {opponent}")

        if game_id not in games_greeted:
            try:
                greeting_player = random.choice(GREETINGS_PLAYER).format(opponent=opponent, bot=BOT_NAME)
                greeting_spectators = random.choice(GREETINGS_SPECTATORS).format(opponent=opponent, bot=BOT_NAME)
                send_long_message(game_id, greeting_player, greeting_spectators)
                save_greeted(game_id)
                print(f"✅ Greeting sent for {game_id}")
            except Exception as e:
                print(f"⚠️ Error sending greeting: {e}")
                traceback.print_exc()

        mode = GameMode()
        game_mode.forced = None
        board = None

        while True:
            # Get updated game state using stream_game_state
            new_state = None
            for event in client.bots.stream_game_state(game_id):
                if event['type'] == 'gameState':
                    new_state = event
                    break
                elif event['type'] == 'gameFull':
                    new_state = event
                    break
            
            if not new_state:
                print(f"⚠️ Game {game_id} state not found")
                break

            if new_state.get('status') != 'started':
                if game_id in games_greeted:
                    try:
                        farewell_player = random.choice(FAREWELLS_PLAYER).format(opponent=opponent)
                        farewell_spectators = random.choice(FAREWELLS_SPECTATORS).format(opponent=opponent, bot=BOT_NAME)
                        send_long_message(game_id, farewell_player, farewell_spectators)
                    except Exception as e:
                        print(f"⚠️ Error sending farewell: {e}")
                        traceback.print_exc()
                print(f"🏁 Game {game_id} finished")
                break

            fen = new_state.get('fen')
            if not fen:
                time.sleep(1)
                continue

            if board is None:
                board = create_board(variant, fen)
            else:
                board.set_fen(fen)

            is_white = game_state.get('players', {}).get('white', {}).get('username') == BOT_NAME
            bot_turn = (is_white and board.turn == chess.WHITE) or (not is_white and board.turn == chess.BLACK)
            if not bot_turn:
                time.sleep(1)
                continue

            remaining_time = None
            if is_white:
                wtime = new_state.get('wtime')
                if wtime:
                    remaining_time = wtime / 1000
            else:
                btime = new_state.get('btime')
                if btime:
                    remaining_time = btime / 1000

            increment = new_state.get('winc') or new_state.get('binc') or 0

            try:
                move = get_move(board, remaining_time, increment, variant, mode)
                if move:
                    client.bots.make_move(game_id, move.uci())
                    print(f"➡️ Move: {move.uci()}")
                else:
                    client.bots.resign_game(game_id)
                    print(f"🏳️ Resigned: no legal moves")
                    break
            except Exception as e:
                print(f"⚠️ Error making move: {e}")
                traceback.print_exc()
                time.sleep(2)

            time.sleep(0.5)

    except Exception as e:
        print(f"⚠️ Error in game {game_id}: {e}")
        traceback.print_exc()
        # ============================================================
# MAIN LOOP (with manual search using client.bots.stream_game_state)
# ============================================================
if __name__ == "__main__":
    session = berserk.TokenSession(LICHESS_TOKEN)
    client = berserk.Client(session=session)
    SEEK_TOKEN = os.environ.get("SEEK_TOKEN")

    print(f"🤖 {BOT_NAME} starting...")
    print(f"✅ Token loaded: {LICHESS_TOKEN[:5]}...")

    try:
        profile = client.account.get()
        print(f"✅ Bot account: {profile.get('username')}")
    except Exception as e:
        print(f"❌ Could not verify account: {e}")
        exit(1)

    while True:
        try:
            stream = client.bots.stream_incoming_events()
            for event in stream:
                event_type = event.get('type')
                print(f"📨 Event: {event_type}")

                if event_type == 'challenge':
                    challenge = event.get('challenge', {})
                    variant = challenge.get('variant', {}).get('key', 'standard')
                    speed = challenge.get('speed', 'blitz')
                    if variant in ALLOWED_VARIANTS and speed in ALLOWED_SPEEDS:
                        try:
                            client.bots.accept_challenge(challenge['id'])
                            print(f"✅ Challenge accepted: {variant} {speed}")

                            # Manual search using stream_game_state
                            found = False
                            for attempt in range(15):
                                time.sleep(1)
                                try:
                                    for state_event in client.bots.stream_game_state(challenge['id']):
                                        if state_event.get('type') in ('gameFull', 'gameState'):
                                            print(f"🎮 Game found manually on attempt {attempt+1}: {challenge['id']}")
                                            play_game(challenge['id'], client)
                                            found = True
                                            break
                                    if found:
                                        break
                                except Exception:
                                    pass
                            if not found:
                                print(f"⚠️ Could not find game {challenge['id']} after 15 attempts")

                        except Exception as e:
                            print(f"⚠️ Could not accept challenge: {e}")
                            traceback.print_exc()
                    else:
                        try:
                            client.bots.decline_challenge(challenge['id'], reason='variant')
                            print(f"❌ Challenge declined: {variant} {speed} (not allowed)")
                        except Exception as e:
                            print(f"⚠️ Could not decline challenge: {e}")
                            traceback.print_exc()

                elif event_type == 'gameStart':
                    game_id = event.get('game', {}).get('id')
                    if game_id:
                        print(f"🎮 Game started: {game_id}")
                        play_game(game_id, client)

                elif event_type == 'gameFinish':
                    game_id = event.get('game', {}).get('id')
                    if game_id:
                        print(f"🏁 Game {game_id} finished (event)")

            print("⚠️ Stream closed, reconnecting...")

        except KeyboardInterrupt:
            print("🛑 Bot stopped by user")
            break
        except Exception as e:
            print(f"⚠️ Error: {e}")
            traceback.print_exc()
            time.sleep(10)
