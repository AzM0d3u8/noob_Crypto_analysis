"""Moving-average crossover strategy placeholder."""

from __future__ import annotations

import pandas as pd



def generate_signals(df: pd.DataFrame, short_window: int = 20, long_window: int = 50) -> pd.Series:
    """Return +1 long / 0 flat signals using MA crossover."""
    short_ma = df["close"].rolling(short_window, min_periods=short_window).mean()
    long_ma = df["close"].rolling(long_window, min_periods=long_window).mean()
    signal = (short_ma > long_ma).astype(int)
    return signal.shift(1).fillna(0)
