# Crypto Strategy Backtesting

Evaluate crypto trading strategies on historical BTC and ETH data and compare them against a buy-and-hold baseline.

## Scope

- Assets: BTC, ETH
- Intervals: `1d` and `1h`
- Baseline: Buy-and-hold with matching assumptions
- Strategies:
  - Moving Average Crossover
  - RSI Mean Reversion
  - Combined MA + RSI
- Metrics:
  - Total return
  - Sharpe ratio
  - Max drawdown

## Project Structure

- `src/` core logic for data handling, features, strategies, backtesting, and analysis
- `tests/` unit tests for indicators and backtest behavior
- `notebooks/` exploratory and reporting notebook
- `app/` Streamlit dashboard
- `data/raw/` raw downloaded OHLCV datasets
- `data/processed/` cleaned interval-consistent OHLCV datasets

## Quick Start

1. Create or activate your Python environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run tests:

```bash
pytest -q
```

4. Launch dashboard:

```bash
streamlit run app/streamlit_app.py
```

## Dashboard Features

- Live ingestion from Binance or CoinGecko
- Data cleaning and feature engineering (MA, RSI, MACD)
- Strategy evaluation:
  - Buy & Hold
  - MA Crossover
  - RSI Reversion
  - Combined MA + RSI
- Performance metrics and visualizations:
  - Total return, Sharpe ratio, max drawdown, trade count
  - Price and signal charts
  - Equity and drawdown curves
- CSV export and email delivery of run summary

## Email Setup (SMTP)

You can configure SMTP credentials in the dashboard form directly, or set these environment variables before launching Streamlit:

```bash
set SMTP_HOST=smtp.gmail.com
set SMTP_PORT=587
set SMTP_USER=your_email@example.com
set SMTP_PASSWORD=your_app_password
set DEFAULT_EMAIL_RECIPIENT=sadmansakib087@gmail.com
```

Optional safety allowlist (recommended in production):

```bash
set ALLOWED_RECIPIENTS=sadmansakib087@gmail.com
```

Then run:

```bash
streamlit run app/streamlit_app.py
```

## Deploy (Docker)

1. Build image:

```bash
docker build -t crypto-backtest-dashboard .
```

2. Run container with SMTP configuration:

```bash
docker run -d -p 8501:8501 ^
  -e SMTP_HOST=smtp.gmail.com ^
  -e SMTP_PORT=587 ^
  -e SMTP_USER=your_email@gmail.com ^
  -e SMTP_PASSWORD=your_app_password ^
  -e DEFAULT_EMAIL_RECIPIENT=johndoe7@gmail.com ^
  -e ALLOWED_RECIPIENTS=fsghhjtfb087@gmail.com ^
  --name crypto-backtest-dashboard ^
  crypto-backtest-dashboard
```

3. Open:

```text
http://localhost:8501
```

## Notes

- Keep timestamps in UTC across all modules.
- Avoid look-ahead bias by shifting strategy signals before applying returns.
- Use identical cost assumptions when comparing strategy vs buy-and-hold.
