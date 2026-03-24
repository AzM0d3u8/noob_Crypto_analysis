"""Plot helper placeholders."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd



def plot_equity_curve(equity: pd.Series, title: str = "Equity Curve") -> None:
    """Plot a simple equity curve."""
    fig, ax = plt.subplots(figsize=(10, 4))
    equity.plot(ax=ax)
    ax.set_title(title)
    ax.set_ylabel("Portfolio Value")
    plt.tight_layout()
