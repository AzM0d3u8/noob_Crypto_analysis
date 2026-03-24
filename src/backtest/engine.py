"""Vectorized backtest engine placeholder."""

from __future__ import annotations

import pandas as pd



def run_backtest(df: pd.DataFrame, signal: pd.Series, initial_capital: float = 1000.0) -> pd.DataFrame:
    """Compute equity curve for a long/flat strategy."""
    returns = df["close"].pct_change().fillna(0)
    strat_returns = returns * signal
    equity = initial_capital * (1 + strat_returns).cumprod()
    out = pd.DataFrame({"returns": returns, "strategy_returns": strat_returns, "equity": equity})
    return out
