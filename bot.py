import berserk, chess, chess.variant, requests, time, random, threading, json, os, chess.engine
from urllib.parse import quote
from itertools import count
from collections import namedtuple
from datetime import datetime

# ============================================================
# CONFIGURACIÓN (EL TOKEN SE LEE DE UNA VARIABLE DE ENTORNO)
# ============================================================
LICHESS_TOKEN = os.environ.get("LICHESS_BOT_TOKEN")
if not LICHESS_TOKEN:
    print("ERROR - EROR: LICHESS_BOT_TOKEN no esta definida. Ponla como secreto en GitHub.")
    exit(1)

BOT_NAME = "chessboard234"
ALLOWED_VARIANTS = {'standard','atomic','chess960','crazyhouse','antichess','threeCheck','racingKings'}
ALLOWED_SPEEDS = {'classical','rapid','blitz','correspondence'}

TEAM_IDS = [
    "daily-bot-tournaments",
    "core-chess-study",
    "darkonbot",
    "growing-chess-variants-masters"
]
MAX_TOURNAMENTS_PER_CYCLE = 3

class GameMode:
    def __init__(self): self.forced = None
game_mode = threading.local()

# ============================================================
# DETECCIÓN DE STOCKFISH LOCAL (máxima fuerza)
# ============================================================
STOCKFISH_PATH = os.path.expanduser("~/bin/stockfish")
if not os.path.exists(STOCKFISH_PATH):
    STOCKFISH_PATH = os.path.join(os.path.dirname(__file__), "stockfish")

engine = None
if os.path.exists(STOCKFISH_PATH):
    os.chmod(STOCKFISH_PATH, 0o755)
    try:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        engine.configure({"Threads": 2, "Hash": 64})   # Máxima potencia para GitHub Actions
        print(f"🔥 Stockfish local activo - Stockfish local active (3500+ ELO) en {STOCKFISH_PATH}")
    except Exception as e:
        print(f"⚠️ No se pudo iniciar Stockfish - Could not start Stockfish: {e}")
        engine = None
else:
    print("😴 Stockfish local no encontrado - Stockfish local not found. Instálalo en ~/bin/stockfish.")
 # ============================================================
# ARCHIVO DE SALUDOS (no repetir tras reinicio)
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
# MENSAJES (INGLÉS, AMABLES, CON KAOMOJIS Y ERRORES HUMANOS)
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
    "Note to self: {oponente} talks more than my hash table can store. :o"
]
DESPEDIDAS_RIVAL = [
    "Good game, {oponente}! I really enjoyed it. See u soon! :)",
    "Well played, {oponente}. That was a pleasure. ._.",
    "Thx for the game, {oponente}. Come back anytime! ;)",
    "That was a lot of fun! Take care, {oponente}. :D",
    "GG! I'm loggin off now. Stay safe, {oponente}. o/",
    "Game over. U were a worthy opponent, {oponente}. Respect! ^^",
    "I have to go now. Goodbye, {oponente}! :3",
    "Even a bot needs rest. Farewell, {oponente}! ._.",
    "Good game! If u have any feedback or suggestions, tell @GatoChess89. Take care! :)"
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
    "I'd respond with a witty comeback, but I'm too busy winnin this game. {oponente} understands. ._."
]
DESPEDIDAS_ESPECTADORES = [
    "The game is over! Thank u all for watchin. :)",
    "Spectators, I hope u enjoyed the match. Goodbye! ._.",
    "The curtain falls. Another excitin game in the books. :D",
    "That's all, folks! Tune in next time. ;)",
    "Game over. Thank u to everyone who followed the match. ^^",
    "The game has ended. See u soon, spectators! :3",
    "I'm shuttin down. But remember: chess is beautiful. Goodbye! o/",
    "Good game! If u have any feedback or suggestions, tell @GatoChess89. Take care! ._."
]

COMMANDS_LIST = (
    "Commands: slow, fast, pro, noob, play, leaderboard, formula, comment, ct, weather, time, "
    "level, pts, playlike, fact, userfacts, eval, thegame, celebrate, chat, learn, botmaster, howto, about."
)

# ============================================================
# COMANDOS (con restricción noob)
# ============================================================
def procesar_comando(texto, oponente, mode, game_info=None):
    t = texto.strip().lower()
    if t.startswith('!'): t = t[1:].strip()
    if t in ('commands','comands','comand','help','?'): return COMMANDS_LIST
    if t in ('slow','slw','sloww'): mode.forced = 'slow'; return "🐢 Slow mode activated. I will think very deeply."
    if t in ('fast','fst','fastt'): mode.forced = 'fast'; return "⚡ Fast mode activated. Instant moves (random)."
    if t in ('pro','proo','promode','strong'): mode.forced = 'pro'; return "🏆 Pro mode activated. Maximum strength!"
    if t in ('noob','nob','beginner','easy'):
        if game_info and game_info.get('speed') != 'correspondence':
            return "🍼 Noob mode is only available in friendly (casual) games."
        if game_info and game_info.get('opponent_rating', 9999) >= 1500:
            return "🍼 Noob mode is only for opponents rated under 1500."
        mode.forced = 'noob'
        return "🍼 Noob mode activated. Random moves only."
    if t in ('play','play chess','normal','reset'): mode.forced = None; return "♟️ Adaptive mode restored. I'll follow your rhythm."
    if t in ('leaderboard','ranking','lb'): return f"🏅 {oponente}, you are currently the most important player in my database."
    if t in ('formula','math'): return "🧪 My formula: Fun + concentration = great chess."
    if t == 'comment': return random.choice(["This position looks interesting!","I'm enjoying our game."])
    if t in ('ct','time','clock'): return f"⏰ Server time: {time.strftime('%H:%M:%S UTC', time.gmtime())}."
    if t == 'weather': return "☀️ The weather in my server room is always perfect."
    if t in ('level','strength'):
        if mode.forced == 'noob': return "🍼 I'm playing like a beginner right now."
        if mode.forced == 'fast': return "⚡ I'm moving instantly (random)."
        if mode.forced == 'slow': return "🐢 I'm thinking very carefully."
        if mode.forced == 'pro': return "🏆 I'm at full power."
        return "🎛️ I'm adapting to your speed."
    if t == 'pts': return "💯 I have exactly 1,048,576 points. They are imaginary, just like your chances (kidding!)."
    if t == 'playlike': return random.choice(["Today I'm playing like Tal – sacrifices everywhere!","I'm channelling my inner Petrosian – solid and reliable."])
    if t == 'fact':
        return random.choice([
            "The longest chess game theoretically possible is 5,949 moves.",
            "The word 'checkmate' comes from Persian 'shah mat' – the king is helpless.",
            "There are more possible chess games than atoms in the observable universe."
        ])
    if t == 'userfacts': return f"📊 Fun fact about {oponente}: you are a valued opponent. Keep it up!"
    if t == 'eval': return "📈 The position is balanced. Keep playing carefully!"
    if t == 'thegame': return "🎲 You just lost The Game. But don't worry, we can start a new one!"
    if t == 'celebrate': return "🎉 WOOO! I'm happy to be playing with you!"
    if t == 'chat': return "💬 I like chatting with friendly opponents like you!"
    if t == 'learn': return "📚 I learn from every game. Thank you for teaching me something new!"
    if t in ('botmaster','master','creator'): return "👑 My botmaster is a wonderful person who created me. All credit goes to them!"
    if t == 'howto': return "🎓 The best way to beat me? Practice, patience and a good opening."
    if t == 'about': return f"ℹ️ I'm {BOT_NAME}, a friendly chess bot that loves to play. Type 'commands' to see what I can do!"
    return None

# ============================================================
# ENVÍO DE MENSAJES (consola bilingüe, sin límites)
# ============================================================
def enviar_mensaje_largo(game_id, texto_rival, texto_espectadores=None, solo_rival=False):
    def dividir_y_enviar(texto, room):
        if not texto:
            return
        print(f"📤 Enviando a {room} - Sending to {room}: {texto[:60]}...")
        max_len = 800
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
                    requests.post(url,
                                  headers={"Authorization": f"Bearer {LICHESS_TOKEN}"},
                                  json={"room": "spectator", "text": trozo}, timeout=5)
                time.sleep(0.3)
            except Exception as e:
                print(f"   ⚠️ Error {room} - Error {room}: {e}")
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
# TABLERO POR VARIANTE
# ============================================================
def crear_tablero(variante, fen_inicial=None):
    if variante == 'standard': return chess.Board() if not fen_inicial else chess.Board(fen_inicial)
    if variante == 'chess960': return chess.Board(fen_inicial, chess960=True) if fen_inicial else chess.Board(chess960=True)
    if variante == 'atomic': return chess.variant.AtomicBoard()
    if variante == 'crazyhouse': return chess.variant.CrazyhouseBoard()
    if variante == 'racingKings': return chess.variant.RacingKingsBoard()
    return chess.Board() if not fen_inicial else chess.Board(fen_inicial)

# ============================================================
# SUNFISH (reserva)
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
initial_sf = (
    "         \n"  "         \n"  " rnbqkbnr\n"  " pppppppp\n"
    " ........\n"  " ........\n"  " ........\n"  " ........\n"
    " PPPPPPPP\n"  " RNBQKBNR\n"  "         \n"  "         \n"
)
N,E,S,W = -10,1,10,-1
directions = {
    "P":(N,N+N,N+W,N+E), "N":(N+N+E,E+N+E,E+S+E,S+S+E,S+S+W,W+S+W,W+N+W,N+N+W),
    "B":(N+E,S+E,S+W,N+W), "R":(N,E,S,W), "Q":(N,E,S,W,N+E,S+E,S+W,N+W),
    "K":(N,E,S,W,N+E,S+E,S+W,N+W)
}
MATE_LOWER = piece_sf["K"] - 10*piece_sf["Q"]
MATE_UPPER = piece_sf["K"] + 10*piece_sf["Q"]
QS, QS_A, EVAL_ROUGHNESS = 40, 140, 15
Move_sf = namedtuple("Move_sf","i j prom")

class Position:
    def __init__(self, board=initial_sf, score=0, wc=(True,True), bc=(True,True), ep=0, kp=0):
        self.board=board; self.score=score; self.wc=wc; self.bc=bc; self.ep=ep; self.kp=kp
    def gen_moves(self):
        for i,p in enumerate(self.board):
            if not p.isupper(): continue
            for d in directions[p]:
                for j in count(i+d, d):
                    q = self.board[j]
                    if q.isspace() or q.isupper(): break
                    if p=="P":
                        if d in (N,N+N) and q!=".": break
                        if d==N+N and (i<A1+N or self.board[i+N]!="."): break
                        if d in (N+W,N+E) and q=="." and j not in (self.ep,self.kp,self.kp-1,self.kp+1): break
                        if A8<=j<=H8:
                            for prom in "NBRQ": yield Move_sf(i,j,prom)
                            break
                    yield Move_sf(i,j,"")
                    if p in "PNK" or q.islower(): break
                    if i==A1 and self.board[j+E]=="K" and self.wc[0]: yield Move_sf(j+E,j+W,"")
                    if i==H1 and self.board[j+W]=="K" and self.wc[1]: yield Move_sf(j+W,j+E,"")
    def rotate(self, nullmove=False):
        return Position(self.board[::-1].swapcase(), -self.score, self.bc, self.wc,
                        119-self.ep if self.ep and not nullmove else 0,
                        119-self.kp if self.kp and not nullmove else 0)
    def move(self, move):
        i,j,prom = move; p,q = self.board[i], self.board[j]
        put = lambda board,i,p: board[:i]+p+board[i+1:]
        board = self.board; wc,bc,ep,kp = self.wc,self.bc,0,0
        score = self.score + self.value(move)
        board = put(board, j, board[i]); board = put(board, i, ".")
        if i==A1: wc = (False, wc[1])
        if i==H1: wc = (wc[0], False)
        if j==A8: bc = (bc[0], False)
        if j==H8: bc = (False, bc[1])
        if p=="K":
            wc = (False, False)
            if abs(j-i)==2:
                kp = (i+j)//2
                board = put(board, A1 if j<i else H1, "."); board = put(board, kp, "R")
        if p=="P":
            if A8<=j<=H8: board = put(board, j, prom)
            if j-i==2*N: ep = i+N
            if j==self.ep: board = put(board, j+S, ".")
        return Position(board, score, wc, bc, ep, kp).rotate()
    def value(self, move):
        i,j,prom = move; p,q = self.board[i], self.board[j]
        score = pst_sf[p][j] - pst_sf[p][i]
        if q.islower(): score += pst_sf[q.upper()][119-j]
        if abs(j-self.kp)<2: score += pst_sf["K"][119-j]
        if p=="K" and abs(i-j)==2:
            score += pst_sf["R"][(i+j)//2] - pst_sf["R"][A1 if j<i else H1]
        if p=="P":
            if A8<=j<=H8: score += pst_sf[prom][j] - pst_sf["P"][j]
            if j==self.ep: score += pst_sf["P"][119-(j+S)]
        return score

Entry = namedtuple("Entry","lower upper")
class Searcher:
    def __init__(self):
        self.tp_score={}; self.tp_move={}; self.history=set(); self.nodes=0
    def bound(self, pos, gamma, depth, can_null=True):
        self.nodes+=1; depth=max(depth,0)
        if pos.score <= -MATE_LOWER: return -MATE_UPPER
        entry = self.tp_score.get((pos,depth,can_null), Entry(-MATE_UPPER,MATE_UPPER))
        if entry.lower >= gamma: return entry.lower
        if entry.upper < gamma: return entry.upper
        if can_null and depth>0 and pos in self.history: return 0
        def moves():
            if depth>2 and can_null and abs(pos.score)<500:
                yield None, -self.bound(pos.rotate(nullmove=True),1-gamma,depth-3)
            if depth==0: yield None, pos.score
            killer = self.tp_move.get(pos)
            if not killer and depth>2:
                self.bound(pos,gamma,depth-3,can_null=False)
                killer = self.tp_move.get(pos)
            val_lower = QS - depth*QS_A
            if killer and pos.value(killer)>=val_lower:
                yield killer, -self.bound(pos.move(killer),1-gamma,depth-1)
            for val,move in sorted(((pos.value(m),m) for m in pos.gen_moves()), reverse=True):
                if val<val_lower: break
                if depth<=1 and pos.score+val<gamma:
                    yield move, pos.score+val if val<MATE_LOWER else MATE_UPPER
                    break
                yield move, -self.bound(pos.move(move),1-gamma,depth-1)
        best = -MATE_UPPER
        for move,score in moves():
            best = max(best,score)
            if best>=gamma:
                if move is not None: self.tp_move[pos] = move
                break
        if depth>2 and best==-MATE_UPPER:
            flipped = pos.rotate(nullmove=True)
            in_check = self.bound(flipped,MATE_UPPER,0)==MATE_UPPER
            best = -MATE_LOWER if in_check else 0
        if best>=gamma: self.tp_score[pos,depth,can_null] = Entry(best,entry.upper)
        if best<gamma: self.tp_score[pos,depth,can_null] = Entry(entry.lower,best)
        return best
    def search(self, history, time_limit=2.5, max_nodes=100000):
        self.nodes=0; self.history=set(history); self.tp_score.clear()
        start=time.time(); best_move=None; gamma=0
        for depth in range(1,1000):
            lower,upper = -MATE_LOWER,MATE_LOWER
            while lower<upper-EVAL_ROUGHNESS:
                if time.time()-start > time_limit*0.85 or self.nodes>=max_nodes: break
                score = self.bound(history[-1],gamma,depth,can_null=False)
                if score>=gamma: lower=score
                if score<gamma: upper=score
                yield depth,gamma,score,self.tp_move.get(history[-1])
                gamma = (lower+upper+1)//2
            if time.time()-start > time_limit*0.75 or self.nodes>=max_nodes: break
        best_move = self.tp_move.get(history[-1])
        return best_move

def parse(c): fil,rank = ord(c[0])-ord("a"), int(c[1])-1; return A1+fil-10*rank
def render(i): rank,fil = divmod(i-A1,10); return chr(fil+ord("a"))+str(-rank+1)

def board_to_sunfish_history(board):
    pos = Position(initial_sf,0,(True,True),(True,True),0,0)
    history = [pos]
    for move in board.move_stack:
        is_white = (len(history)%2==1)
        i = parse(move.uci()[:2]); j = parse(move.uci()[2:4])
        prom = move.uci()[4:].upper() if len(move.uci())>4 else ""
        if not is_white: i,j = 119-i,119-j
        pos = pos.move(Move_sf(i,j,prom))
        history.append(pos)
    return history

def sunfish_move(board, remaining_time, mode):
    if mode.forced in ('noob','fast'): return None
    if mode.forced=='slow':
        time_limit=20.0; max_nodes=5_000_000
    elif mode.forced=='pro':
        time_limit=15.0; max_nodes=4_000_000
    else:
        if remaining_time and remaining_time>180:
            time_limit=18.0; max_nodes=4_500_000
        elif remaining_time and remaining_time>60:
            time_limit=10.0; max_nodes=2_500_000
        elif remaining_time and remaining_time>20:
            time_limit=5.0; max_nodes=1_500_000
        else:
            time_limit=2.0; max_nodes=500_000
    try:
        history = board_to_sunfish_history(board)
        searcher = Searcher()
        best_move = None
        for depth,gamma,score,move in searcher.search(history, time_limit, max_nodes):
            if move: best_move = move
        if best_move is None: return None
        i,j,prom = best_move.i, best_move.j, best_move.prom
        if board.turn==chess.BLACK: i,j = 119-i,119-j
        uci = render(i)+render(j)+prom.lower()
        return chess.Move.from_uci(uci)
    except:
        return None

# ============================================================
# ALFA-BETA (variantes)
# ============================================================
piece_values = {chess.PAWN:100,chess.KNIGHT:320,chess.BISHOP:330,chess.ROOK:500,chess.QUEEN:900,chess.KING:20000}
pst_tactic = {
    chess.PAWN: [0,0,0,0,0,0,0,0,50,50,50,50,50,50,50,50,10,10,20,30,30,20,10,10,5,5,10,25,25,10,5,5,0,0,0,20,20,0,0,0,5,-5,-10,0,0,-10,-5,5,5,10,10,-20,-20,10,10,5,0,0,0,0,0,0,0,0],
    chess.KNIGHT: [-50,-40,-30,-30,-30,-30,-40,-50,-40,-20,0,0,0,0,-20,-40,-30,0,10,15,15,10,0,-30,-30,5,15,20,20,15,5,-30,-30,0,15,20,20,15,0,-30,-30,5,10,15,15,10,5,-30,-40,-20,0,5,5,0,-20,-40,-50,-40,-30,-30,-30,-30,-40,-50],
    chess.BISHOP: [-20,-10,-10,-10,-10,-10,-10,-20,-10,0,0,0,0,0,0,-10,-10,0,5,10,10,5,0,-10,-10,5,5,10,10,5,5,-10,-10,0,10,10,10,10,0,-10,-10,10,10,10,10,10,10,-10,-10,5,0,0,0,0,5,-10,-20,-10,-10,-10,-10,-10,-10,-20],
    chess.ROOK: [0,0,0,0,0,0,0,0,5,10,10,10,10,10,10,5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,0,0,0,5,5,0,0,0],
    chess.QUEEN: [-20,-10,-10,-5,-5,-10,-10,-20,-10,0,0,0,0,0,0,-10,-10,0,5,5,5,5,0,-10,-5,0,5,5,5,5,0,-5,0,0,5,5,5,5,0,-5,-10,5,5,5,5,5,0,-10,-10,0,5,0,0,0,0,-10,-20,-10,-10,-5,-5,-10,-10,-20],
    chess.KING: [-30,-40,-40,-50,-50,-40,-40,-30,-30,-40,-40,-50,-50,-40,-40,-30,-30,-40,-40,-50,-50,-40,-40,-30,-30,-40,-40,-50,-50,-40,-40,-30,-20,-30,-30,-40,-40,-30,-30,-20,-10,-20,-20,-20,-20,-20,-20,-10,20,20,0,0,0,0,20,20,20,30,10,0,0,10,30,20]
}
def evaluate_board(board):
    if board.is_checkmate(): return -100000 if board.turn==chess.WHITE else 100000
    if board.is_stalemate() or board.is_insufficient_material(): return 0
    score=0
    usar_pst = isinstance(board, chess.Board) and not board.chess960
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece is None: continue
        value = piece_values[piece.piece_type]
        if usar_pst:
            if piece.color==chess.WHITE: idx = (7-chess.square_rank(sq))*8+chess.square_file(sq)
            else: idx = chess.square_rank(sq)*8+chess.square_file(sq)
            value += pst_tactic[piece.piece_type][idx]
        score += value if piece.color==chess.WHITE else -value
    return score
def quiescence(board,alpha,beta,maximizing):
    stand_pat = evaluate_board(board)
    if maximixing:
        if stand_pat>=beta: return beta
        alpha = max(alpha,stand_pat)
    else:
        if stand_pat<=alpha: return alpha
        beta = min(beta,stand_pat)
    for move in board.legal_moves:
        if not board.is_capture(move): continue
        board.push(move)
        eval = quiescence(board,alpha,beta,not maximixing)
        board.pop()
        if maximixing:
            alpha = max(alpha,eval)
            if alpha>=beta: return beta
        else:
            beta = min(beta,eval)
            if beta<=alpha: return alpha
    return alpha if maximixing else beta
def minimax(board,depth,alpha,beta,maximizing,start_time,time_limit):
    if time.time()-start_time > time_limit: return evaluate_board(board)
    if depth==0 or board.is_game_over(): return quiescence(board,alpha,beta,maximizing)
    if maximixing:
        max_eval=-99999
        for move in board.legal_moves:
            board.push(move)
            eval = minimax(board,depth-1,alpha,beta,False,start_time,time_limit)
            board.pop()
            max_eval = max(max_eval,eval)
            alpha = max(alpha,eval)
            if beta<=alpha: break
        return max_eval
    else:
        min_eval=99999
        for move in board.legal_moves:
            board.push(move)
            eval = minimax(board,depth-1,alpha,beta,True,start_time,time_limit)
            board.pop()
            min_eval = min(min_eval,eval)
            beta = min(beta,eval)
            if beta<=alpha: break
        return min_eval
def find_best_move(board,depth=3,time_limit=2.0):
    start = time.time()
    best_move=None; best_eval=-99999 if board.turn==chess.WHITE else 99999
    for move in board.legal_moves:
        if time.time()-start > time_limit*0.8: break
        board.push(move)
        eval = minimax(board,depth-1,-99999,99999,board.turn==chess.BLACK,start,time_limit)
        board.pop()
        if board.turn==chess.WHITE:
            if eval>best_eval: best_eval,best_move = eval,move
        else:
            if eval<best_eval: best_eval,best_move = eval,move
    return best_move

def antichess_legal_moves(board):
    pseudos = list(board.generate_pseudo_legal_moves())
    captures = [m for m in pseudos if board.is_capture(m)]
    return captures if captures else [m for m in pseudos if not board.is_castling(m)]
  # ============================================================
# OBTENER JUGADA (Cloud Eval + Stockfish local + Sunfish)
# ============================================================
def obtener_jugada(board, variante, remaining_time, mode):
    if mode.forced in ('noob','fast'):
        moves = antichess_legal_moves(board) if variante=='antichess' else list(board.legal_moves)
        if moves: return random.choice(moves)
        return None
    if remaining_time is not None and remaining_time<5:
        moves = antichess_legal_moves(board) if variante=='antichess' else list(board.legal_moves)
        if moves: return random.choice(moves)
        return None

    # 1) Cloud Eval (aperturas)
    try:
        fen = board.fen(); fen_encoded = quote(fen, safe='')
        url = f"https://lichess.org/api/cloud-eval?fen={fen_encoded}&variant={variante}"
        resp = requests.get(url, timeout=2)
        if resp.status_code==200:
            data = resp.json()
            if "pvs" in data and len(data["pvs"])>0:
                mejor_san = data["pvs"][0]["moves"].split()[0]
                move = board.parse_san(mejor_san)
                if move in board.legal_moves:
                    print("   ☁️ Cloud Eval - Cloud Eval")
                    return move
    except: pass

    # 2) Stockfish local (si está disponible) – 3 segundos de análisis
    if engine:
        try:
            result = engine.play(board, chess.engine.Limit(time=3.0))
            if result.move and result.move in board.legal_moves:
                print("   🔥 Stockfish local - Stockfish local")
                return result.move
        except Exception as e:
            print(f"   ⚠️ Fallo Stockfish local - Stockfish error: {e}")

    # 3) Sunfish (reserva para estándar)
    if variante == 'standard':
        move = sunfish_move(board, remaining_time, mode)
        if move and move in board.legal_moves:
            print("   🐟 Sunfish - Sunfish")
            return move

    # 4) Alfa-beta para variantes
    if variante in ('atomic','crazyhouse','racingKings','chess960','threeCheck'):
        depth = 7 if (mode.forced=='slow' or (mode.forced is None and remaining_time and remaining_time>60)) else 6
        move = find_best_move(board, depth, time_limit=2.0)
        if move and move in board.legal_moves: return move

    # 5) Antichess
    if variante == 'antichess':
        moves = antichess_legal_moves(board)
        if moves: return random.choice(moves)
        return None

    moves = antichess_legal_moves(board) if variante=='antichess' else list(board.legal_moves)
    if moves: return random.choice(moves)
    return None

# ============================================================
# MANEJO DE PARTIDA
# ============================================================
def jugar_partida(game_id):
    global games_greeted
    mi_color = None; oponente = "Rival"; board = None; variante = "standard"; initial_fen = None; ultimo_movimiento = None
    game_info = {}
    if not hasattr(game_mode, 'forced'): game_mode.forced = None
    try:
        for evento in client.bots.stream_game_state(game_id):
            if evento['type'] == 'gameFull':
                if evento['white'].get('id') == BOT_NAME:
                    mi_color = 'white'
                    oponente = evento['black'].get('name', evento['black'].get('id', 'Rival'))
                else:
                    mi_color = 'black'
                    oponente = evento['white'].get('name', evento['white'].get('id', 'Rival'))
                variante = evento['variant']['key']
                print(f"🎮 {oponente} - {variante} ({mi_color}) - Juego empezado")

                game_info = {
                    'speed': evento.get('speed', 'rapid'),
                    'opponent_rating': evento.get('black', {}).get('rating', 1500) if mi_color == 'white' else evento.get('white', {}).get('rating', 1500)
                }

                initial_fen = evento.get('initialFen')
                if initial_fen == 'startpos' or not initial_fen: initial_fen = None

                board = crear_tablero(variante, initial_fen)
                movimientos = evento['state']['moves'].split()
                for m in movimientos:
                    if m:
                        try: board.push(chess.Move.from_uci(m))
                        except: pass

                if game_id not in games_greeted:
                    saludo_rival = random.choice(SALUDOS_RIVAL).format(oponente=oponente, bot=BOT_NAME)
                    saludo_esp = random.choice(SALUDOS_ESPECTADORES).format(oponente=oponente, bot=BOT_NAME)
                    enviar_mensaje_largo(game_id, saludo_rival, saludo_esp)
                    games_greeted.add(game_id)
                    save_greeted(game_id)

                if not board.is_game_over():
                    turno_bot = (mi_color == 'white' and len(movimientos) % 2 == 0) or (mi_color == 'black' and len(movimientos) % 2 == 1)
                    if turno_bot:
                        remaining = _obtener_tiempo(evento['state'], mi_color)
                        move = obtener_jugada(board, variante, remaining, game_mode)
                        if move and move in board.legal_moves:
                            try:
                                client.bots.make_move(game_id, move.uci())
                                ultimo_movimiento = move.uci()
                                print(f"♟️ {move.uci()} - Jugado")
                            except Exception as e:
                                if 'Not your turn' not in str(e) and 'Bad Request' not in str(e):
                                    print(f"⚠️ Error al mover - Move error: {e}")

            elif evento['type'] == 'gameState':
                movimientos = evento['moves'].split()
                if not movimientos: continue
                if ultimo_movimiento and movimientos[-1] == ultimo_movimiento: continue
                board = crear_tablero(variante, initial_fen)
                for m in movimientos:
                    if m:
                        try: board.push(chess.Move.from_uci(m))
                        except: pass
                es_mi_turno = (mi_color == 'white' and len(movimientos) % 2 == 0) or (mi_color == 'black' and len(movimientos) % 2 == 1)
                if es_mi_turno and not board.is_game_over():
                    remaining = _obtener_tiempo(evento, mi_color)
                    move = obtener_jugada(board, variante, remaining, game_mode)
                    if move and move in board.legal_moves:
                        try:
                            client.bots.make_move(game_id, move.uci())
                            ultimo_movimiento = move.uci()
                            print(f"♟️ {move.uci()} - Jugado")
                        except Exception as e:
                            if 'Not your turn' not in str(e) and 'Bad Request' not in str(e):
                                print(f"⚠️ Error al mover - Move error: {e}")

            elif evento['type'] == 'chatLine':
                if evento['username'].lower() != BOT_NAME.lower():
                    texto = evento['text']
                    print(f"💬 [{evento['username']}] dice - says: {texto[:40]}")
                    resp_cmd = procesar_comando(texto, oponente, game_mode, game_info)
                    if resp_cmd:
                        enviar_mensaje_largo(game_id, resp_cmd, None, solo_rival=True)
                    else:
                        # Respuesta contextual rápida
                        if "good" in texto.lower():
                            respuesta_rival = f"Thx, {oponente}! I do my best. Now, watch this. :)"
                        elif "lol" in texto.lower():
                            respuesta_rival = f"Laugh all u want, {oponente}. The board is still my playground. ._."
                        elif "bad" in texto.lower():
                            respuesta_rival = f"Bad? I'm just gettin started, {oponente}. :P"
                        elif "hi" in texto.lower() or "hello" in texto.lower():
                            respuesta_rival = f"Hey there, {oponente}! Ready to lose? I mean, ready to play! ;)"
                        else:
                            respuesta_rival = random.choice(RESPUESTAS_RIVAL).format(oponente=oponente, bot=BOT_NAME)
                        respuesta_esp = random.choice(RESPUESTAS_ESPECTADORES).format(oponente=oponente, bot=BOT_NAME)
                        enviar_mensaje_largo(game_id, respuesta_rival, respuesta_esp)

            elif evento['type'] == 'gameEnd':
                despedida_rival = random.choice(DESPEDIDAS_RIVAL).format(oponente=oponente, bot=BOT_NAME)
                despedida_esp = random.choice(DESPEDIDAS_ESPECTADORES).format(oponente=oponente, bot=BOT_NAME)
                enviar_mensaje_largo(game_id, despedida_rival, despedida_esp)
                print("💬 Despedida enviada - Farewell sent")
                break

    except Exception as e:
        print(f"❌ Error en partida {game_id} - Game error: {e}")

def _obtener_tiempo(state, mi_color):
    key = 'wtime' if mi_color == 'white' else 'btime'
    raw = state.get(key)
    if raw is not None:
        try: return float(raw) / 1000.0
        except: pass
    return None
  # ============================================================
# TORNEOS (con los 4 equipos)
# ============================================================
def join_team_tournaments():
    joined_ids = set()
    while True:
        try:
            total_joined = 0
            for team_id in TEAM_IDS:
                if total_joined >= MAX_TOURNAMENTS_PER_CYCLE: break
                url = f"https://lichess.org/api/team/{team_id}/arena?status=created"
                resp = requests.get(url, timeout=15)
                resp.raise_for_status()
                tournaments = [json.loads(line) for line in resp.text.splitlines() if line.strip()]
                for t in tournaments:
                    if total_joined >= MAX_TOURNAMENTS_PER_CYCLE: break
                    tid = t["id"]
                    if tid in joined_ids: continue
                    variant_raw = t.get("variant", "standard")
                    if isinstance(variant_raw, dict): variant = variant_raw.get("key", "standard")
                    else: variant = str(variant_raw)
                    speed = t.get("speed", "")
                    if not speed: speed = t.get("perf", {}).get("key", "")
                    if variant not in ALLOWED_VARIANTS or speed not in ALLOWED_SPEEDS:
                        print(f"   ⏩ {tid} {variant}/{speed} - Torneo omitido")
                        continue
                    nombre = t.get("fullName", tid)
                    link = f"https://lichess.org/tournament/{tid}"
                    starts_at = t.get("startsAt", "")
                    minutes = t.get("minutes", 0)
                    try:
                        fecha = datetime.fromisoformat(starts_at.replace("Z", "+00:00")).strftime("%d/%m %H:%M UTC")
                    except:
                        fecha = str(starts_at)
                    print(f"🏆 {nombre} | {variant}/{speed} - Torneo encontrado")
                    print(f"   {link} | {fecha} | {minutes}min | {team_id}")
                    join_url = f"https://lichess.org/api/tournament/{tid}/join"
                    try:
                        join_resp = requests.post(join_url, headers={"Authorization": f"Bearer {LICHESS_TOKEN}"}, timeout=10)
                        if join_resp.status_code == 200:
                            print(f"   ✅ Unido - Joined")
                            joined_ids.add(tid)
                            total_joined += 1
                        else:
                            print(f"   ⚠️ {join_resp.status_code} {join_resp.text.strip()} - No unido")
                            if "too many tournaments" in join_resp.text: break
                    except requests.exceptions.SSLError:
                        print(f"   ⚠️ SSL - Error SSL")
                    except Exception as e:
                        print(f"   ⚠️ {e} - Error")
        except Exception as e:
            print(f"⚠️ Error torneos - Tournaments error: {e}")
        time.sleep(1800)

# ============================================================
# AUTO-SEEK (MEJORADO, sin errores JSON)
# ============================================================
def auto_seek():
    seek_pares = [(180, 0), (180, 2), (300, 0), (300, 3), (600, 0)]  # 3+0, 3+2, 5+0, 5+3, 10+0
    while True:
        try:
            resp = requests.get(
                "https://lichess.org/api/bot/online",
                headers={"Authorization": f"Bearer {LICHESS_TOKEN}"},
                timeout=10
            )
            if resp.status_code == 200:
                bots = []
                for line in resp.text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if isinstance(obj, dict) and "username" in obj:
                            bots.append(obj)
                    except (json.JSONDecodeError, AttributeError):
                        continue
                otros = [b for b in bots if b["username"].lower() != BOT_NAME.lower()]
                random.shuffle(otros)
                desafiado = False
                for rival in otros:
                    variant = random.choice(list(ALLOWED_VARIANTS))
                    base_time, increment = random.choice(seek_pares)
                    mode = random.choice(["rated", "casual"])
                    challenge_url = f"https://lichess.org/api/challenge/{rival['username']}"
                    challenge_data = {
                        "variant": variant,
                        "time": base_time,
                        "increment": increment,
                        "mode": mode
                    }
                    resp_challenge = requests.post(
                        challenge_url,
                        headers={"Authorization": f"Bearer {LICHESS_TOKEN}"},
                        data=challenge_data,
                        timeout=10
                    )
                    if resp_challenge.status_code == 200:
                        print(f"🔍 Desafiado {rival['username']} a {variant} {base_time}s+{increment}s ({mode}) - Challenged")
                        desafiado = True
                        break
                    else:
                        if resp_challenge.status_code != 400:
                            print(f"⚠️ No se pudo desafiar a {rival['username']} ({resp_challenge.status_code}) - Challenge failed")
                        time.sleep(0.5)
                if not desafiado:
                    print("🔍 Ningún bot disponible - No bots available")
            else:
                print(f"⚠️ Error al obtener bots online - Online bots error: {resp.status_code}")
        except Exception as e:
            print(f"⚠️ Error en auto_seek - Seek error: {e}")
        time.sleep(60)

# ============================================================
# CONEXIÓN PRINCIPAL
# ============================================================
session = berserk.TokenSession(LICHESS_TOKEN)
client = berserk.Client(session)

def decline_challenge_safe(challenge_id):
    try:
        client.bots.decline_challenge(challenge_id, reason="No me apetece jugar esta modalidad ahora")
    except:
        try: client.bots.decline_challenge(challenge_id)
        except: pass

threading.Thread(target=join_team_tournaments, daemon=True).start()
threading.Thread(target=auto_seek, daemon=True).start()

print("🤖 ChessBoard234 listo - ChessBoard234 ready (Stockfish local)")
while True:
    try:
        for evento in client.bots.stream_incoming_events():
            if evento['type'] == 'challenge':
                challenger = evento['challenge']['challenger']['name']
                if challenger.lower() == BOT_NAME.lower():
                    print(f"👤 Propio ignorado - Self challenge ignored")
                    continue
                variante = evento['challenge']['variant']['key']
                speed = evento['challenge']['speed']
                print(f"⚔️ {challenger} - {variante}/{speed} - Desafío recibido")
                if variante in ALLOWED_VARIANTS and speed in ALLOWED_SPEEDS:
                    try:
                        client.bots.accept_challenge(evento['challenge']['id'])
                        print("✅ Aceptado - Accepted")
                    except Exception as e:
                        print(f"⚠️ No aceptado - Not accepted: {e}")
                else:
                    decline_challenge_safe(evento['challenge']['id'])
                    print("❌ Rechazado - Declined")
            elif evento['type'] == 'gameStart':
                threading.Thread(target=jugar_partida, args=(evento['game']['id'],)).start()
    except Exception as e:
        print(f"🔄 Reconectando... - Reconnecting... ({type(e).__name__})")
        time.sleep(5)
