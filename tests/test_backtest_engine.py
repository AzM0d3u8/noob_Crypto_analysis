"""Backtest engine smoke tests."""

import pandas as pd

from src.backtest.baseline import run_buy_and_hold
from src.backtest.engine import run_backtest



def test_run_backtest_returns_equity_column() -> None:
    df = pd.DataFrame({"close": [100, 101, 102, 99, 105]})
    signal = pd.Series([0, 1, 1, 0, 1])
    out = run_backtest(df, signal, initial_capital=1000)
    assert "equity" in out.columns



def test_buy_and_hold_returns_equity_column() -> None:
    df = pd.DataFrame({"close": [100, 102, 101, 103]})
    out = run_buy_and_hold(df, initial_capital=1000)
    assert "equity" in out.columns
