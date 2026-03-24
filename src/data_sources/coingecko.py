"""CoinGecko OHLCV adapter."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import requests


COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
CANONICAL_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume", "symbol", "interval"]
VALID_INTERVALS = {"1h": "1h", "1d": "1d"}

SYMBOL_TO_COIN_ID = {
    "btc": "bitcoin",
    "eth": "ethereum",
}


def _to_coin_id(symbol: str) -> str:
    token = symbol.strip().lower()
    if token in SYMBOL_TO_COIN_ID:
        return SYMBOL_TO_COIN_ID[token]
    return token


def _to_sec(ts: datetime) -> int:
    return int(ts.timestamp())


def _market_chart_range(
    session: requests.Session,
    coin_id: str,
    start_sec: int,
    end_sec: int,
    timeout: float,
) -> dict[str, Any]:
    url = f"{COINGECKO_BASE_URL}/coins/{coin_id}/market_chart/range"
    params = {
        "vs_currency": "usd",
        "from": start_sec,
        "to": end_sec,
    }
    response = session.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Unexpected CoinGecko response format.")
    return payload


def _series_from_points(points: list[list[float]], value_name: str) -> pd.Series:
    if not points:
        return pd.Series(dtype="float64", name=value_name)
    frame = pd.DataFrame(points, columns=["timestamp_ms", value_name])
    frame["timestamp"] = pd.to_datetime(frame["timestamp_ms"], unit="ms", utc=True)
    frame = frame.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
    return frame.set_index("timestamp")[value_name].astype(float)


def fetch_ohlcv(
    symbol: str,
    interval: str,
    start: datetime | None = None,
    end: datetime | None = None,
    timeout: float = 20.0,
) -> pd.DataFrame:
    """Fetch and resample CoinGecko market data into canonical OHLCV bars.

    CoinGecko's public market chart range endpoint provides timestamped price and
    total volume points. This adapter resamples the price stream to OHLC and
    uses resampled volume means for the bar volume field.
    """
    if interval not in VALID_INTERVALS:
        raise ValueError(f"Unsupported interval '{interval}'. Use one of {sorted(VALID_INTERVALS)}")

    end_utc = end.astimezone(timezone.utc) if end else datetime.now(timezone.utc)
    start_utc = start.astimezone(timezone.utc) if start else end_utc - timedelta(days=365)
    if start_utc >= end_utc:
        raise ValueError("start must be earlier than end.")

    symbol_name = symbol.strip().upper()
    coin_id = _to_coin_id(symbol)
    rule = VALID_INTERVALS[interval]

    with requests.Session() as session:
        payload = _market_chart_range(
            session=session,
            coin_id=coin_id,
            start_sec=_to_sec(start_utc),
            end_sec=_to_sec(end_utc),
            timeout=timeout,
        )

    price_series = _series_from_points(payload.get("prices", []), "price")
    volume_series = _series_from_points(payload.get("total_volumes", []), "total_volume")

    if price_series.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    ohlc = price_series.resample(rule).ohlc().dropna()
    volume = volume_series.resample(rule).mean() if not volume_series.empty else pd.Series(dtype="float64")
    frame = ohlc.join(volume.rename("volume"), how="left")

    out = frame.rename(columns={"open": "open", "high": "high", "low": "low", "close": "close"}).reset_index()
    out["volume"] = out["volume"].astype(float)
    out["symbol"] = symbol_name
    out["interval"] = interval

    out = out.drop_duplicates(subset=["timestamp", "symbol", "interval"]).sort_values("timestamp")
    return out.reset_index(drop=True).reindex(columns=CANONICAL_COLUMNS)
