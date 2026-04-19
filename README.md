# ⚽ Football Betting Intelligence

AI-powered football betting signals using calibrated statistical models and real-time Kalshi market data.

> **⚠️ Paper trading only.** This system tracks hypothetical bets for research purposes. No real money is wagered automatically.

---

## How It Works

```
Historical Results (football-data.org)    Kalshi Live Markets    The Odds API
         │                                       │                    │
         ▼                                       ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Data Ingestion Layer                             │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Calibrated Poisson Model                             │
│  • Per-team attack/defense strengths (Dixon-Coles corrected)           │
│  • Recency-weighted (60-day half-life — recent form counts more)       │
│  • 875+ matches across EPL, Bundesliga, UCL                            │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Signal Generation                                  │
│  • Market-aware edge shrinkage (blends model with market by confidence)│
│  • Min 8% edge threshold · 15% min win probability                     │
│  • Edge cap at 25% · Confidence-based bet sizing                       │
│  • Probability-adjusted EV scoring                                     │
└───────────┬──────────────────────┬──────────────────────┬───────────────┘
            │                      │                      │
            ▼                      ▼                      ▼
    Telegram Alerts       Paper Trade Ledger       Web Dashboard
    (real-time)           (SQLite)                 (React + FastAPI)
                                                         │
                                                         ▼
                                               Adaptive Feedback Loop
                                               (auto-tunes thresholds
                                                from settled results)
```

## Features

### Model
- **Calibrated Poisson** with Dixon-Coles low-score correction
- **Recency-weighted** — 60-day half-life exponential decay (last week counts 5x more than 3 months ago)
- **Market-aware shrinkage** — blends model probability with market based on data confidence
- Per-team attack/defense strength ratings across home and away contexts
- Full scoreline probability matrix → 1X2, over/under, BTTS, spreads, first-half

### Signal Generation
- **8% minimum edge** threshold (filters noise)
- **15% minimum win probability** (eliminates longshot bets)
- **25% edge cap** (extreme divergences flagged as model uncertainty)
- Probability-adjusted EV and scoring (high-prob + high-edge > low-prob + high-edge)
- Confidence-based bet sizing hints (HIGH=full unit, MEDIUM=half, LOW=quarter)

### Adaptive Feedback Loop
- Automatically analyzes settled trade outcomes
- Tunes thresholds per bet type, edge range, probability bucket, and confidence level
- Raises min edge for losing bet types, lowers for profitable ones
- Can auto-disable underperforming bet types or confidence levels
- Persists learned parameters to JSON, survives restarts
- Starts in "warming up" mode until 20+ trades settle

### Market Coverage
- **Kalshi** — Moneyline, spread, over/under, BTTS, first-half
- **The Odds API** — Aggregated bookmaker odds (UK/EU)
- **football-data.org** — Historical results for calibration

### Supported Leagues
| League | Code |
|---|---|
| Premier League | EPL |
| Bundesliga | BL1 |
| UEFA Champions League | UCL |

### Dashboard (7 tabs)
| Tab | Description |
|---|---|
| **Active Signals** | Current betting opportunities with bet type badges, win likelihood, reasoning |
| **Performance** | Settled-only KPIs — win rate, ROI, cumulative PnL, max drawdown |
| **Trade Log** | Full signal history with sortable columns |
| **Model Insights** | Per-match deep dive — xG, team strengths, scoreline heatmap, goal distribution |
| **Tuning** | Adaptive feedback loop — performance by type/edge/prob, current params, manual retune |
| **Docs** | Full setup guide, API key instructions, NAS deployment tips |

---

## Quick Start

### Docker (recommended)

```bash
git clone https://github.com/robinsanjeev/football-betting-intel.git
cd football-betting-intel
cp config/config.yaml.example config/config.yaml
# Edit config.yaml with your API keys
docker compose up -d
```

Open `http://localhost:8080`

### Manual

```bash
# Prerequisites: Python 3.11+, Node 20+

# Backend
pip install -r requirements.txt

# Frontend
cd web && npm install && npm run build && cd ..

# Configure
cp config/config.yaml.example config/config.yaml
# Edit config.yaml with your API keys

# Run
uvicorn football_intel.api.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`

---

## API Keys Required

| Service | Purpose | Cost | Link |
|---|---|---|---|
| football-data.org | Historical match results | Free (10 req/min) | [Sign up](https://www.football-data.org/) |
| Kalshi | Live prediction market prices | Free account | [Sign up](https://kalshi.com/) |
| The Odds API | Bookmaker odds (optional) | Free (500 req/month) | [Sign up](https://the-odds-api.com/) |
| Telegram Bot | Signal alerts (optional) | Free | [BotFather](https://core.telegram.org/bots#creating-a-new-bot) |

---

## Project Structure

```
football_intel/
├── api/                       # FastAPI backend
│   ├── main.py                # All API routes + static file serving
│   ├── models.py              # Pydantic response schemas
│   └── cache.py               # Signal cache (15-min TTL)
├── models/                    # Prediction models
│   ├── calibrated_poisson.py  # Main model (Dixon-Coles + recency)
│   ├── historical_data.py     # Historical data fetcher + cache
│   └── poisson.py             # Naive Poisson baseline
├── strategy/                  # Betting logic
│   ├── signal_generator.py    # Edge detection + market shrinkage
│   ├── adaptive.py            # Feedback loop + auto-tuning
│   └── ev.py                  # Expected value calculations
├── ingestion/                 # Data source clients
│   ├── kalshi_soccer.py       # Kalshi soccer markets
│   ├── football_data.py       # football-data.org client
│   └── odds_api.py            # The Odds API client
├── scripts/                   # CLI tools
│   ├── run_pipeline.py        # Full pipeline → signals + alerts
│   ├── settle_trades.py       # Settle pending trades + trigger adaptive loop
│   └── run_signals.py         # Signal generation only
├── web/                       # React + Vite + Tailwind frontend
│   └── src/pages/             # Dashboard tabs
├── config/                    # YAML config (git-ignored)
├── Dockerfile                 # Multi-stage build
├── docker-compose.yml         # One-command deployment
└── requirements.txt           # Python dependencies
```

---

## Scripts

```bash
# Run full pipeline (signals + Telegram alerts + paper trades)
python3 -m football_intel.scripts.run_pipeline

# Generate signals only (stdout)
python3 -m football_intel.scripts.run_signals

# Settle pending trades (checks Kalshi for results)
python3 -m football_intel.scripts.settle_trades

# Dry run settlement (no DB changes)
python3 -m football_intel.scripts.settle_trades --dry-run
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Health check |
| `/api/signals/active` | GET | Current betting signals |
| `/api/signals/history` | GET | Historical signal archive |
| `/api/trades` | GET | Paper trade ledger |
| `/api/performance` | GET | Win rate, ROI, PnL, drawdown |
| `/api/accuracy` | GET | Model calibration metrics |
| `/api/model-insights` | GET | Per-match model breakdowns |
| `/api/adaptive` | GET | Feedback loop analysis + params |
| `/api/adaptive/retune` | POST | Trigger manual parameter retune |

---

## NAS Deployment

### Synology
Container Manager → Project → Upload `docker-compose.yml` → Build & Run

### QNAP
Container Station → Create Application → Paste docker-compose contents

### Unraid
Community Applications → Docker Compose → point to `docker-compose.yml`

**Persistent data:** The compose file mounts `config/` and `data/` as volumes so your settings and trade history survive container restarts.

---

## License

Private project. Not licensed for redistribution.
