"""Smoke test script for workspace validation."""

from __future__ import annotations

import platform
import sys

import matplotlib
import numpy as np
import pandas as pd


if __name__ == "__main__":
    print("Interpreter:", sys.executable)
    print("Python     :", platform.python_version())
    print("numpy      :", np.__version__)
    print("pandas     :", pd.__version__)
    print("matplotlib :", matplotlib.__version__)
    values = np.array([1, 2, 3, 4, 5], dtype=float)
    print("Mean value :", values.mean())
