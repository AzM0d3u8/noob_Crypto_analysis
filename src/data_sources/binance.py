"""Binance OHLCV adapter."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import requests


BINANCE_BASE_URL = "https://api.binance.com"
KLINES_PATH = "/api/v3/klines"
CANONICAL_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume", "symbol", "interval"]
VALID_INTERVALS = {"1h", "1d"}
MAX_LIMIT = 1000


def _to_binance_symbol(symbol: str, quote_asset: str = "USDT") -> str:
    token = symbol.strip().upper()
    if token.endswith(quote_asset):
        return token
    return f"{token}{quote_asset}"


def _to_ms(ts: datetime) -> int:
    return int(ts.timestamp() * 1000)


def _request_klines(
    session: requests.Session,
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    limit: int,
    timeout: float,
) -> list[list[Any]]:
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": limit,
    }
    response = session.get(f"{BINANCE_BASE_URL}{KLINES_PATH}", params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("Unexpected Binance response format.")
    return payload


def fetch_ohlcv(
    symbol: str,
    interval: str,
    start: datetime | None = None,
    end: datetime | None = None,
    quote_asset: str = "USDT",
    timeout: float = 15.0,
) -> pd.DataFrame:
    """Fetch OHLCV from Binance and return a canonical dataframe.

    Args:
        symbol: Base token symbol (for example, "BTC") or full symbol ("BTCUSDT").
        interval: Supported intervals are "1h" and "1d".
        start: Optional UTC start datetime. Defaults to 365 days before ``end``.
        end: Optional UTC end datetime. Defaults to current UTC time.
        quote_asset: Quote asset used when only base token is provided.
        timeout: Per-request timeout in seconds.
    """
    if interval not in VALID_INTERVALS:
        raise ValueError(f"Unsupported interval '{interval}'. Use one of {sorted(VALID_INTERVALS)}")

    end_utc = end.astimezone(timezone.utc) if end else datetime.now(timezone.utc)
    start_utc = start.astimezone(timezone.utc) if start else end_utc - timedelta(days=365)
    if start_utc >= end_utc:
        raise ValueError("start must be earlier than end.")

    symbol_name = symbol.strip().upper()
    market_symbol = _to_binance_symbol(symbol, quote_asset=quote_asset)

    rows: list[dict[str, Any]] = []
    cursor = _to_ms(start_utc)
    end_ms = _to_ms(end_utc)

    with requests.Session() as session:
        while cursor < end_ms:
            klines = _request_klines(
                session=session,
                symbol=market_symbol,
                interval=interval,
                start_ms=cursor,
                end_ms=end_ms,
                limit=MAX_LIMIT,
                timeout=timeout,
            )
            if not klines:
                break

            for candle in klines:
                rows.append(
                    {
                        "timestamp": pd.to_datetime(candle[0], unit="ms", utc=True),
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": float(candle[5]),
                        "symbol": symbol_name,
                        "interval": interval,
                    }
                )

            last_open_time = int(klines[-1][0])
            next_cursor = last_open_time + 1
            if next_cursor <= cursor:
                break
            cursor = next_cursor

            if len(klines) < MAX_LIMIT:
                break

    if not rows:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    out = pd.DataFrame(rows)
    out = out.drop_duplicates(subset=["timestamp", "symbol", "interval"]).sort_values("timestamp")
    return out.reset_index(drop=True).reindex(columns=CANONICAL_COLUMNS)
