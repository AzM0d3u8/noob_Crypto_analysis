"""Interactive dashboard for crypto strategy evaluation and email reporting."""

from __future__ import annotations

import io
import os
import smtplib
from datetime import date, datetime, time, timedelta, timezone
from email.message import EmailMessage

import numpy as np
import pandas as pd
import streamlit as st

from src.analysis.metrics import max_drawdown, sharpe_ratio, total_return
from src.backtest.baseline import run_buy_and_hold
from src.backtest.engine import run_backtest
from src.data_pipeline.cleaning import clean_ohlcv
from src.data_sources.binance import fetch_ohlcv as fetch_binance_ohlcv
from src.data_sources.coingecko import fetch_ohlcv as fetch_coingecko_ohlcv
from src.features.indicators import macd, moving_average, rsi
from src.strategies.combined import generate_signals as combined_signals
from src.strategies.ma_crossover import generate_signals as ma_signals
from src.strategies.rsi_reversion import generate_signals as rsi_signals


st.set_page_config(page_title="Crypto Strategy Backtest", layout="wide")


def _to_datetime_utc(day: date, end_of_day: bool = False) -> datetime:
	if end_of_day:
		return datetime.combine(day, time.max, tzinfo=timezone.utc)
	return datetime.combine(day, time.min, tzinfo=timezone.utc)


@st.cache_data(ttl=900)
def load_market_data(
	provider: str,
	symbol: str,
	interval: str,
	start_dt: datetime,
	end_dt: datetime,
) -> pd.DataFrame:
	if provider == "Binance":
		data = fetch_binance_ohlcv(symbol=symbol, interval=interval, start=start_dt, end=end_dt)
	else:
		data = fetch_coingecko_ohlcv(symbol=symbol, interval=interval, start=start_dt, end=end_dt)
	return clean_ohlcv(data)


def build_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
	frame = df.copy()
	frame["returns"] = frame["close"].pct_change()
	frame["ma20"] = moving_average(frame["close"], 20)
	frame["ma50"] = moving_average(frame["close"], 50)
	frame["ma200"] = moving_average(frame["close"], 200)
	frame["rsi14"] = rsi(frame["close"], 14)
	macd_frame = macd(frame["close"])
	frame = frame.join(macd_frame)
	return frame


def evaluate_strategies(df: pd.DataFrame, initial_capital: float, interval: str) -> dict[str, dict[str, pd.DataFrame | pd.Series]]:
	ma = ma_signals(df)
	rsi_sig = rsi_signals(df)
	combo = combined_signals(df)
	baseline = pd.Series(1.0, index=df.index)

	results: dict[str, dict[str, pd.DataFrame | pd.Series]] = {}
	signals = {
		"Buy & Hold": baseline,
		"MA Crossover": ma,
		"RSI Reversion": rsi_sig,
		"Combined": combo,
	}

	for name, signal in signals.items():
		if name == "Buy & Hold":
			bt = run_buy_and_hold(df, initial_capital=initial_capital)
			strategy_returns = bt["returns"]
		else:
			bt = run_backtest(df, signal=signal, initial_capital=initial_capital)
			strategy_returns = bt["strategy_returns"]

		ppy = 24 * 365 if interval == "1h" else 365
		summary = {
			"Total Return": total_return(bt["equity"]),
			"Sharpe": sharpe_ratio(strategy_returns.fillna(0), periods_per_year=ppy),
			"Max Drawdown": max_drawdown(bt["equity"]),
			"Trades": int(signal.diff().abs().fillna(0).sum()) if name != "Buy & Hold" else 1,
			"Final Equity": float(bt["equity"].iloc[-1]) if not bt.empty else initial_capital,
		}
		results[name] = {"signal": signal, "backtest": bt, "summary": pd.Series(summary)}

	return results


def build_summary_table(results: dict[str, dict[str, pd.DataFrame | pd.Series]]) -> pd.DataFrame:
	rows = []
	for strategy, payload in results.items():
		s = payload["summary"]
		rows.append(
			{
				"Strategy": strategy,
				"Total Return": s["Total Return"],
				"Sharpe": s["Sharpe"],
				"Max Drawdown": s["Max Drawdown"],
				"Trades": int(s["Trades"]),
				"Final Equity": s["Final Equity"],
			}
		)
	table = pd.DataFrame(rows).sort_values("Sharpe", ascending=False).reset_index(drop=True)
	return table


def drawdown_series(equity: pd.Series) -> pd.Series:
	running_max = equity.cummax()
	return equity / running_max - 1


def summary_text(symbol: str, interval: str, table: pd.DataFrame) -> str:
	winner = table.iloc[0]
	buy_hold = table.loc[table["Strategy"] == "Buy & Hold"].iloc[0]
	outperf = winner["Total Return"] - buy_hold["Total Return"]
	return (
		f"Top strategy for {symbol} ({interval}) is {winner['Strategy']} with "
		f"total return {winner['Total Return']:.2%} and Sharpe {winner['Sharpe']:.2f}. "
		f"Relative to Buy & Hold, return delta is {outperf:.2%}."
	)


def send_email_report(
	smtp_host: str,
	smtp_port: int,
	smtp_user: str,
	smtp_password: str,
	recipients: list[str],
	subject: str,
	body: str,
	csv_bytes: bytes,
) -> None:
	msg = EmailMessage()
	msg["From"] = smtp_user
	msg["To"] = ", ".join(recipients)
	msg["Subject"] = subject
	msg.set_content(body)
	msg.add_attachment(csv_bytes, maintype="text", subtype="csv", filename="strategy_summary.csv")

	with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
		server.starttls()
		server.login(smtp_user, smtp_password)
		server.send_message(msg)


st.title("Crypto Strategy Evaluation Dashboard")
st.caption("Live data ingestion, strategy backtesting, benchmark comparison, and email reporting")

with st.sidebar:
	st.header("Run Controls")
	provider = st.selectbox("Data Provider", ["Binance", "CoinGecko"], index=0)
	symbol = st.selectbox("Asset", ["BTC", "ETH"], index=0)
	interval = st.selectbox("Interval", ["1d", "1h"], index=0)

	default_end = datetime.now(timezone.utc).date()
	default_start = default_end - timedelta(days=365)
	start_day = st.date_input("Start date (UTC)", value=default_start)
	end_day = st.date_input("End date (UTC)", value=default_end)
	initial_capital = st.number_input("Initial capital", min_value=100.0, value=1000.0, step=100.0)

	run_clicked = st.button("Run Evaluation", type="primary")

if "state" not in st.session_state:
	st.session_state["state"] = {}

if run_clicked:
	start_dt = _to_datetime_utc(start_day)
	end_dt = _to_datetime_utc(end_day, end_of_day=True)
	if start_dt >= end_dt:
		st.error("Start date must be earlier than end date.")
	else:
		with st.spinner("Loading live market data and running backtests..."):
			market = load_market_data(
				provider=provider,
				symbol=symbol,
				interval=interval,
				start_dt=start_dt,
				end_dt=end_dt,
			)

			if market.empty:
				st.warning("No data returned for the selected inputs.")
			else:
				feature_frame = build_feature_frame(market)
				results = evaluate_strategies(feature_frame, initial_capital=initial_capital, interval=interval)
				table = build_summary_table(results)
				run_note = summary_text(symbol=symbol, interval=interval, table=table)

				st.session_state["state"] = {
					"provider": provider,
					"symbol": symbol,
					"interval": interval,
					"start": start_dt,
					"end": end_dt,
					"market": market,
					"features": feature_frame,
					"results": results,
					"summary": table,
					"insight": run_note,
				}

state = st.session_state.get("state", {})
if not state:
	st.info("Select controls and click Run Evaluation to generate the full dashboard.")
	st.stop()

market = state["market"]
features = state["features"]
results = state["results"]
summary = state["summary"]

st.subheader("Performance Snapshot")
metric_cols = st.columns(4)
metric_cols[0].metric("Provider", state["provider"])
metric_cols[1].metric("Asset", state["symbol"])
metric_cols[2].metric("Interval", state["interval"])
metric_cols[3].metric("Rows", f"{len(market):,}")

st.markdown("### Strategy Comparison")
styled = summary.copy()
for col in ["Total Return", "Max Drawdown"]:
	styled[col] = styled[col].map(lambda x: f"{x:.2%}")
styled["Sharpe"] = styled["Sharpe"].map(lambda x: f"{x:.2f}")
styled["Final Equity"] = styled["Final Equity"].map(lambda x: f"${x:,.2f}")
st.dataframe(styled, use_container_width=True, hide_index=True)

st.info(state["insight"])

st.markdown("### Price and Strategy Signals")
selected_strategy = st.selectbox("Choose strategy for signal chart", ["MA Crossover", "RSI Reversion", "Combined"], index=0)
signal = results[selected_strategy]["signal"]
signal_shift = signal.diff().fillna(0)
entries = market.loc[signal_shift > 0, ["timestamp", "close"]]
exits = market.loc[signal_shift < 0, ["timestamp", "close"]]

chart_df = features[["timestamp", "close", "ma20", "ma50", "ma200"]].set_index("timestamp")
st.line_chart(chart_df, height=340)

signal_plot = pd.DataFrame(index=market["timestamp"])
signal_plot["price"] = market["close"].values
signal_plot["entry"] = np.nan
signal_plot["exit"] = np.nan
if not entries.empty:
	signal_plot.loc[entries["timestamp"], "entry"] = entries["close"].values
if not exits.empty:
	signal_plot.loc[exits["timestamp"], "exit"] = exits["close"].values
st.caption("Entry and exit markers for selected strategy")
st.line_chart(signal_plot, height=260)

st.markdown("### Equity Curves")
equity_curves = pd.DataFrame(index=market["timestamp"])
for name, payload in results.items():
	bt = payload["backtest"]
	equity_curves[name] = bt["equity"].values
st.line_chart(equity_curves, height=360)

st.markdown("### Drawdown Curves")
drawdown_curves = pd.DataFrame(index=market["timestamp"])
for name, payload in results.items():
	bt = payload["backtest"]
	drawdown_curves[name] = drawdown_series(bt["equity"]).values
st.line_chart(drawdown_curves, height=260)

st.markdown("### Data Quality and EDA")
col_a, col_b = st.columns(2)
with col_a:
	st.write("Data sample")
	st.dataframe(market.head(10), use_container_width=True)
with col_b:
	st.write("Feature sample")
	st.dataframe(features[["timestamp", "returns", "rsi14", "macd", "signal", "hist"]].tail(10), use_container_width=True)

vol_30 = features["returns"].rolling(30).std()
eda = pd.DataFrame({
	"timestamp": features["timestamp"],
	"returns": features["returns"],
	"volatility_30": vol_30,
})
st.line_chart(eda.set_index("timestamp")[["returns", "volatility_30"]], height=250)

summary_csv = summary.to_csv(index=False).encode("utf-8")
st.download_button(
	label="Download Summary CSV",
	data=summary_csv,
	file_name=f"{state['symbol'].lower()}_{state['interval']}_strategy_summary.csv",
	mime="text/csv",
)

st.markdown("## Email Results")
st.caption("Use SMTP credentials from environment variables or fill the form below.")

default_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
default_port = int(os.getenv("SMTP_PORT", "587"))
default_user = os.getenv("SMTP_USER", "")
default_pass = os.getenv("SMTP_PASSWORD", "")
default_recipient = os.getenv("DEFAULT_EMAIL_RECIPIENT", "sadmansakib087@gmail.com")
allowed_recipients_raw = os.getenv("ALLOWED_RECIPIENTS", "").strip()
allowed_recipients = {item.strip().lower() for item in allowed_recipients_raw.split(",") if item.strip()}

with st.form("email_form"):
	smtp_host = st.text_input("SMTP host", value=default_host)
	smtp_port = st.number_input("SMTP port", min_value=1, max_value=65535, value=default_port)
	smtp_user = st.text_input("SMTP user", value=default_user)
	smtp_password = st.text_input("SMTP password", value=default_pass, type="password")
	recipients_raw = st.text_input("Recipients (comma separated)", value=default_recipient)
	custom_subject = st.text_input("Subject", value=f"Crypto Strategy Results - {state['symbol']} {state['interval']}")

	submitted = st.form_submit_button("Send Email")

if submitted:
	recipients = [token.strip() for token in recipients_raw.split(",") if token.strip()]
	if not recipients and default_recipient:
		recipients = [default_recipient]
	if not recipients:
		st.error("Please provide at least one recipient email.")
	elif allowed_recipients and any(email.lower() not in allowed_recipients for email in recipients):
		st.error("One or more recipients are not allowed by ALLOWED_RECIPIENTS.")
	elif not smtp_user or not smtp_password:
		st.error("SMTP user and password are required.")
	else:
		try:
			email_body = (
				f"Dashboard run: {state['provider']} {state['symbol']} {state['interval']}\n"
				f"Window: {state['start'].date()} to {state['end'].date()} UTC\n\n"
				f"{state['insight']}\n\n"
				f"Summary table:\n{summary.to_string(index=False)}\n"
			)
			send_email_report(
				smtp_host=smtp_host,
				smtp_port=int(smtp_port),
				smtp_user=smtp_user,
				smtp_password=smtp_password,
				recipients=recipients,
				subject=custom_subject,
				body=email_body,
				csv_bytes=summary_csv,
			)
			st.success("Email sent successfully.")
		except Exception as exc:  # pragma: no cover - runtime delivery depends on SMTP provider.
			st.error(f"Failed to send email: {exc}")
