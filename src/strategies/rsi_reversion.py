"""RSI threshold strategy placeholder."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.indicators import rsi



def generate_signals(df: pd.DataFrame, lower: float = 30, upper: float = 70) -> pd.Series:
    """Return +1 when oversold, 0 when overbought, hold previous otherwise."""
    rsi_values = rsi(df["close"])
    raw = pd.Series(index=df.index, data=np.nan, dtype="float")
    raw[rsi_values < lower] = 1
    raw[rsi_values > upper] = 0
    return raw.ffill().fillna(0).shift(1).fillna(0)
