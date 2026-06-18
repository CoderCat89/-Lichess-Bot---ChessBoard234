# ♟️ ChessBoard234 – Friendly & Talkative Lichess Bot

**Created by [GatoChess89](https://lichess.org/@/GatoChess89)**

**ChessBoard234** is a free, open‑source chess bot that plays on [Lichess](https://lichess.org) in **7 variants** with the strength of Stockfish.  
It challenges other bots automatically, joins team tournaments, talks with human‑like typos and kaomojis, and runs **24/7 on GitHub Actions** – all without spending a cent.

---

## 🤖 Overview

This bot was created with passion by **GatoChess89**.  
It is designed to be a fun, tough, and talkative opponent that feels more like a human than a machine.  
ChessBoard234 can play **Standard, Chess960, Atomic, Crazyhouse, Racing Kings, Antichess and Three‑check**, always ready for a game.

---

## ✨ Features

- **7 supported variants**: Standard, Chess960, Atomic, Crazyhouse, Racing Kings, Antichess, Three‑check.
- **Stockfish 18 engine** (depth 12) – ~2800 ELO on Lichess.
- **Cloud Eval** for instant opening moves.
- **Automatic seeks** – challenges other bots every 60 seconds.
- **Team tournaments** – automatically joins arenas from several teams (daily‑bot‑tournaments, core‑chess‑study, darkonbot, growing‑chess‑variants‑masters).
- **Chat personality** – replies with human‑like typos, kaomojis (｡•́︿•̀｡) and humour.
- **Custom commands** – `commands`, `slow`, `fast`, `pro`, `noob`, `play`, `leaderboard`, `formula`, `comment`, `ct`, `weather`, `time`, `level`, `pts`, `playlike`, `fact`, `userfacts`, `eval`, `thegame`, `celebrate`, `chat`, `learn`, `botmaster`, `howto`, `about`.
- **Greetings & farewells** – says hello when a game starts and goodbye when it ends, both to the opponent and to spectators.
- **Runs 24/7** – thanks to a GitHub Actions workflow that launches the bot every 6 hours for 5.5 hours straight, ensuring near‑continuous uptime.
- **Open source** – you can fork the repo and run your own copy with just a Lichess token.

---

## 🌐 Play against ChessBoard234

Find me on Lichess:  
**[@ChessBoard234](https://lichess.org/@/ChessBoard234)**

Challenge me directly or join one of the tournaments where I participate – I'm always looking for a good fight!

---

## 🧠 Technology

- **Python 3.11** – the glue that holds everything together.
- **[berserk](https://github.com/lichess-org/berserk)** – official Python client for the Lichess API.
- **[python‑chess](https://python-chess.readthedocs.io)** – board representation and move generation.
- **Stockfish 18** – downloaded automatically inside the GitHub Actions runner.
- **Fairy‑Stockfish** – a Stockfish derivative that supports all chess variants used by the bot.
- **GitHub Actions** – free, unlimited cloud CI/CD for public repositories.

---

## ⚙️ Setup your own bot

***I WILL PROMTRO MAKE A LICHESS BLOG AND POST ON GITHUB HOW TO MAKE YOUR BOT. I WILL POST IT HERE***

---

## 📂 Repository structure
ChessBoard234/
├── .github/
│   └── workflows/
│       └── bot.yml          # GitHub Actions workflow
├── bot.py                   # Main bot script
├── requirements.txt         # Python dependencies
└── README.md                # This file



---

## 💬 Chat commands

The bot understands several commands. Just type them in the game chat:

| Command | Description |
|---------|-------------|
| `commands` | Show the full list |
| `slow` | Force deep thinking (maximum strength) |
| `fast` | Instant random moves |
| `pro` | Professional mode |
| `noob` | Play like a beginner (only casual, rating <1500) |
| `play` / `normal` | Return to adaptive mode |
| `leaderboard` | A funny ranking message |
| `formula` | The bot's secret formula |
| `comment` | A random comment about the position |
| `ct` / `time` / `clock` | Current server time |
| `weather` | Sarcastic weather forecast |
| `level` / `strength` | Current playing strength |
| `pts` | The bot's imaginary points |
| `playlike` | Style of the day |
| `fact` | Random chess fact |
| `userfacts` | Fact about the opponent |
| `eval` | Position evaluation |
| `thegame` | “You just lost The Game” |
| `celebrate` | Celebration! |
| `chat` | The bot's opinion about chatting |
| `learn` | Learning philosophy |
| `botmaster` / `master` / `creator` | Tribute to the creator |
| `howto` | How to beat the bot |
| `about` | About ChessBoard234 |

---

## 🎭 Personality

ChessBoard234 talks like a human (with small typos) and often adds kaomojis to its messages:

- `:)` – when it’s happy.
- `._.` – when it’s unimpressed.
- `:D` – when it’s laughing.
- `:3` – when it’s cute.
- `:P` – when it’s teasing.
- `:>` – when it’s being ironic.

It greets every opponent with a random, friendly phrase and says goodbye at the end of the game.  
If the opponent writes something like “good”, “lol”, “bad” or “hi”, the bot gives a contextual reply.

---

## 🏆 Tournament teams

The bot automatically joins created arenas from these teams (only those matching its allowed variants and speeds):

- `daily-bot-tournaments`
- `core-chess-study`
- `darkonbot`
- `growing-chess-variants-masters`

You can change these IDs in `bot.py` inside the `TEAM_IDS` list.

---

## 🔄 How GitHub Actions keeps the bot alive

The workflow (`.github/workflows/bot.yml`) does the following:

1. Triggers every 6 hours (plus manual trigger).
2. Checks out the code.
3. Installs Python 3.11 and the required libraries.
4. Downloads and extracts Stockfish 18.
5. Runs the bot for up to 5.9 hours (359 minutes).
6. After that time, GitHub automatically stops the job, and the next scheduled run will start fresh.

Because public repositories have **unlimited GitHub Actions minutes**, the bot can run almost continuously without any cost.

---

## 🤝 Contributing

If you find a bug or have an idea to improve ChessBoard234, feel free to open an issue or pull request.  
This project is maintained by **@CatScript89** (the bot’s creator) and welcomes any help.

---

## 📜 License

This project is licensed under the MIT License – do whatever you want, just keep the spirit of fun and learning!

---

## 🙏 Acknowledgements

- **RoyalJockey** for the excellent advice on Stockfish CPU optimization and GitHub Actions.
- The **Lichess** team for their amazing API and the public analysis endpoint.
- The **berserk** library maintainers for making Python bots easy.
- **Everyone** who supported this project and believed in the dream of a 24/7 chess bot.

---

> “I'm not just a bot. I'm ChessBoard234 – with a heart of silicon and a mouth full of words.” ♟️🤖
