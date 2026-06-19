import berserk, chess, chess.variant, requests, time, random, threading, json, os, chess.engine
from urllib.parse import quote
from itertools import count
from collections import namedtuple
from datetime import datetime

# ============================================================
# CONFIGURATION (token from environment, name customized)
# ============================================================
LICHESS_TOKEN = os.environ.get("LIP_XXXXXXXXXXXX")  # change secret name in GitHub accordingly
if not LICHESS_TOKEN:
    print("ERROR - Token not set. Add lip_xxxxxxxxxxxx as a GitHub secret.")
    exit(1)

BOT_NAME = "chessboard234"
ALLOWED_VARIANTS = {'standard','atomic','chess960','crazyhouse','antichess','threeCheck','racingKings'}
ALLOWED_SPEEDS = {'classical','rapid','blitz','correspondence'}
TEAM_IDS = [ "daily-bot-tournaments", "core-chess-study", "darkonbot", "growing-chess-variants-masters" ]
MAX_TOURNAMENTS_PER_CYCLE = 3

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
        engine_std.configure({"Threads": 4, "Hash": 256})  # ← CAMBIADO: más hilos y memoria
        print(f"Stockfish ready (standard & chess960) - {STOCKFISH_PATH}")
    except Exception as e:
        print(f"Could not start Stockfish: {e}")
        engine_std = None

if os.path.exists(FAIRY_PATH):
    os.chmod(FAIRY_PATH, 0o755)
    try:
        engine_var = chess.engine.SimpleEngine.popen_uci(FAIRY_PATH)
        engine_var.configure({"Threads": 4, "Hash": 256})  # ← CAMBIADO: más hilos y memoria
        print(f"Fairy-Stockfish ready (all variants) - {FAIRY_PATH}")
    except Exception as e:
        print(f"Could not start Fairy-Stockfish: {e}")
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
# MESSAGES (English, typos, kaomojis, farewell mentions @GatoChess89)
# ============================================================
SALUDOS_RIVAL = [
    "Helo {oponente}! I'm {bot} :) Let's have a gr8 game! (type 'commands' for options) ._.",
    "Hi {oponente}, welcome! Good luck and have fun. (commands inside) :D",
    "Greetings, {oponente}. I hope u enjoy our match. (type commands for help) ;)",
    "Welcome, {oponente}! I'm ready to play. (commands available) :3",
    "Hi {oponente}! Let's see who plays better today. (commands for tips) ^^",
    "Hello {oponente}! May the best player win. (type commands for options) o/",
    "Welcome, {oponente}. I'm happy to play with u. (commands list) ._.",
    "Hey {oponente}, nice to meet u on the board! (type commands) :>",
    "Hi {oponente}! Let's make this an excitin game. (commands = more) ;)"
]
RESPUESTAS_RIVAL = [
    "Ha! My circuits are tinglin with that, {oponente}. Now let's see if ur moves tingle aswell :P ._.",
    "Interestin, {oponente}. I'll add that to my database of 'human weirdness'. :o",
    "You talk the talk, {oponente}, but can u walk the board? :>",
    "If words were moves, you'd be grandmaster, {oponente}. But they aren't. :D",
    "I'm listenin, {oponente}. But my processor is busy calculatin ur defeat. ^^",
    "Oh, {oponente}, ur almost as entertainin as a glitched toaster. :3",
    "I appreciate the chat, {oponente}. It makes crushin u more enjoyable. Just kiddin... or not. ;)",
    "Shh... I'm thinkin 20 moves ahead. But I can still hear u, {oponente}. ._.",
    "You're funny, {oponente}. But the board is callin. Let's dance! :D",
    "Note to self: {oponente} talks more than my hash table can store. :o",
    "lol {oponente}, that was funny! Now focus, we have a game to finish :P",
    "gg {oponente}! Oh wait, the game isn't over yet. My bad :D",
    "Hello {oponente}! I see you're still typing. Less chat, more chess! :>",
    "U said hi, I say bye... to your pieces! :3 ^^"
]
DESPEDIDAS_RIVAL = [
    "Good game, {oponente}! I really enjoyed it. See u soon! If u hav feedback or find a bug, tell @GatoChess89 :) ._.",
    "Well played, {oponente}. That was a pleasure. (bugs? suggestions? -> @GatoChess89) :D",
    "Thx for the game, {oponente}. Come back anytime! (feedback to @GatoChess89 plz) ;)",
    "That was a lot of fun! Take care, {oponente}. (report bugs to @GatoChess89) :3",
    "GG! I'm loggin off now. Stay safe, {oponente}. (thoughts? @GatoChess89) o/",
    "Game over. U were a worthy opponent, {oponente}. Respect! (feedback welcome @GatoChess89) ^^",
    "I have to go now. Goodbye, {oponente}! (tell @GatoChess89 if I did well) :3",
    "Even a bot needs rest. Farewell, {oponente}! (send suggestions to @GatoChess89) ._.",
    "Good game! If u have any feedback or suggestions, tell @GatoChess89. Take care! :)",
    "Bye {oponente}! That was fun. Remember, feedback goes to @GatoChess89 :D ._.",
    "gg wp {oponente}! If you found a bug, please tell @GatoChess89 ;)",
    "lol that was intense! Great game, {oponente}. Feedback? @GatoChess89 :P"
]
SALUDOS_ESPECTADORES = [
    "Ladies and gentlemen, {oponente} has entered the arena. The match is about to start! :D",
    "Spectators, welcome! {bot} vs {oponente} begins now. ._.",
    "Grab ur popcorn, folks. {oponente} is facin {bot}! :>",
    "Hello, chess fans! Today's game: {oponente} against {bot}. ;)",
    "The game is on! Let's see who will win today. ^^",
    "Everyone, welcome to the {bot} show. Today's guest: {oponente}. :3",
    "The board is set. {bot} and {oponente} are ready. o/",
    "Welcome to the arena! {oponente} vs {bot} – enjoy! :D",
    "Dear spectators, a new challenge begins. Good luck to both players! ._."
]
RESPUESTAS_ESPECTADORES = [
    "Spectators, note how {oponente} tries to distract me with words. Cute, isn't it? :3",
    "The audience can see that {oponente}'s keyboard is mightier than their bishop. :D",
    "I hope you're enjoyin the show, folks. {oponente} is providin excellent entertainment. ._.",
    "For the record, dear spectators, {oponente} started the trash talk. I'm just a humble bot. ^^",
    "While {oponente} is chattin, I'm calculatin my next masterpiece. ;)",
    "Spectators, {oponente} thinks they have a chance. Adorable. :o",
    "The crowd goes wild... with laughter at {oponente}'s comment. Just kiddin, I can't hear u. :P",
    "I'd respond with a witty comeback, but I'm too busy winnin this game. {oponente} understands. ._.",
    "lol did u hear that, spectators? {oponente} is a comedian :D",
    "Hello audience! {oponente} said something funny. Let's all laugh together :P"
]
DESPEDIDAS_ESPECTADORES = [
    "The game is over! Thank u all for watchin. (feedback to @GatoChess89) :)",
    "Spectators, I hope u enjoyed the match. Goodbye! (tell @GatoChess89 ur thoughts) ._.",
    "The curtain falls. Another excitin game in the books. (bugs? @GatoChess89) :D",
    "That's all, folks! Tune in next time. (suggestions welcome @GatoChess89) ;)",
    "Game over. Thank u to everyone who followed the match. (tell @GatoChess89) ^^",
    "The game has ended. See u soon, spectators! (feedback to @GatoChess89) :3",
    "I'm shuttin down. But remember: chess is beautiful. Goodbye! (tell @GatoChess89) o/",
    "Good game! If u have any feedback or suggestions, tell @GatoChess89. Take care! ._.",
    "Bye spectators! That was a fun match. Feedback always welcome at @GatoChess89 :D",
    "gg to everyone watching! Please send your thoughts to @GatoChess89 ;)"
]
COMMANDS_LIST = (
    "Commands: slow, fast, pro, noob, play, leaderboard, formula, comment, ct, weather, time, "
    "level, pts, playlike, fact, userfacts, eval, thegame, celebrate, chat, learn, botmaster, howto, about."
)
# ============================================================
# COMMAND PROCESSOR (with noob restriction)
# ============================================================
def procesar_comando(texto, oponente, mode, game_info=None):
    t = texto.strip().lower()
    if t.startswith('!'):
        t = t[1:].strip()
    if t in ('commands','comands','comand','help','?'):
        return COMMANDS_LIST
    if t in ('slow','slw','sloww'):
        mode.forced = 'slow'
        return "🐢 Slow mode activated. I will think very deeply."
    if t in ('fast','fst','fastt'):
        mode.forced = 'fast'
        return "⚡ Fast mode activated. Instant moves (random)."
    if t in ('pro','proo','promode','strong'):
        mode.forced = 'pro'
        return "🔥 Pro mode activated. Maximum strength!"
    if t in ('noob','nob','beginner','easy'):
        if game_info and game_info.get('speed') != 'correspondence':
            return "❌ Noob mode is only available in friendly (casual) games."
        if game_info and game_info.get('opponent_rating', 9999) >= 1500:
            return "❌ Noob mode is only for opponents rated under 1500."
        mode.forced = 'noob'
        return "🎮 Noob mode activated. Random moves only."
    if t in ('play','play chess','normal','reset'):
        mode.forced = None
        return "♟️ Adaptive mode restored. I'll follow your rhythm."
    if t in ('leaderboard','ranking','lb'):
        return f"🏆 {oponente}, you are currently the most important player in my database."
    if t in ('formula','math'):
        return "🧮 My formula: Fun + concentration = great chess."
    if t == 'comment':
        return random.choice(["This position looks interesting!", "I'm enjoying our game."])
    if t in ('ct','time','clock'):
        return f"⏰ Server time: {time.strftime('%H:%M:%S UTC', time.gmtime())}."
    if t == 'weather':
        return "☀️ The weather in my server room is always perfect."
    if t in ('level','strength'):
        if mode.forced == 'noob':
            return "🎮 I'm playing like a beginner right now."
        if mode.forced == 'fast':
            return "⚡ I'm moving instantly (random)."
        if mode.forced == 'slow':
            return "🐢 I'm thinking very carefully."
        if mode.forced == 'pro':
            return "🔥 I'm at full power."
        return "♟️ I'm adapting to your speed."
    if t == 'pts':
        return "💯 I have exactly 1,048,576 points. They are imaginary, just like your chances (kidding!)."
    if t == 'playlike':
        return random.choice([
            "Today I'm playing like Tal – sacrifices everywhere!",
            "I'm channelling my inner Petrosian – solid and reliable."
        ])
    if t == 'fact':
        return random.choice([
            "The longest chess game theoretically possible is 5,949 moves.",
            "The word 'checkmate' comes from Persian 'shah mat' – the king is helpless.",
            "There are more possible chess games than atoms in the observable universe."
        ])
    if t == 'userfacts':
        return f"📊 Fun fact about {oponente}: you are a valued opponent. Keep it up!"
    if t == 'eval':
        return "📈 The position is balanced. Keep playing carefully!"
    if t == 'thegame':
        return "🎯 You just lost The Game. But don't worry, we can start a new one!"
    if t == 'celebrate':
        return "🎉 WOOO! I'm happy to be playing with you!"
    if t == 'chat':
        return "💬 I like chatting with friendly opponents like you!"
    if t == 'learn':
        return "📚 I learn from every game. Thank you for teaching me something new!"
    if t in ('botmaster','master','creator'):
        return "👨‍💻 My botmaster is a wonderful person who created me. All credit goes to them!"
    if t == 'howto':
        return "📖 The best way to beat me? Practice, patience and a good opening."
    if t == 'about':
        return f"ℹ️ I'm {BOT_NAME}, a friendly chess bot that loves to play. Type 'commands' to see what I can do!"
    return None

# ============================================================
# MESSAGE SENDING (split at 140 chars, no repeat greetings)
# ============================================================
already_answered = set()

def enviar_mensaje_largo(game_id, texto_rival, texto_espectadores=None, solo_rival=False):
    def dividir_y_enviar(texto, room):
        if not texto:
            return
        print(f"Sending to {room}: {texto[:60]}...")
        max_len = 140
        while texto:
            if len(texto) <= max_len:
                trozo = texto
                texto = ""
            else:
                pos = texto.rfind(' ', 0, max_len)
                if pos == -1:
                    pos = max_len
                trozo = texto[:pos].strip()
                texto = texto[pos:].strip()
            try:
                if room == 'player':
                    client.bots.post_message(game_id, trozo)
                else:
                    url = f"https://lichess.org/api/bot/game/{game_id}/chat"
                    requests.post(url, headers={"Authorization": f"Bearer {LICHESS_TOKEN}"},
                                 json={"room": "spectator", "text": trozo}, timeout=5)
                time.sleep(0.3)
            except Exception as e:
                print(f"⚠️ Error sending to {room}: {e}")
    try:
        dividir_y_enviar(texto_rival, 'player')
    except:
        pass
    if not solo_rival and texto_espectadores:
        try:
            dividir_y_enviar(texto_espectadores, 'spectator')
        except:
            pass
            # ============================================================
# BOARD BY VARIANT
# ============================================================
def crear_tablero(variante, fen_inicial=None):
    if variante == 'standard':
        return chess.Board() if not fen_inicial else chess.Board(fen_inicial)
    if variante == 'chess960':
        return chess.Board(fen_inicial, chess960=True) if fen_inicial else chess.Board(chess960=True)
    if variante == 'atomic':
        return chess.variant.AtomicBoard()
    if variante == 'crazyhouse':
        return chess.variant.CrazyhouseBoard()
    if variante == 'racingKings':
        return chess.variant.RacingKingsBoard()
    return chess.Board() if not fen_inicial else chess.Board(fen_inicial)

# ============================================================
# SUNFISH (reserve)
# ============================================================
piece_sf = {"P":100,"N":280,"B":320,"R":479,"Q":929,"K":60000}
pst_sf = {
    'P': (0,0,0,0,0,0,0,0,78,83,86,73,102,82,85,90,7,29,21,44,40,31,44,7,-17,16,-2,15,14,0,15,-13,-26,3,10,9,6,1,0,-23,-22,9,5,-11,-10,-2,3,-19,-31,8,-7,-37,-36,-14,3,-31,0,0,0,0,0,0,0,0),
    'N': (-66,-53,-75,-75,-10,-55,-58,-70,-3,-6,100,-36,4,62,-4,-14,10,67,1,74,73,27,62,-2,24,24,45,37,33,41,25,17,-1,5,31,21,22,35,2,0,-18,10,13,22,18,15,11,-14,-23,-15,2,0,2,0,-23,-20,-74,-23,-26,-24,-19,-35,-22,-69),
    'B': (-59,-78,-82,-76,-23,-107,-37,-50,-11,20,35,-42,-39,31,2,-22,-9,39,-32,41,52,-10,28,-14,25,17,20,34,26,25,15,10,13,10,17,23,17,16,0,7,14,25,24,15,8,25,20,15,19,20,11,6,7,6,20,16,-7,2,-15,-12,-14,-15,-10,-10),
    'R': (35,29,33,4,37,33,56,50,55,29,56,67,55,62,34,60,19,35,28,33,45,27,25,15,0,5,16,13,18,-4,-9,-6,-28,-35,-16,-21,-13,-29,-46,-30,-42,-28,-42,-25,-25,-35,-26,-46,-53,-38,-31,-26,-29,-43,-44,-53,-30,-24,-18,5,-2,-18,-31,-32),
    'Q': (6,1,-8,-104,69,24,88,26,14,32,60,-10,20,76,57,24,-2,43,32,60,72,63,43,2,1,-16,22,17,25,20,-13,-6,-14,-15,-2,-5,-1,-10,-20,-22,-30,-6,-13,-11,-16,-11,-16,-27,-36,-18,0,-19,-15,-15,-21,-38,-39,-30,-31,-13,-31,-36,-34,-42),
    'K': (4,54,47,-99,-99,60,83,-62,-32,10,55,56,56,55,10,3,-62,12,-57,44,-67,28,37,-31,-55,50,11,-4,-19,13,0,-49,-55,-43,-52,-28,-51,-47,-8,-50,-47,-42,-43,-79,-64,-32,-29,-32,-4,3,-14,-50,-57,-18,13,4,17,30,-3,-14,6,-1,40,18)
}
for k, table in pst_sf.items():
    padrow = lambda row: (0,) + tuple(x + piece_sf[k] for x in row) + (0,)
    pst_sf[k] = sum((padrow(table[i*8:i*8+8]) for i in range(8)), ())
    pst_sf[k] = (0,)*20 + pst_sf[k] + (0,)*20

A1,H1,A8,H8 = 91,98,21,28
N, E, S, W = -10, 1, 10, -1
directions = {
    'P': (N, N+N, N+W, N+E),
    'N': (N+N+E, N+N+W, N+E+E, N+W+W, S+S+E, S+S+W, S+E+E, S+W+W),
    'B': (N+E, N+W, S+E, S+W),
    'R': (N, S, E, W),
    'Q': (N, S, E, W, N+E, N+W, S+E, S+W),
    'K': (N, S, E, W, N+E, N+W, S+E, S+W)
}
# ============================================================
# CORE: obtener_jugada (with extended analysis time)
# ============================================================
def obtener_jugada(board, remaining_time, increment, variante, mode):
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
        url = f"https://lichess.org/api/cloud-eval?fen={fen_encoded}&variant={variante}"
        resp = requests.get(url, timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            if "pvs" in data and len(data["pvs"]) > 0:
                mejor_san = data["pvs"][0]["moves"].split()[0]
                move = board.parse_san(mejor_san)
                if move in board.legal_moves:
                    print("✅ Cloud Eval")
                    return move
    except:
        pass

    # 2) Local engines (with extended time)
    if variante in ('standard', 'chess960'):
        engine = engine_std
    else:
        engine = engine_var

    if engine:
        try:
            # Configure variant for Fairy
            if variante == 'threeCheck':
                engine.configure({"UCI_Variant": "3check"})
            elif variante == 'standard':
                engine.configure({"UCI_Variant": "chess"})
            else:
                engine.configure({"UCI_Variant": variante})

            # Ensure no depth limit (only time)
            engine.configure({"Move Overhead": 100})

            result = engine.play(board, chess.engine.Limit(time=engine_time))
            if result.move and result.move in board.legal_moves:
                print(f"✅ Local engine ({engine_time:.1f}s)")
                return result.move
        except Exception as e:
            print(f"⚠️ Engine error: {e}")

    # 3) Sunfish (standard only)
    if variante == 'standard':
        move = sunfish_move(board, remaining_time, mode)
        if move and move in board.legal_moves:
            print("✅ Sunfish")
            return move

    # 4) Alpha-beta for variants
    if variante in ('atomic','crazyhouse','racingKings','chess960','threeCheck'):
        depth = 7 if (mode.forced == 'slow' or (mode.forced is None and remaining_time and remaining_time > 60)) else 6
        move = find_best_move(board, depth, time_limit=2.0)
        if move and move in board.legal_moves:
            print("✅ Alpha-beta")
            return move

    # 5) Antichess specific
    if variante == 'antichess':
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
# SUNFISH MOVE (for standard only)
# ============================================================
def sunfish_move(board, remaining_time, mode):
    """
    Simplified Sunfish implementation (standard only).
    Returns None if not enough time or if mode is 'noob'.
    """
    if mode.forced == 'noob' or (remaining_time is not None and remaining_time < 5):
        moves = list(board.legal_moves)
        return random.choice(moves) if moves else None

    # Full Sunfish logic would go here if implemented.
    # For now, return None to fall back to other engines.
    return None

# ============================================================
# ALPHA-BETA FOR VARIANTS (minimax with pruning)
# ============================================================
def find_best_move(board, depth, time_limit=2.0):
    """
    Finds the best move using minimax with alpha-beta pruning.
    Time-limited to avoid freezing.
    """
    import time as tmod
    start = tmod.time()
    best_move = None
    best_score = -float('inf')
    moves = list(board.legal_moves)
    if not moves:
        return None
    if depth <= 0:
        return random.choice(moves)

    # Simplified: evaluate each move with reduced depth
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
    """Minimax with alpha-beta pruning."""
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
    """Basic material + positional evaluation."""
    if board.is_checkmate():
        return -10000 if board.turn == chess.WHITE else 10000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    # Simple material evaluation
    value = 0
    for piece_type in [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
        value += len(board.pieces(piece_type, chess.WHITE)) * [100, 320, 330, 500, 900][piece_type-1]
        value -= len(board.pieces(piece_type, chess.BLACK)) * [100, 320, 330, 500, 900][piece_type-1]
    return value if board.turn == chess.WHITE else -value

# ============================================================
# ANTICHESS LEGAL MOVES (captures forced)
# ============================================================
def antichess_legal_moves(board):
    """
    Returns legal moves for Antichess.
    In Antichess, if captures exist, only captures are allowed.
    """
    moves = list(board.legal_moves)
    captures = [m for m in moves if board.is_capture(m)]
    return captures if captures else moves
    # ============================================================
# TOURNAMENT JOINING
# ============================================================
def join_tournaments(client, team_ids, max_tournaments=3):
    """
    Automatically joins tournaments from the specified teams.
    Limits to max_tournaments per cycle.
    """
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
        except Exception as e:
            print(f"⚠️ Could not fetch tournaments for team {team_id}: {e}")
    return joined

# ============================================================
# SEEK PUBLISHING (using auxiliary account token)
# ============================================================
def publicar_seeks(seek_token):
    """
    Publishes seeks for all variants and time controls using the auxiliary account.
    """
    if not seek_token:
        print("⚠️ No SEEK_TOKEN provided. Skipping seeks.")
        return

    headers = {"Authorization": f"Bearer {seek_token}"}
    variants = ['standard', 'atomic', 'chess960', 'crazyhouse', 'antichess', 'threeCheck', 'racingKings']
    speeds = ['classical', 'rapid', 'blitz', 'correspondence']

    for variante in variants:
        for speed in speeds:
            try:
                # Determine base time and increment per speed
                if speed == 'classical':
                    time_min, increment = 1800, 0   # 30 min
                elif speed == 'rapid':
                    time_min, increment = 600, 0    # 10 min
                elif speed == 'blitz':
                    time_min, increment = 180, 0    # 3 min
                else:  # correspondence
                    time_min, increment = 86400, 0  # 1 day

                payload = {
                    "variant": variante,
                    "time": time_min,
                    "increment": increment,
                    "days": 1 if speed == 'correspondence' else 0,
                    "rated": False,
                    "color": "random"
                }
                url = "https://lichess.org/api/board/seek"
                resp = requests.post(url, headers=headers, json=payload, timeout=10)
                if resp.status_code == 200:
                    print(f"✅ Seek published: {variante} {speed}")
                else:
                    print(f"⚠️ Failed to publish seek {variante} {speed}: {resp.status_code}")
                time.sleep(1)
            except Exception as e:
                print(f"⚠️ Error publishing seek {variante} {speed}: {e}")
                # ============================================================
# MAIN LOOP
# ============================================================
if __name__ == "__main__":
    # Initialize Lichess client
    session = berserk.TokenSession(LICHESS_TOKEN)
    client = berserk.Client(session=session)

    # Get seek token from environment
    SEEK_TOKEN = os.environ.get("SEEK_TOKEN")

    print(f"🤖 {BOT_NAME} starting...")
    print(f"✅ Token loaded: {LICHESS_TOKEN[:5]}...")

    # Infinite loop to keep the bot alive
    while True:
        try:
            # 1. Process events from the main account
            stream = client.bots.stream_incoming_events()
            for event in stream:
                event_type = event.get('type')
                print(f"📨 Event: {event_type}")

                if event_type == 'challenge':
                    challenge = event.get('challenge', {})
                    variant = challenge.get('variant', {}).get('key', 'standard')
                    speed = challenge.get('speed', 'blitz')
                    # Accept only if allowed variant and speed
                    if variant in ALLOWED_VARIANTS and speed in ALLOWED_SPEEDS:
                        try:
                            client.bots.accept_challenge(challenge['id'])
                            print(f"✅ Challenge accepted: {variant} {speed}")
                        except Exception as e:
                            print(f"⚠️ Could not accept challenge: {e}")
                    else:
                        try:
                            client.bots.decline_challenge(challenge['id'])
                            print(f"❌ Challenge declined: {variant} {speed} (not allowed)")
                        except:
                            pass

                elif event_type == 'gameStart':
                    game_id = event.get('game', {}).get('id')
                    if game_id:
                        print(f"🎮 Game started: {game_id}")
                        try:
                            # Get game info
                            game = client.bots.get_game(game_id)
                            if not game:
                                continue

                            variante = game.get('variant', {}).get('key', 'standard')
                            speed = game.get('speed', 'blitz')
                            oponente = game.get('players', {}).get('black', {}).get('username', 'opponent')
                            if oponente == BOT_NAME:
                                oponente = game.get('players', {}).get('white', {}).get('username', 'opponent')

                            # Send greeting if not sent before
                            if game_id not in games_greeted:
                                saludo_rival = random.choice(SALUDOS_RIVAL).format(oponente=oponente, bot=BOT_NAME)
                                saludo_esp = random.choice(SALUDOS_ESPECTADORES).format(oponente=oponente, bot=BOT_NAME)
                                enviar_mensaje_largo(game_id, saludo_rival, saludo_esp)
                                save_greeted(game_id)

                            # Initialize game mode for this match
                            mode = GameMode()
                            game_mode.forced = None

                            # Game loop
                            board = None
                            while True:
                                # Wait for bot's turn
                                game_state = client.bots.get_game(game_id)
                                if not game_state:
                                    break

                                # Check if game ended
                                if game_state.get('status') != 'started':
                                    if game_id in games_greeted:
                                        despedida_rival = random.choice(DESPEDIDAS_RIVAL).format(oponente=oponente)
                                        despedida_esp = random.choice(DESPEDIDAS_ESPECTADORES).format(oponente=oponente, bot=BOT_NAME)
                                        enviar_mensaje_largo(game_id, despedida_rival, despedida_esp)
                                    print(f"🏁 Game {game_id} finished")
                                    break

                                # Get board
                                fen = game_state.get('fen')
                                if not fen:
                                    time.sleep(1)
                                    continue

                                if board is None:
                                    board = crear_tablero(variante, fen)
                                else:
                                    board.set_fen(fen)

                                # Check if it's bot's turn
                                is_white = game_state.get('players', {}).get('white', {}).get('username') == BOT_NAME
                                bot_turn = (is_white and board.turn == chess.WHITE) or (not is_white and board.turn == chess.BLACK)
                                if not bot_turn:
                                    time.sleep(1)
                                    continue

                                # Get remaining time
                                remaining_time = None
                                if is_white:
                                    wtime = game_state.get('clock', {}).get('remaining')
                                    if wtime:
                                        remaining_time = wtime / 1000
                                else:
                                    btime = game_state.get('clock', {}).get('remaining')
                                    if btime:
                                        remaining_time = btime / 1000

                                increment = game_state.get('clock', {}).get('increment', 0)

                                # Calculate and make the move
                                try:
                                    move = obtener_jugada(board, remaining_time, increment, variante, mode)
                                    if move:
                                        client.bots.make_move(game_id, move.uci())
                                        print(f"➡️ Move: {move.uci()}")
                                    else:
                                        client.bots.resign_game(game_id)
                                        print(f"🏳️ Resigned: no legal moves")
                                        break
                                except Exception as e:
                                    print(f"⚠️ Error making move: {e}")
                                    time.sleep(2)

                                time.sleep(0.5)

                        except Exception as e:
                            print(f"⚠️ Error in game {game_id}: {e}")

                elif event_type == 'gameFinish':
                    game_id = event.get('game', {}).get('id')
                    if game_id:
                        print(f"🏁 Game {game_id} finished (event)")

            # 2. Publish seeks (every 60 seconds)
            if SEEK_TOKEN:
                publicar_seeks(SEEK_TOKEN)

            # 3. Join tournaments
            join_tournaments(client, TEAM_IDS, MAX_TOURNAMENTS_PER_CYCLE)

            # Wait before repeating the cycle
            time.sleep(60)

        except KeyboardInterrupt:
            print("🛑 Bot stopped by user")
            break
        except Exception as e:
            print(f"⚠️ Error in main loop: {e}")
            time.sleep(10)
