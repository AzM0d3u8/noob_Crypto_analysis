"""Buy-and-hold baseline placeholder."""

from __future__ import annotations

import pandas as pd



def run_buy_and_hold(df: pd.DataFrame, initial_capital: float = 1000.0) -> pd.DataFrame:
    """Compute buy-and-hold equity curve."""
    returns = df["close"].pct_change().fillna(0)
    equity = initial_capital * (1 + returns).cumprod()
    return pd.DataFrame({"returns": returns, "equity": equity})
