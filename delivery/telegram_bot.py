"""Telegram alert sender for betting recommendations.

This is a simple one-shot sender script; wiring it into cron or a scheduler
is left to a separate runner module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests

from football_intel.common.config import load_config
from football_intel.common.logging_utils import get_logger
from football_intel.strategy.signal_generator import BettingSignal

logger = get_logger(__name__)


@dataclass
class BetAlert:
    match: str
    kickoff_utc: str
    side: str
    model_prob: float
    implied_prob: float
    ev: float
    kalshi_url: Optional[str] = None

    def format_message(self) -> str:
        return (
            f"⚽ Betting Signal\n"
            f"Match: {self.match}\n"
            f"Kickoff (UTC): {self.kickoff_utc}\n"
            f"Recommended side: {self.side}\n"
            f"Model prob: {self.model_prob:.1%}\n"
            f"Market implied prob: {self.implied_prob:.1%}\n"
            f"EV (per $10): ${self.ev:0.2f}\n"
            + (f"Kalshi: {self.kalshi_url}\n" if self.kalshi_url else "")
        )


class TelegramClient:
    def __init__(self) -> None:
        cfg = load_config().telegram
        self.token = cfg.bot_token
        self.chat_id = cfg.chat_id

    def send_message(self, text: str, parse_mode: str = "", topic_id: int | None = None) -> None:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if topic_id is not None:
            payload["message_thread_id"] = topic_id
        logger.info("Sending Telegram alert to %s", self.chat_id)
        resp = requests.post(url, json=payload, timeout=10)
        if not resp.ok:
            logger.error(
                "Telegram sendMessage failed: status=%s body=%s", resp.status_code, resp.text
            )
            resp.raise_for_status()

    def send_bet_alert(self, alert: BetAlert) -> None:
        self.send_message(alert.format_message())

    def send_signal_alert(self, signal: BettingSignal, topic_id: int | None = None) -> None:
        """Format a BettingSignal and send it as a Telegram message."""
        _BET_TYPE_EMOJI = {
            "MONEYLINE": "⚽",
            "OVER_UNDER": "🥅",
            "SPREAD": "📊",
            "FIRST_HALF": "⏱️",
            "BTTS": "🤝",
        }
        bet_emoji = _BET_TYPE_EMOJI.get(signal.bet_type, "🎯")

        # Format EV as signed percentage
        ev_pct = signal.ev_per_dollar * 100
        if ev_pct >= 0:
            ev_str = f"+{ev_pct:.0f}%"
        else:
            ev_str = f"{ev_pct:.0f}%"

        text = (
            f"🔥 BET | {bet_emoji} {signal.bet_type} — {signal.match_title}\n"
            f"\n"
            f"📈 Chance: ~{signal.model_prob:.0%}\n"
            f"\n"
            f"💰 Value: {ev_str} per $1 if it hits\n"
            f"\n"
            f"🧠 Why: {signal.reasoning}\n"
            f"\n"
            f"🔗 {signal.kalshi_url}"
        )
        logger.info(
            "Sending signal alert for %s (%s) to Telegram",
            signal.match_title,
            signal.bet_type,
        )
        self.send_message(text, topic_id=topic_id)
