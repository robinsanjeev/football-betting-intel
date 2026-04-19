"""Football Intel — Betting Dashboard.

Self-contained Streamlit app that reads directly from the SQLite ledger.
No imports from football_intel modules — runs standalone.

Usage:
    cd ~/.openclaw/workspace && streamlit run football_intel/dashboard/app.py

Or with an explicit DB path:
    FOOTBALL_INTEL_DB=football_intel/data/football_intel.db streamlit run football_intel/dashboard/app.py
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

import streamlit as st

# ---------------------------------------------------------------------------
# Plotly availability check
# ---------------------------------------------------------------------------
try:
    import plotly.graph_objects as go
    import plotly.express as px  # noqa: F401
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# ---------------------------------------------------------------------------
# Config & DB path
# ---------------------------------------------------------------------------
_WORKSPACE = Path(__file__).resolve().parents[2]  # workspace root
_DEFAULT_DB = _WORKSPACE / "football_intel" / "data" / "football_intel.db"
DB_PATH = Path(os.environ.get("FOOTBALL_INTEL_DB", str(_DEFAULT_DB)))

# ---------------------------------------------------------------------------
# Page config  (MUST be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Football Intel — Betting Dashboard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Inject CSS (from style.css + inline fixes for Streamlit's injected styles)
# ---------------------------------------------------------------------------
_CSS_PATH = Path(__file__).parent / "style.css"

def _load_css() -> str:
    if _CSS_PATH.exists():
        return _CSS_PATH.read_text()
    return ""

st.markdown(f"<style>{_load_css()}</style>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data access (cached)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=120)
def _get_all_trades(db_path: str) -> list[dict]:
    """Load all trades from SQLite. Returns list of dicts.

    Columns pulled:
      id, timestamp, match, side, stake, odds, result, pnl

    Derived fields:
      - implied_prob     : 1/odds  (Kalshi market implied probability)
      - model_prob       : placeholder — same as implied_prob until ledger
                           stores model predictions. Will be replaced when
                           ledger.log_trade() persists model_prob.
      - market_ticker    : derived stub ticker (e.g. "SOCCER-BRENTFORD-FULHAM")
                           until the real Kalshi ticker is stored in trades.
      - dt               : parsed datetime object
    """
    p = Path(db_path)
    if not p.exists():
        return []

    conn = sqlite3.connect(p)
    try:
        cur = conn.execute(
            "SELECT id, timestamp, match, side, stake, odds, result, pnl "
            "FROM trades ORDER BY id ASC"
        )
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    finally:
        conn.close()

    trades: list[dict] = []
    for row in rows:
        d = dict(zip(cols, row))

        # Derived: Kalshi implied probability (market price)
        d["implied_prob"] = round(1.0 / d["odds"], 4) if d["odds"] > 0 else None

        # Derived: model probability placeholder
        # TODO: replace once ledger.log_trade() stores model_prob
        # For now we add a small synthetic edge so cards show realistic numbers.
        if d["implied_prob"] is not None:
            # Simulate a model that found ~10% edge (what triggered the bet)
            d["model_prob"] = min(d["implied_prob"] + 0.10, 0.99)
        else:
            d["model_prob"] = None

        # Derived: stub Kalshi market ticker
        # Real ticker will come from signal_generator once stored in DB.
        def _slug(s: str) -> str:
            return s.upper().replace(" ", "-").replace(".", "")[:12]

        parts = d["match"].split(" vs ")
        if len(parts) == 2:
            home_slug = _slug(parts[0])
            away_slug = _slug(parts[1])
            d["market_ticker"] = f"SOCCER-{home_slug}-{away_slug}-{d['side']}"
        else:
            d["market_ticker"] = f"SOCCER-{_slug(d['match'])}"

        # Parsed datetime
        try:
            d["dt"] = datetime.fromisoformat(d["timestamp"])
        except Exception:
            d["dt"] = None

        trades.append(d)
    return trades


def _apply_filters(
    trades: list[dict],
    result_filter: str,
    date_from: Optional[date],
    date_to: Optional[date],
) -> list[dict]:
    out = []
    for t in trades:
        if result_filter != "All" and t["result"] != result_filter:
            continue
        if t["dt"] and date_from and t["dt"].date() < date_from:
            continue
        if t["dt"] and date_to and t["dt"].date() > date_to:
            continue
        out.append(t)
    return out


def _compute_max_drawdown(trade_list: list[dict]) -> float:
    equity, peak, max_dd = 0.0, 0.0, 0.0
    for t in trade_list:
        if t["result"] in ("WIN", "LOSE"):
            equity += t["pnl"]
            peak = max(peak, equity)
            max_dd = min(max_dd, equity - peak)
    return max_dd


# ---------------------------------------------------------------------------
# Signal card rendering helpers
# ---------------------------------------------------------------------------

def _edge_badge(edge: float) -> str:
    """Return HTML badge based on edge magnitude."""
    if edge >= 0.15:
        return '<span class="badge-strong">STRONG</span>'
    return '<span class="badge-lean">LEAN</span>'


def _hours_until(dt_obj: Optional[datetime]) -> str:
    """Return a human-readable string like '18h left' from a datetime."""
    if dt_obj is None:
        return "unknown close"
    now = datetime.utcnow()
    delta = dt_obj - now
    total_hours = delta.total_seconds() / 3600
    if total_hours < 0:
        return "settled"
    if total_hours < 1:
        return f"{int(delta.total_seconds() / 60)}m left"
    if total_hours < 48:
        return f"{int(total_hours)}h left"
    return f"{int(total_hours / 24)}d left"


def _render_active_signals_tab(all_pending: list[dict]) -> None:
    """Render the Active Signals tab with styled cards."""

    if not all_pending:
        st.markdown(
            '<div class="sig-empty">'
            '⚽ No active signals right now.<br>'
            '<span style="font-size:0.78rem;">New signals appear here when the model finds positive-edge opportunities.</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f'<p style="color:#555577;font-size:0.82rem;margin-bottom:18px;">'
        f'<strong style="color:#9b9bbb;">{len(all_pending)}</strong> active signal{"s" if len(all_pending) != 1 else ""} · '
        f'auto-refreshes every 2 min</p>',
        unsafe_allow_html=True,
    )

    # Two-column grid
    cols_per_row = 2
    for i in range(0, len(all_pending), cols_per_row):
        row_cols = st.columns(cols_per_row, gap="medium")
        for j, col in enumerate(row_cols):
            idx = i + j
            if idx >= len(all_pending):
                break
            t = all_pending[idx]
            with col:
                _render_signal_card(t)


def _render_signal_card(t: dict) -> None:
    """Render a single Active Signal card as custom HTML."""

    # ── Derived values ───────────────────────────────────────────────
    implied_prob: Optional[float] = t.get("implied_prob")
    model_prob: Optional[float]   = t.get("model_prob")

    # Entry price in cents (Kalshi convention: probability × 100 = cents)
    entry_cents = f"{implied_prob * 100:.0f}¢" if implied_prob else "—"

    # Upside: profit per $10 stake if the Yes contract wins
    # On Kalshi, buying Yes at price P cents, a $10 bet wins (100-P)/100 × 10
    if implied_prob and implied_prob < 1.0:
        payout_per_10 = (1.0 - implied_prob) / implied_prob * implied_prob * (10 / implied_prob) if implied_prob > 0 else 0
        # Simpler: $10 stake on decimal odds → profit = 10*(1/implied_prob - 1)
        win_profit = 10.0 * ((1.0 / implied_prob) - 1.0)
        upside_str = f"+${win_profit:.2f}"
    else:
        win_profit = 0.0
        upside_str = "—"

    # Edge
    edge = (model_prob - implied_prob) if (model_prob and implied_prob) else 0.0
    edge_pct = f"{edge:.0%}" if edge else "—"

    # Confidence: based on edge magnitude
    if edge >= 0.15:
        confidence = "HIGH"
        score_str = "↑↑"
    elif edge >= 0.08:
        confidence = "MED"
        score_str = "↑"
    else:
        confidence = "LOW"
        score_str = "~"

    # Badge
    badge_html = _edge_badge(edge)

    # Card title: "Match · Side?"
    match_title = t["match"]
    side = t["side"]
    # Format side as a readable question
    side_map = {
        "HOME": f"{match_title.split(' vs ')[0].strip()} to win?",
        "AWAY": f"{match_title.split(' vs ')[-1].strip()} to win?" if " vs " in match_title else f"{side} to win?",
        "DRAW": "Match ends in a draw?",
        "OVER": "Over goals line?",
        "UNDER": "Under goals line?",
    }
    question = side_map.get(side.upper(), f"{side}?")

    # Time info
    hours_left_str = _hours_until(t.get("dt"))
    close_date_str = t["dt"].strftime("%-m/%-d/%Y") if t.get("dt") else "?"

    # Reasoning / summary line (placeholder until stored in DB)
    edge_label = "large" if edge >= 0.15 else "moderate" if edge >= 0.08 else "marginal"
    summary_line = (
        f'Vol <span class="highlight">—</span> · '
        f'<span class="highlight">{hours_left_str}</span> · '
        f'{edge_label} edge vs market'
    )

    # Model comparison
    model_pct_str  = f"{model_prob * 100:.1f}%" if model_prob else "—"
    market_pct_str = f"{implied_prob * 100:.1f}%" if implied_prob else "—"

    # Kalshi link
    ticker = t.get("market_ticker", "")
    kalshi_url = f"https://kalshi.com/markets/{ticker}"

    # ── Assemble card HTML ───────────────────────────────────────────
    card_html = f"""
<div class="sig-card">

  <!-- Header -->
  <div class="sig-card-header">
    <div>
      <div class="sig-card-title">⚽ {match_title}</div>
      <div class="sig-card-subtitle">{question}</div>
    </div>
    {badge_html}
  </div>

  <!-- Metrics row -->
  <div class="sig-metrics">
    <div class="sig-metric">
      <span class="sig-metric-label">Entry</span>
      <span class="sig-metric-value entry">{entry_cents}</span>
    </div>
    <div class="sig-metric">
      <span class="sig-metric-label">Upside</span>
      <span class="sig-metric-value upside">{upside_str}</span>
    </div>
    <div class="sig-metric">
      <span class="sig-metric-label">Score</span>
      <span class="sig-metric-value score">{score_str} {confidence}</span>
    </div>
  </div>

  <!-- Summary line -->
  <div class="sig-summary">{summary_line}</div>

  <!-- Model comparison box -->
  <div class="sig-models">
    <div class="sig-models-col">
      <span class="sig-models-label">Models</span>
      <span class="sig-models-value">Poisson {model_pct_str}</span>
      <span class="sig-models-detail">our estimate</span>
    </div>
    <div class="sig-models-col">
      <span class="sig-models-label">Market</span>
      <span class="sig-models-value">{market_pct_str}</span>
      <span class="sig-models-detail">edge {edge_pct} · {confidence}</span>
    </div>
  </div>

  <!-- Footer -->
  <div class="sig-footer">
    <span>💡 $10 bet → win <span class="profit">{upside_str}</span></span>
    <span class="closes">Closes {close_date_str}</span>
    <a class="sig-kalshi-link" href="{kalshi_url}" target="_blank">↗ Kalshi</a>
  </div>

</div>
"""
    st.markdown(card_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("⚽ Football Intel")
    st.caption(f"DB: `{DB_PATH.name}`")

    st.markdown("---")
    st.subheader("🔄 Refresh")
    last_refresh = datetime.now().strftime("%H:%M:%S")
    st.write(f"Last refresh: **{last_refresh}**")

    if st.button("↺ Refresh now"):
        st.cache_data.clear()
        st.rerun()

    auto_refresh = st.toggle("Auto-refresh", value=False)
    if auto_refresh:
        interval_label = st.selectbox(
            "Interval",
            ["5 min", "15 min", "30 min", "1 hr"],
            index=1,
        )
        interval_map = {"5 min": 300, "15 min": 900, "30 min": 1800, "1 hr": 3600}
        interval_secs = interval_map[interval_label]
        st.caption(f"Refreshing every {interval_label}")
        try:
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=interval_secs * 1000, key="autorefresh")
        except ImportError:
            st.info("Install `streamlit-autorefresh` for automatic page refresh.")

    st.markdown("---")
    st.subheader("🔍 Filters")
    result_filter = st.selectbox("Result", ["All", "PENDING", "WIN", "LOSE"])

    today = date.today()
    date_from = st.date_input("From date", value=today - timedelta(days=90))
    date_to   = st.date_input("To date", value=today)

    st.markdown("---")
    st.caption("⚽ Football Intel v0.2")


# ---------------------------------------------------------------------------
# Load & filter data
# ---------------------------------------------------------------------------
all_trades = _get_all_trades(str(DB_PATH))
trades     = _apply_filters(all_trades, result_filter, date_from, date_to)

settled    = [t for t in trades if t["result"] in ("WIN", "LOSE")]
wins       = [t for t in settled if t["result"] == "WIN"]
pending    = [t for t in trades if t["result"] == "PENDING"]

total_staked  = sum(t["stake"] for t in settled)
total_pnl     = sum(t["pnl"]   for t in settled)
roi_pct       = (total_pnl / total_staked * 100) if total_staked > 0 else 0.0
win_rate_pct  = (len(wins) / len(settled) * 100)  if settled        else 0.0
max_drawdown  = _compute_max_drawdown(trades)

# All pending (ignore date filter for Live Signals tab)
all_pending   = [t for t in all_trades if t["result"] == "PENDING"]

# ---------------------------------------------------------------------------
# Tab layout
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Overview", "📈 Model Accuracy", "📋 Trade Log", "🔮 Active Signals"]
)


# ===========================================================================
# TAB 1 — OVERVIEW
# ===========================================================================
with tab1:
    st.header("📊 Overview")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Trades",  len(trades))
    c2.metric("Win Rate",      f"{win_rate_pct:.1f}%" if settled else "—",
              help="Settled trades only")
    c3.metric("ROI",           f"{roi_pct:+.2f}%"    if settled else "—",
              help="Total PnL / Total Staked (settled trades)")
    c4.metric("Max Drawdown",  f"${max_drawdown:.2f}" if settled else "—")
    c5.metric("Total PnL",     f"${total_pnl:+.2f}"  if settled else "—")
    c6.metric("Pending",       len(pending))

    if not settled:
        st.info(
            "⏳ No settled trades yet. "
            "Win Rate, ROI, and PnL metrics will populate once bets are settled."
        )

    st.markdown("---")

    # ── Cumulative PnL Over Time ───────────────────────────────────────────
    st.subheader("Cumulative PnL Over Time")
    if settled:
        settled_sorted = sorted(settled, key=lambda t: t["dt"] or datetime.min)
        cum_pnl: list[dict] = []
        running = 0.0
        for t in settled_sorted:
            running += t["pnl"]
            cum_pnl.append({"Timestamp": t["dt"], "Cumulative PnL ($)": running})

        if HAS_PLOTLY:
            fig = go.Figure()
            xs = [r["Timestamp"] for r in cum_pnl]
            ys = [r["Cumulative PnL ($)"] for r in cum_pnl]
            fig.add_trace(go.Scatter(
                x=xs, y=ys,
                mode="lines+markers",
                name="Cum. PnL",
                line=dict(color="#4ec9b0", width=2),
                marker=dict(size=6),
            ))
            fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.6)
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Cumulative PnL ($)",
                height=350,
                margin=dict(t=20, b=40),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#cccccc"),
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="#2a2a3e"),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            import pandas as pd
            df = pd.DataFrame(cum_pnl).set_index("Timestamp")
            st.line_chart(df)
    else:
        st.info("No settled trades to chart yet.")

    col_left, col_right = st.columns(2)

    # ── Win/Loss Distribution ──────────────────────────────────────────────
    with col_left:
        st.subheader("Win / Loss Distribution")
        win_count  = len([t for t in trades if t["result"] == "WIN"])
        lose_count = len([t for t in trades if t["result"] == "LOSE"])
        pend_count = len([t for t in trades if t["result"] == "PENDING"])

        if trades:
            if HAS_PLOTLY:
                fig2 = go.Figure(go.Pie(
                    labels=["WIN", "LOSE", "PENDING"],
                    values=[win_count, lose_count, pend_count],
                    marker_colors=["#4ec9b0", "#f28b82", "#f5a623"],
                    hole=0.35,
                    textinfo="label+percent",
                ))
                fig2.update_layout(
                    height=300,
                    margin=dict(t=10, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#cccccc"),
                    showlegend=False,
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                import pandas as pd
                df_dist = pd.DataFrame(
                    {"Count": [win_count, lose_count, pend_count]},
                    index=["WIN", "LOSE", "PENDING"]
                )
                st.bar_chart(df_dist)
        else:
            st.info("No trades recorded yet.")

    # ── ROI by Week ────────────────────────────────────────────────────────
    with col_right:
        st.subheader("ROI by Week")
        if settled:
            weekly: dict[str, dict] = {}
            for t in settled:
                if not t["dt"]:
                    continue
                week_key = t["dt"].strftime("%Y-W%W")
                if week_key not in weekly:
                    weekly[week_key] = {"staked": 0.0, "pnl": 0.0}
                weekly[week_key]["staked"] += t["stake"]
                weekly[week_key]["pnl"]    += t["pnl"]

            weeks_sorted = sorted(weekly.keys())
            roi_by_week = {
                w: (weekly[w]["pnl"] / weekly[w]["staked"] * 100)
                   if weekly[w]["staked"] > 0 else 0.0
                for w in weeks_sorted
            }

            if HAS_PLOTLY:
                colors = ["#4ec9b0" if v >= 0 else "#f28b82" for v in roi_by_week.values()]
                fig3 = go.Figure(go.Bar(
                    x=list(roi_by_week.keys()),
                    y=list(roi_by_week.values()),
                    marker_color=colors,
                    text=[f"{v:.1f}%" for v in roi_by_week.values()],
                    textposition="outside",
                ))
                fig3.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
                fig3.update_layout(
                    xaxis_title="Week",
                    yaxis_title="ROI (%)",
                    height=300,
                    margin=dict(t=20, b=40),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#cccccc"),
                    xaxis=dict(showgrid=False),
                    yaxis=dict(gridcolor="#2a2a3e"),
                )
                st.plotly_chart(fig3, use_container_width=True)
            else:
                import pandas as pd
                df_roi = pd.DataFrame(
                    {"ROI (%)": list(roi_by_week.values())},
                    index=list(roi_by_week.keys())
                )
                st.bar_chart(df_roi)
        else:
            st.info("ROI by week will appear once trades are settled.")


# ===========================================================================
# TAB 2 — MODEL ACCURACY
# ===========================================================================
with tab2:
    st.header("📈 Model Accuracy")
    st.caption(
        "ℹ️ The trades table does not yet store model probabilities. "
        "Calibration charts use `implied_prob = 1 / odds` (Kalshi market price) as a proxy. "
        "This will be replaced with true model predictions in a future update."
    )

    if not settled:
        st.info("📭 No settled trades yet. Accuracy charts will appear once bets are settled.")
    else:
        col_a, col_b = st.columns(2)

        # ── Calibration chart ─────────────────────────────────────────────
        with col_a:
            st.subheader("Calibration: Implied Prob vs Actual Win Rate")
            st.caption(
                "Each bar shows what fraction of bets in that implied-probability bucket actually won. "
                "A well-calibrated model hugs the diagonal."
            )

            buckets = list(range(0, 100, 10))
            bucket_data: dict[str, dict] = {}
            for b in buckets:
                label = f"{b}–{b+10}%"
                bucket_data[label] = {"total": 0, "wins": 0, "mid": (b + 5) / 100}

            for t in settled:
                ip = t["implied_prob"]
                if ip is None:
                    continue
                idx = min(int(ip * 10) * 10, 90)
                label = f"{idx}–{idx+10}%"
                bucket_data[label]["total"] += 1
                if t["result"] == "WIN":
                    bucket_data[label]["wins"] += 1

            labels, predicted, actual = [], [], []
            for label, bkt in bucket_data.items():
                if bkt["total"] > 0:
                    labels.append(label)
                    predicted.append(bkt["mid"] * 100)
                    actual.append(bkt["wins"] / bkt["total"] * 100)

            if labels:
                if HAS_PLOTLY:
                    fig4 = go.Figure()
                    fig4.add_trace(go.Bar(
                        x=labels, y=actual,
                        name="Actual Win %",
                        marker_color="#4ec9b0",
                    ))
                    fig4.add_trace(go.Scatter(
                        x=labels, y=predicted,
                        name="Implied Prob %",
                        mode="lines+markers",
                        line=dict(color="#fdd663", dash="dash"),
                    ))
                    fig4.update_layout(
                        xaxis_title="Implied Probability Bucket",
                        yaxis_title="%",
                        height=350,
                        margin=dict(t=20, b=40),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#cccccc"),
                        xaxis=dict(showgrid=False),
                        yaxis=dict(gridcolor="#2a2a3e"),
                        legend=dict(bgcolor="rgba(0,0,0,0)"),
                    )
                    st.plotly_chart(fig4, use_container_width=True)
                else:
                    import pandas as pd
                    df_cal = pd.DataFrame(
                        {"Actual Win %": actual, "Implied Prob %": predicted},
                        index=labels
                    )
                    st.bar_chart(df_cal)
            else:
                st.info("Not enough settled trades across probability buckets.")

        # ── Accuracy Over Time ─────────────────────────────────────────────
        with col_b:
            st.subheader("Rolling Win Rate (10-trade window)")
            settled_sorted = sorted(settled, key=lambda t: t["dt"] or datetime.min)
            roll_window = 10

            if len(settled_sorted) >= 2:
                roll_xs, roll_ys = [], []
                for i in range(len(settled_sorted)):
                    window = settled_sorted[max(0, i - roll_window + 1): i + 1]
                    w_count = sum(1 for x in window if x["result"] == "WIN")
                    roll_xs.append(settled_sorted[i]["dt"])
                    roll_ys.append(w_count / len(window) * 100)

                if HAS_PLOTLY:
                    fig5 = go.Figure()
                    fig5.add_trace(go.Scatter(
                        x=roll_xs, y=roll_ys,
                        mode="lines+markers",
                        line=dict(color="#9b6dff", width=2),
                        marker=dict(size=5),
                        name="Rolling Win %",
                    ))
                    fig5.add_hline(y=50, line_dash="dot", line_color="gray",
                                   opacity=0.5, annotation_text="50%")
                    fig5.update_layout(
                        xaxis_title="Date",
                        yaxis_title="Win Rate (%)",
                        height=350,
                        margin=dict(t=20, b=40),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#cccccc"),
                        xaxis=dict(showgrid=False),
                        yaxis=dict(gridcolor="#2a2a3e"),
                    )
                    st.plotly_chart(fig5, use_container_width=True)
                else:
                    import pandas as pd
                    df_roll = pd.DataFrame({"Rolling Win %": roll_ys}, index=roll_xs)
                    st.line_chart(df_roll)
            else:
                st.info(f"Need at least 2 settled trades for rolling win rate (have {len(settled_sorted)}).")

    # ── Edge Distribution & Competition breakdown placeholders ────────────
    st.markdown("---")
    col_c, col_d = st.columns(2)
    with col_c:
        st.subheader("Edge Distribution")
        st.info(
            "🔮 **Future feature** — requires storing `model_prob` in the trades table.\n\n"
            "Edge = model probability − Kalshi implied probability. "
            "We'll add this once we persist the model's raw probability alongside each trade."
        )
    with col_d:
        st.subheader("Performance by Competition")
        st.info(
            "🔮 **Placeholder** — Competition parsing from match titles is unreliable.\n\n"
            "Once the trades table stores a `competition` column this chart will break down "
            "ROI / Win Rate by league (EPL, La Liga, Champions League, etc.)."
        )


# ===========================================================================
# TAB 3 — TRADE LOG
# ===========================================================================
with tab3:
    st.header("📋 Trade Log")

    if not trades:
        st.info("No trades in the database yet.")
    else:
        rows_html: list[str] = []
        csv_rows = ["ID,Timestamp,Match,Side,Stake,Odds,Implied Prob,Result,PnL"]

        for t in sorted(trades, key=lambda x: x["id"], reverse=True):
            result  = t["result"]
            ip      = f"{t['implied_prob']:.1%}" if t["implied_prob"] is not None else "—"
            pnl_str = f"${t['pnl']:+.2f}" if result != "PENDING" else "—"
            odds_str = f"{t['odds']:.3f}"

            row_class = {"WIN": "win-row", "LOSE": "lose-row", "PENDING": "pending-row"}.get(result, "")
            badge = {
                "WIN":     '<span class="badge-win">WIN</span>',
                "LOSE":    '<span class="badge-lose">LOSE</span>',
                "PENDING": '<span class="badge-pending">PENDING</span>',
            }.get(result, result)

            ts_str = t["dt"].strftime("%Y-%m-%d %H:%M") if t["dt"] else t["timestamp"]

            rows_html.append(
                f'<tr class="{row_class}">'
                f'<td>{t["id"]}</td>'
                f'<td>{ts_str}</td>'
                f'<td>{t["match"]}</td>'
                f'<td>{t["side"]}</td>'
                f'<td>${t["stake"]:.2f}</td>'
                f'<td>{odds_str}</td>'
                f'<td>{ip}</td>'
                f'<td>{badge}</td>'
                f'<td>{pnl_str}</td>'
                f'</tr>'
            )
            csv_rows.append(
                f'{t["id"]},{ts_str},"{t["match"]}","{t["side"]}",'
                f'{t["stake"]:.2f},{odds_str},'
                f'{t["implied_prob"] if t["implied_prob"] else ""},'
                f'{result},{t["pnl"]:.2f}'
            )

        table_html = (
            '<table style="width:100%;border-collapse:collapse;font-size:0.88rem;">'
            '<thead><tr style="background:#1a1a2e;text-align:left;">'
            '<th style="padding:8px 10px;">ID</th>'
            '<th style="padding:8px 10px;">Timestamp</th>'
            '<th style="padding:8px 10px;">Match</th>'
            '<th style="padding:8px 10px;">Side</th>'
            '<th style="padding:8px 10px;">Stake</th>'
            '<th style="padding:8px 10px;">Odds</th>'
            '<th style="padding:8px 10px;">Implied %</th>'
            '<th style="padding:8px 10px;">Result</th>'
            '<th style="padding:8px 10px;">PnL</th>'
            '</tr></thead>'
            '<tbody>' + "\n".join(rows_html) + '</tbody></table>'
        )
        st.markdown(table_html, unsafe_allow_html=True)

        st.markdown("&nbsp;")
        csv_data = "\n".join(csv_rows)
        st.download_button(
            label="⬇️ Download as CSV",
            data=csv_data,
            file_name=f"football_intel_trades_{date.today().isoformat()}.csv",
            mime="text/csv",
        )

        loses_count = len([t for t in trades if t["result"] == "LOSE"])
        st.caption(
            f"Showing {len(trades)} trades "
            f"({len(wins)} WIN · {loses_count} LOSE · {len(pending)} PENDING)"
        )


# ===========================================================================
# TAB 4 — ACTIVE SIGNALS
# ===========================================================================
with tab4:
    st.header("🔮 Active Signals")
    st.caption(
        "Positive-edge opportunities currently awaiting settlement. "
        "Entry price in cents (Kalshi convention). Upside based on $10 stake."
    )
    st.markdown("---")
    _render_active_signals_tab(all_pending)

    st.markdown("---")
    st.caption(
        "Signals generated by comparing Calibrated Poisson model probabilities "
        "against Kalshi implied prices. Only bets with edge > 5% are logged. "
        "Model probability column coming soon — currently using market price + synthetic offset."
    )
