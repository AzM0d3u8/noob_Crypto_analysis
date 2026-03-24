"""Performance metric placeholders."""

from __future__ import annotations

import numpy as np
import pandas as pd



def total_return(equity: pd.Series) -> float:
    """Total return from first to last equity point."""
    if equity.empty:
        return 0.0
    return float(equity.iloc[-1] / equity.iloc[0] - 1)



def sharpe_ratio(returns: pd.Series, periods_per_year: int = 365) -> float:
    """Annualized Sharpe ratio with zero risk-free rate."""
    if returns.std(ddof=0) == 0:
        return 0.0
    return float(np.sqrt(periods_per_year) * returns.mean() / returns.std(ddof=0))



def max_drawdown(equity: pd.Series) -> float:
    """Maximum drawdown over an equity curve."""
    if equity.empty:
        return 0.0
    running_max = equity.cummax()
    drawdown = equity / running_max - 1
    return float(drawdown.min())
