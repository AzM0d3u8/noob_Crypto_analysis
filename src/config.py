"""Project configuration for symbols, intervals, and backtest assumptions."""

from dataclasses import dataclass, field


@dataclass
class BacktestConfig:
    symbols: list[str] = field(default_factory=lambda: ["BTC", "ETH"])
    intervals: list[str] = field(default_factory=lambda: ["1d", "1h"])
    initial_capital: float = 1000.0
    fee_bps: float = 10.0
    slippage_bps: float = 5.0
