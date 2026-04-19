"""Kalshi client with RSA-PSS request signing.

Implements the official Kalshi authentication scheme:
- Each request is signed with an RSA private key.
- Headers: KALSHI-ACCESS-KEY, KALSHI-ACCESS-TIMESTAMP, KALSHI-ACCESS-SIGNATURE.
- Signature = RSA-PSS(SHA256) over: timestamp + METHOD + path (no query params).

Supports REST polling for markets and a WebSocket stub for live price/OB data.
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from football_intel.common.config import load_config
from football_intel.common.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class MarketQuote:
    market_id: str
    contract_ticker: str
    last_price: float
    bid: Optional[float]
    ask: Optional[float]
    depth: Dict[str, Any]


def _load_private_key(path: str):
    """Load an RSA private key from a PEM .key file."""
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(
            f.read(), password=None, backend=default_backend()
        )


def _sign_request(private_key, timestamp_ms: str, method: str, path: str) -> str:
    """Create an RSA-PSS signature for a Kalshi API request.

    The message to sign is: timestamp_ms + METHOD + path (without query params).
    """
    path_without_query = path.split("?")[0]
    message = f"{timestamp_ms}{method}{path_without_query}".encode("utf-8")
    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")


class KalshiClient:
    def __init__(self) -> None:
        cfg = load_config().kalshi
        self.base_url = cfg.base_url.rstrip("/")
        self.ws_url = cfg.ws_url
        self.key_id = cfg.key_id
        self.football_prefix = cfg.football_markets_prefix
        self.private_key = _load_private_key(cfg.private_key_path)
        self.session = requests.Session()

    def _auth_headers(self, method: str, path: str) -> Dict[str, str]:
        """Build the three Kalshi auth headers for a given request."""
        timestamp_ms = str(int(dt.datetime.now().timestamp() * 1000))
        # The full path from root (e.g. /trade-api/v2/markets)
        full_path = urlparse(self.base_url + path).path
        signature = _sign_request(self.private_key, timestamp_ms, method, full_path)
        return {
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
            "KALSHI-ACCESS-SIGNATURE": signature,
        }

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = self._auth_headers("GET", path)
        logger.debug("GET %s params=%s", url, params)
        resp = self.session.get(url, headers=headers, params=params or {}, timeout=10)
        resp.raise_for_status()
        return resp.json()

    # --- REST polling -----------------------------------------------------

    def list_football_markets(self) -> List[Dict[str, Any]]:
        """List football-related markets using a naming convention prefix."""
        data = self._get("/markets", params={"search": self.football_prefix})
        return data.get("markets", data)

    def get_market(self, ticker: str) -> Dict[str, Any]:
        """Fetch a single market by ticker.

        Returns the full market dict (may be nested under 'market' key).
        The caller should inspect 'status' and 'result' fields:
          - status: 'active' | 'closed' | 'determined' | 'finalized'
          - result: 'yes' | 'no' | '' (empty until determined)
        """
        data = self._get(f"/markets/{ticker}")
        return data.get("market", data)

    def get_order_book(self, market_id: str) -> Dict[str, Any]:
        data = self._get(f"/markets/{market_id}/orderbook")
        return data

    # --- WebSocket streaming (stub) --------------------------------------

    def stream_order_books(
        self,
        market_ids: List[str],
        on_update: Callable[[Dict[str, Any]], None],
        stop_event: Optional[threading.Event] = None,
    ) -> None:
        """Stream live order-book updates for given markets.

        This is a minimal stub: it connects, subscribes to the given market IDs,
        and forwards any messages to the provided callback.
        """
        try:
            import websocket as ws_lib  # type: ignore[import-untyped]
        except ImportError:
            logger.error("websocket-client not installed; cannot stream order books")
            return

        stop_event = stop_event or threading.Event()

        # Build auth headers for the WS handshake
        timestamp_ms = str(int(dt.datetime.now().timestamp() * 1000))
        ws_path = urlparse(self.ws_url).path
        signature = _sign_request(self.private_key, timestamp_ms, "GET", ws_path)

        ws_headers = {
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
            "KALSHI-ACCESS-SIGNATURE": signature,
        }

        def _run() -> None:
            ws = ws_lib.WebSocketApp(
                self.ws_url,
                header=ws_headers,
                on_message=lambda _ws, msg: on_update(json.loads(msg)),
                on_error=lambda _ws, err: logger.error("Kalshi WS error: %s", err),
                on_close=lambda _ws, _c, _m: logger.info("Kalshi WS closed"),
            )

            def _on_open(_ws) -> None:
                logger.info("Kalshi WS connected; subscribing to markets: %s", market_ids)
                sub_msg = {"type": "subscribe", "markets": market_ids}
                _ws.send(json.dumps(sub_msg))

            ws.on_open = _on_open

            while not stop_event.is_set():
                try:
                    ws.run_forever(ping_interval=20, ping_timeout=10)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Kalshi WS run_forever error: %s", exc)
                time.sleep(5)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    # --- Helper -----------------------------------------------------------

    def build_market_quote(self, market: Dict[str, Any], order_book: Dict[str, Any]) -> MarketQuote:
        """Normalize a market + order book into a MarketQuote object."""
        market_id = str(market.get("id") or market.get("ticker", ""))
        ticker = str(market.get("ticker", ""))
        last_price = float(market.get("last_price") or market.get("yes_ask") or 0.0)

        bids = order_book.get("bids") or order_book.get("yes", [])
        asks = order_book.get("asks") or order_book.get("no", [])

        best_bid = float(bids[0][0]) if bids else None
        best_ask = float(asks[0][0]) if asks else None

        return MarketQuote(
            market_id=market_id,
            contract_ticker=ticker,
            last_price=last_price,
            bid=best_bid,
            ask=best_ask,
            depth={"bids": bids, "asks": asks},
        )
