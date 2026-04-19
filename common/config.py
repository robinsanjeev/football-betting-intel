"""Config loader for the Football Betting Intelligence System.

Reads config/config.yaml (user-specific, gitignored) with a fallback to
config.yaml.example for structure reference.
"""

from __future__ import annotations

import dataclasses
import pathlib
from typing import Any, Dict

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"


class ConfigError(RuntimeError):
    pass


@dataclasses.dataclass
class FootballDataConfig:
    api_key: str
    base_url: str
    leagues: list[str]
    max_leagues_per_run: int = 8


@dataclasses.dataclass
class KalshiConfig:
    key_id: str
    private_key_path: str
    base_url: str
    ws_url: str
    football_markets_prefix: str


@dataclasses.dataclass
class OddsApiConfig:
    api_key: str
    base_url: str
    regions: str
    markets: str
    sports: list[str]


@dataclasses.dataclass
class TelegramConfig:
    bot_token: str
    chat_id: str


@dataclasses.dataclass
class StorageConfig:
    db_path: str
    cache_ttl_hours: int


@dataclasses.dataclass
class LoggingConfig:
    level: str
    log_file: str


@dataclasses.dataclass
class AppConfig:
    football_data: FootballDataConfig
    kalshi: KalshiConfig
    odds_api: OddsApiConfig
    telegram: TelegramConfig
    storage: StorageConfig
    logging: LoggingConfig


def _load_yaml() -> Dict[str, Any]:
    cfg_path = CONFIG_DIR / "config.yaml"
    if not cfg_path.exists():
        example = CONFIG_DIR / "config.yaml.example"
        raise ConfigError(
            f"Missing config.yaml at {cfg_path}. Copy {example} and fill in your credentials."
        )
    with cfg_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def load_config() -> AppConfig:
    raw = _load_yaml()

    try:
        fd = raw["football_data"]
        ks = raw["kalshi"]
        oa = raw["odds_api"]
        tg = raw["telegram"]
        st = raw["storage"]
        lg = raw["logging"]
    except KeyError as e:
        raise ConfigError(f"Missing top-level config section: {e.args[0]}") from e

    return AppConfig(
        football_data=FootballDataConfig(
            api_key=str(fd["api_key"]),
            base_url=str(fd.get("base_url", "https://api.football-data.org/v4")),
            leagues=list(fd.get("leagues", [])),
            max_leagues_per_run=int(fd.get("max_leagues_per_run", 8)),
        ),
        kalshi=KalshiConfig(
            key_id=str(ks["key_id"]),
            private_key_path=str(ks["private_key_path"]),
            base_url=str(ks.get("base_url", "https://demo-api.kalshi.co/trade-api/v2")),
            ws_url=str(ks.get("ws_url", "wss://demo-api.kalshi.co/trade-api/ws/v2")),
            football_markets_prefix=str(
                ks.get("football_markets_prefix", "FOOTBALL")
            ),
        ),
        odds_api=OddsApiConfig(
            api_key=str(oa["api_key"]),
            base_url=str(oa.get("base_url", "https://api.the-odds-api.com/v4")),
            regions=str(oa.get("regions", "uk,eu")),
            markets=str(oa.get("markets", "h2h")),
            sports=list(oa.get("sports", ["soccer_epl"])),
        ),
        telegram=TelegramConfig(
            bot_token=str(tg["bot_token"]),
            chat_id=str(tg["chat_id"]),
        ),
        storage=StorageConfig(
            db_path=str(st.get("db_path", "football_intel/data/football_intel.db")),
            cache_ttl_hours=int(st.get("cache_ttl_hours", 6)),
        ),
        logging=LoggingConfig(
            level=str(lg.get("level", "INFO")),
            log_file=str(lg.get("log_file", "football_intel/logs/system.log")),
        ),
    )
