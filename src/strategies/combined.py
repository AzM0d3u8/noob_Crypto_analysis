"""Combined strategy placeholder: MA trend filter + RSI trigger."""

from __future__ import annotations

import pandas as pd

from src.strategies.ma_crossover import generate_signals as ma_signals
from src.strategies.rsi_reversion import generate_signals as rsi_signals



def generate_signals(df: pd.DataFrame) -> pd.Series:
    """Long when MA is long and RSI strategy is long."""
    ma = ma_signals(df)
    rsi = rsi_signals(df)
    return ((ma == 1) & (rsi == 1)).astype(int)
