# Dota 2 AI Coach

A real-time AI coaching assistant for Dota 2 that reads live game data via Game State Integration (GSI), processes it through an event-driven rule engine, and displays actionable notifications and LLM-powered item recommendations on a web dashboard.

## Features

### Real-Time Game State Tracking
✅ Receives live game data from Dota 2 via GSI (hero stats, items, minimap, buildings, draft, etc.)
✅ State diffing engine detects meaningful changes between game ticks
✅ Web dashboard displays live hero HP/mana, KDA, gold, GPM/XPM, and match clock

### Smart Notifications
✅ **Economy thresholds** — alerts when gold crosses milestones (every 1000g)
✅ **Combat alerts** — warns when HP drops below 20% and you have unused active items
✅ **Gank detection** — tracks enemy hero positions on the minimap and alerts when enemies are closing in on your location, including TP/smoke ganks
✅ **Game timings** — heads-up notifications for rune spawns, neutral creeps, siege waves, day/night cycles, Roshan, Tormentor, neutral item tiers, and more

### AI Item Recommendations (Gemini)
✅ **Auto recommendations** — triggered when gold crosses thresholds, suggests 1-3 items to buy next
✅ **Full item build** — on-demand button to get a prioritized 5-item build covering early/mid/late game
✅ Considers your hero, role, current items, enemy lineup, lane matchup, and game time
✅ Runs in a background thread so it never blocks game state processing

### Lane Setup
✅ After the first minute of the game, a popup asks for your lane, position, ally, and lane enemies
✅ This context is fed into the LLM prompts for more accurate recommendations

### Server Logs Panel
✅ Live server-side logs visible on the dashboard
✅ Shows LLM API call status (requesting → received → parsed), errors, and system events

## Architecture

```
Dota 2 Client ──GSI POST──▸ GSI Server (:4000)
                                │
                          GameState object
                                │
                     ▼──────────────────────▼
                  StateDiffer            EventEngine
                  (computes delta)       (evaluates rules)
                                              │
                          ┌───────────────────┼───────────────────┐
                     EconomyRule      CombatRule         MapAwarenessRule
                     TimingsRule      ItemAdvisor (Gemini API)
                                              │
                                         EventBus
                                              │
                              Flask API (:5050) ──▸ Web Dashboard
```

## Setup

### Prerequisites

- Python 3.11+
- Dota 2 installed (Steam)
- A Google Gemini API key (for item recommendations)

### 1. Clone and install dependencies

```bash
git clone https://github.com/sahilhadke/dota2-ai-coach.git
cd dota2-ai-coach
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure your Gemini API key

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_api_key_here
```

Get a key from [Google AI Studio](https://aistudio.google.com/apikey).

> **Note:** The `.env` file is gitignored and will never be committed.

### 3. Install the Dota 2 GSI config

Copy `gamestate_integration_dota2gsi.cfg` into your Dota 2 game config directory:

- **Windows:** `C:\Program Files (x86)\Steam\steamapps\common\dota 2 beta\game\dota\cfg\gamestate_integration\`
- **macOS:** `~/Library/Application Support/Steam/steamapps/common/dota 2 beta/game/dota/cfg/gamestate_integration/`
- **Linux:** `~/.steam/steam/steamapps/common/dota 2 beta/game/dota/cfg/gamestate_integration/`

Create the `gamestate_integration` folder if it doesn't exist. Restart Dota 2 after copying.

### 4. Add Dota 2 launch options

In Steam, right-click **Dota 2** → **Properties** → **General** → **Launch Options** and add:

```
-gamestateintegration
```

This enables the Game State Integration API so Dota 2 sends live data to the coach.

### 5. Run

```bash
./run.sh
```

Or manually:

```bash
source venv/bin/activate
PYTHONPATH=src python -m dota2_coach.main
```

Open **http://127.0.0.1:5050/** in your browser, then start a Dota 2 match.

### Stopping / freeing ports

```bash
./kill_port.sh
```

## Project Structure

```
dota2-ai-coach/
├── src/dota2_coach/
│   ├── main.py                    # Entry point
│   ├── gsi/
│   │   ├── server.py              # GSI HTTP server (listens on :4000)
│   │   └── state.py               # Converts GameState to dict
│   ├── engine/
│   │   ├── __init__.py            # EventEngine orchestrator
│   │   ├── differ.py              # State diffing
│   │   ├── event.py               # Event dataclass + EventBus
│   │   ├── advisor.py             # Gemini LLM item recommendations
│   │   ├── server_log.py          # Server-side log buffer
│   │   └── rules/
│   │       ├── base.py            # Abstract BaseRule
│   │       ├── economy.py         # Gold threshold alerts
│   │       ├── combat.py          # Low HP + active item alerts
│   │       ├── map_awareness.py   # Gank detection via minimap tracking
│   │       └── timings.py         # Rune/creep/objective timing alerts
│   ├── api/
│   │   ├── app.py                 # Flask REST API
│   │   └── static/index.html      # Web dashboard
│   └── prompts/
│       ├── item_recommendation.md # Prompt for threshold-based recs
│       └── full_item_build.md     # Prompt for full 5-item build
├── gamestate_integration_dota2gsi.cfg
├── requirements.txt
├── run.sh
├── kill_port.sh
├── TIME_INFORMATION.md
└── .env                           # YOUR API KEY (gitignored)
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Web dashboard |
| GET | `/state` | Current game state |
| GET | `/events` | Recent event notifications |
| GET | `/recommendation` | Latest auto item recommendation |
| POST | `/full-recommendation` | Trigger full 5-item build |
| GET | `/full-recommendation` | Get latest full build result |
| GET | `/logs` | Server logs (supports `?since=<timestamp>`) |
| POST | `/player-context` | Set lane/position/ally/enemy info |
| GET | `/player-context` | Get current player context |

## Tech Stack

- **Python** — core application
- **Flask** — REST API and static file serving
- **dota2gsipy** — Dota 2 Game State Integration parser
- **Google Gemini** (`google-genai`) — LLM for item recommendations
- **Vanilla HTML/CSS/JS** — dashboard (no build tools needed)
