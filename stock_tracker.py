from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
HIGHS_PATH = ROOT / "data" / "highs.json"


def load_config(path: Path) -> tuple[list[str], float]:
    data = json.loads(path.read_text(encoding="utf-8"))
    tickers = [t.strip().upper() for t in data.get("tickers", []) if str(t).strip()]
    if not tickers:
        raise ValueError("config.json must include a non-empty 'tickers' list.")

    drop_percent = float(data.get("drop_percent", 20))
    if not 0 < drop_percent < 100:
        raise ValueError("'drop_percent' must be between 0 and 100.")

    return tickers, drop_percent


def load_highs(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("highs.json must be a JSON object of {ticker: high}.")

    highs: dict[str, float] = {}
    for key, value in raw.items():
        try:
            highs[str(key).upper()] = float(value)
        except (TypeError, ValueError):
            print(f"WARNING: ignoring bad high for {key!r}: {value!r}")

    return highs


def save_highs(path: Path, highs: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = {k: highs[k] for k in sorted(highs)}
    path.write_text(json.dumps(ordered, indent=2) + "\n", encoding="utf-8")


def fetch_price(ticker: str) -> float:
    ticker_obj = yf.Ticker(ticker)

    try:
        fast_info = ticker_obj.fast_info
    except Exception:
        fast_info = None

    if fast_info:
        last_price = fast_info.get("last_price")
        if last_price:
            return float(last_price)

    history = ticker_obj.history(period="5d")
    if history.empty:
        raise ValueError("No price data returned.")

    return float(history["Close"].iloc[-1])


def send_telegram_message(token: str | None, chat_id: str | None, text: str) -> bool:
    if not token or not chat_id:
        print("Telegram not configured; set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=15)
    if not response.ok:
        print(f"Telegram error {response.status_code}: {response.text}")

    return response.ok


def main() -> None:
    
    tickers, drop_percent = load_config(CONFIG_PATH)
    highs = load_highs(HIGHS_PATH)
    updated_highs = False
    drop_factor = 1 - (drop_percent / 100.0)
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    #send_telegram_message(token,chat_id,f"test")

    for ticker in tickers:
        try:
            price = fetch_price(ticker)
        except Exception as exc:
            print(f"{ticker}: failed to fetch price: {exc}")
            continue

        high = highs.get(ticker)
        if high is None:
            highs[ticker] = price
            updated_highs = True
            print(f"{ticker}: initial high set to {price:.2f}")
            continue

        if price > high:
            highs[ticker] = price
            updated_highs = True
            print(f"{ticker}: new high {price:.2f} (prev {high:.2f})")
            continue

        threshold = high * drop_factor
        if price <= threshold:
            message = (
                f"{ticker} is {drop_percent:.0f}% or more below its high.\n"
                f"Price: {price:.2f}\n"
                f"High: {high:.2f}\n"
                f"Time (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}"
            )
            send_telegram_message(token, chat_id, message)
            print(f"{ticker}: alert sent (price {price:.2f}, high {high:.2f})")
        else:
            print(f"{ticker}: price {price:.2f}, high {high:.2f}")

    if updated_highs:
        save_highs(HIGHS_PATH, highs)
        print(f"Saved highs to {HIGHS_PATH}")
    else:
        print("No high updates.")


if __name__ == "__main__":
    main()
