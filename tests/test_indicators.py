"""Indicator smoke tests."""

import pandas as pd

from src.features.indicators import moving_average, rsi, macd



def test_moving_average_length_matches_input() -> None:
    series = pd.Series([1, 2, 3, 4, 5])
    out = moving_average(series, window=3)
    assert len(out) == len(series)



def test_rsi_output_length_matches_input() -> None:
    series = pd.Series([1, 2, 1, 2, 3, 2, 3, 4, 3, 4, 5, 4, 5, 6, 5])
    out = rsi(series, window=14)
    assert len(out) == len(series)



def test_macd_contains_expected_columns() -> None:
    series = pd.Series(range(1, 40))
    out = macd(series)
    assert set(out.columns) == {"macd", "signal", "hist"}
