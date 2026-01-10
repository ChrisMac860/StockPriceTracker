# StockPriceTracker

Tracks stock prices daily and sends a Telegram alert when a price drops 20% or more
from its recorded high.

## How it works
1. Load tickers from `config.json`.
2. Fetch the latest price for each ticker using `yfinance`.
3. If the current price is a new high, update `data/highs.json`.
4. If the price is 20% or more below the high, send a Telegram alert.

## Configuration
- Edit `config.json` to set your 9 tickers and the drop percentage.
- `data/highs.json` stores the current high for each ticker.

Example `config.json`:

```json
{
  "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX", "JPM"],
  "drop_percent": 20
}
```

## Telegram setup
Create a bot with @BotFather, then set these environment variables:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

For GitHub Actions, add them as repository secrets.

## Run locally
```bash
pip install -r requirements.txt
python stock_tracker.py
```

## GitHub Actions
The workflow runs at US market open and close on weekdays:
- 14:30 UTC
- 21:00 UTC

These match standard time (EST). During daylight saving time, you'll be one hour
late; adjust the cron in `.github/workflows/daily.yml` if you want DST
alignment.

The workflow commits updates to `data/highs.json` so the next run can reuse
the previous highs.
