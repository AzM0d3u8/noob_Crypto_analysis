"""Data cleaning helpers for crypto OHLCV bars."""

from __future__ import annotations

import pandas as pd


CANONICAL_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume", "symbol", "interval"]


def clean_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Apply timestamp normalization, de-duplication, and sorting."""
    if df.empty:
        return df.reindex(columns=CANONICAL_COLUMNS)

    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True)
    out = out.drop_duplicates(subset=["timestamp", "symbol", "interval"]) 
    out = out.sort_values("timestamp").reset_index(drop=True)
    return out.reindex(columns=CANONICAL_COLUMNS)
