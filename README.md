# ⚽ Football Betting Intelligence

A quantitative football (soccer) betting system that identifies positive expected value (EV) opportunities by combining statistical models with real-time market data from Kalshi and multiple bookmakers.

> **⚠️ Paper trading only.** This system tracks hypothetical bets for research purposes. No real money is wagered automatically.

---

## How It Works

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  football-data.org│    │   The Odds API   │    │   Kalshi API     │
│  (match results)  │    │ (bookmaker odds) │    │ (prediction mkts)│
└────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Data Ingestion Layer                        │
│  football_data.py · odds_api.py · kalshi_soccer.py · adapters  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Prediction Models                          │
│  Calibrated Poisson (per-team attack/defense strengths)        │
│  Historical calibration from ~875+ matches across top leagues  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Strategy & Signals                          │
│  EV calculation · Edge detection · Crowd vs. model sentiment   │
│  Min-edge thresholds · Multi-market analysis per match         │
└───────────┬─────────────────────────────────┬───────────────────┘
            │                                 │
            ▼                                 ▼
┌───────────────────────┐         ┌───────────────────────┐
│   Telegram Alerts     │         │   Paper Trade Ledger  │
│   Real-time signals   │         │   SQLite tracking     │
└───────────────────────┘         └───────────┬───────────┘
                                              │
                                              ▼
                                  ┌───────────────────────┐
                                  │    Web Dashboard      │
                                  │  React + Vite + TW    │
                                  │  FastAPI backend      │
                                  └───────────────────────┘
```

## Features

### Prediction Model
- **Calibrated Poisson model** with per-team attack and defense strength ratings
- Trained on 12+ months of historical results from football-data.org
- Covers scoreline probabilities, 1X2, over/under, BTTS, and first-half outcomes
- Team name fuzzy matching across data sources (football-data.org ↔ Kalshi ↔ Odds API)

### Market Coverage
- **Kalshi** — Match-level prediction markets (moneyline, spread, over/under, BTTS, first-half)
- **The Odds API** — Aggregated bookmaker odds across UK and EU regions
- **football-data.org** — Historical match results for model calibration

### Supported Competitions
| League | Code |
|---|---|
| Premier League (England) | EPL |
| Bundesliga (Germany) | BL1 |
| La Liga (Spain) | PD |
| Serie A (Italy) | SA |
| Ligue 1 (France) | FL1 |
| Eredivisie (Netherlands) | DED |
| Primeira Liga (Portugal) | PPL |
| Championship (England) | ELC |
| Serie A (Brazil) | BSA |
| UEFA Champions League | UCL |
| FIFA World Cup | WC |
| European Championships | EC |

### Signal Generation
- Compares model probabilities against market-implied probabilities
- Flags opportunities where model edge exceeds configurable threshold
- Per-match multi-market analysis (all bet types evaluated simultaneously)
- EV formula: `model_prob - market_implied_prob`

### Alerting & Tracking
- **Telegram bot** sends formatted alerts with match details, probabilities, and EV
- **Paper trade ledger** (SQLite) logs every signal with timestamps, odds, and outcomes
- **Trade settlement** script to mark pending trades as WIN/LOSE after matches complete

### Web Dashboard
- **React + TypeScript + Vite** frontend with Tailwind CSS
- **FastAPI** backend serving signals, trades, and performance data
- Pages: Active Signals, Performance & Accuracy, Trade Log, Model Insights, Documentation
- Dark-themed card-based UI
- Metrics: ROI, win rate, max drawdown, cumulative P&L, rolling accuracy

---

## Project Structure

```
football_intel/
├── api/                    # FastAPI backend
│   ├── main.py             # App entry point, all API routes
│   ├── models.py           # Pydantic response schemas
│   └── cache.py            # In-memory signal cache (15-min TTL)
├── common/                 # Shared utilities
│   ├── config.py           # YAML config loader
│   └── logging_utils.py    # Structured logging
├── config/
│   ├── config.yaml         # Your config (git-ignored)
│   ├── config.yaml.example # Template with placeholder keys
│   └── keys/               # API private keys (git-ignored)
├── dashboard/              # Legacy Streamlit dashboard
│   ├── app.py
│   └── style.css
├── delivery/
│   └── telegram_bot.py     # Telegram alert sender
├── ingestion/              # Data source clients
│   ├── adapters.py         # Unified match data adapter
│   ├── cache.py            # Response caching
│   ├── football_data.py    # football-data.org API client
│   ├── kalshi.py           # Kalshi base client (RSA auth)
│   ├── kalshi_soccer.py    # Soccer-specific Kalshi markets
│   ├── kalshi_futures.py   # Season futures markets
│   └── odds_api.py         # The Odds API client
├── models/                 # Prediction models
│   ├── calibrated_poisson.py  # Main model (per-team strengths)
│   ├── poisson.py          # Naive Poisson baseline
│   ├── historical_data.py  # Historical data fetcher + cache
│   ├── hybrid_model.py     # Ensemble/hybrid model
│   └── futures_model.py    # Season futures evaluation
├── scripts/                # CLI runners
│   ├── run_pipeline.py     # Full dual-track pipeline
│   ├── run_signals.py      # Signal generation only
│   ├── kalshi_recon.py     # Market reconnaissance
│   ├── settle_trades.py    # Trade settlement
│   └── demo_flow.py        # Demo walkthrough
├── strategy/               # Betting strategy logic
│   ├── ev.py               # Expected value calculations
│   ├── signal_generator.py # EV signal generator
│   └── sentiment.py        # Crowd vs. model analysis
├── tracking/
│   └── ledger.py           # SQLite paper trade ledger
├── web/                    # React frontend
│   ├── src/
│   │   ├── pages/          # Dashboard pages
│   │   ├── components/     # Reusable UI components
│   │   ├── api.ts          # API client
│   │   └── types.ts        # TypeScript types
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
├── Dockerfile              # Multi-stage build (frontend + API)
├── docker-compose.yml      # One-command deployment
├── requirements.txt        # Python dependencies
└── .gitignore
```

---

## Installation

### Prerequisites
- Python 3.11+
- Node.js 20+ (for the web dashboard)
- API keys for:
  - [football-data.org](https://www.football-data.org/) (free tier available)
  - [The Odds API](https://the-odds-api.com/) (free tier: 500 requests/month)
  - [Kalshi](https://kalshi.com/) (requires account + RSA key pair)
  - A [Telegram bot token](https://core.telegram.org/bots#creating-a-new-bot)

### 1. Clone the repo

```bash
git clone https://github.com/robinsanjeev/football-betting-intel.git
cd football-betting-intel
```

### 2. Set up Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure

```bash
cp config/config.yaml.example config/config.yaml
```

Edit `config/config.yaml` and fill in your API keys:

```yaml
football_data:
  api_key: YOUR_FOOTBALL_DATA_API_KEY

kalshi:
  key_id: YOUR_KALSHI_KEY_ID
  private_key_path: config/keys/kalshi.key

telegram:
  bot_token: YOUR_TELEGRAM_BOT_TOKEN
  chat_id: 'YOUR_TELEGRAM_CHAT_ID'

odds_api:
  api_key: YOUR_ODDS_API_KEY
```

For Kalshi, place your RSA private key at `config/keys/kalshi.key`.

### 4. Install the web dashboard

```bash
cd web
npm install
cd ..
```

### 5. Run

**Option A: Run the pipeline (generates signals + sends Telegram alerts)**
```bash
# From the parent directory of football_intel/
python3 -m football_intel.scripts.run_pipeline
```

**Option B: Start the API server + dashboard**
```bash
# Terminal 1: API
uvicorn football_intel.api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend dev server
cd web && npm run dev
```

Then open `http://localhost:5173` for the dashboard.

**Option C: Docker (production)**
```bash
docker compose up -d
```

Dashboard available at `http://localhost:8080`.

---

## Scripts

| Script | Description |
|---|---|
| `run_pipeline.py` | Full dual-track pipeline: match EV signals + futures analysis → Telegram alerts + ledger |
| `run_signals.py` | Signal generation only (no alerts, just stdout) |
| `kalshi_recon.py` | Reconnaissance: fetches all open Kalshi soccer events and classifies bet types |
| `settle_trades.py` | Settles pending paper trades against actual match results |
| `demo_flow.py` | Interactive demo walkthrough of the system |

Run any script with:
```bash
python3 -m football_intel.scripts.<script_name>
```

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Health check |
| `/api/signals` | GET | Active betting signals |
| `/api/trades` | GET | Paper trade history |
| `/api/performance` | GET | ROI, win rate, drawdown, P&L charts |
| `/api/accuracy` | GET | Model calibration and accuracy metrics |
| `/api/insights/{match}` | GET | Detailed model breakdown for a specific match |

---

## How the Model Works

### Calibrated Poisson

The core model estimates **per-team attack and defense strengths** from historical match results:

1. **Data collection**: Fetches last 12 months of results from football-data.org across all tracked leagues
2. **Strength estimation**: For each team, calculates attack strength (goals scored vs. league average) and defense strength (goals conceded vs. league average)
3. **Lambda prediction**: For a given matchup, computes expected goals (λ) for each team using: `λ_home = avg_goals × home_attack × away_defense × home_advantage`
4. **Probability grid**: Uses Poisson distribution to build a full scoreline probability matrix (0-0 through 6-6)
5. **Market mapping**: Derives probabilities for all market types (1X2, over/under, BTTS, spreads, first-half) from the scoreline grid

### EV Calculation

For each Kalshi market:
```
EV = model_probability - kalshi_implied_probability
```

A signal is emitted when `EV > min_edge` (default: 5%).

---

## License

Private project. Not licensed for redistribution.
