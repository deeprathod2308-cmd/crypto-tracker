"""Real-Time Cryptocurrency Tracker & Data Analyzer (CLI).

Example:
    python crypto_tracker.py -s BTCUSDT ETHUSDT -i 5 -w 20 \
        -a BTCUSDT:above:70000 -a ETHUSDT:below:2000
"""
import argparse
import logging
import statistics
import time
from collections import defaultdict, deque

import requests

API_URL = "https://api.binance.com/api/v3/ticker/price"
TREND_THRESHOLD_PCT = 0.1  # change smaller than this = SIDEWAYS


# ---------- Analysis ----------
def average_price(prices):
    return statistics.mean(prices)


def volatility_pct(prices):
    """Standard deviation as a percentage of the mean price."""
    if len(prices) < 2:
        return 0.0
    return statistics.pstdev(prices) / statistics.mean(prices) * 100


def trend(prices):
    """Compare first and last price in the window."""
    if len(prices) < 2 or prices[0] == 0:
        return "N/A", 0.0
    change = (prices[-1] - prices[0]) / prices[0] * 100
    if change > TREND_THRESHOLD_PCT:
        return "UP", change
    if change < -TREND_THRESHOLD_PCT:
        return "DOWN", change
    return "SIDEWAYS", change


# ---------- Alerts ----------
def parse_alert(text):
    """'BTCUSDT:above:70000' -> ('BTCUSDT', 'above', 70000.0)"""
    try:
        symbol, direction, limit = text.split(":")
        direction = direction.lower()
        if direction not in ("above", "below"):
            raise ValueError
        return symbol.upper(), direction, float(limit)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid alert '{text}'. Use SYMBOL:above|below:PRICE"
        )


def check_alerts(symbol, price, alerts):
    triggered = []
    for sym, direction, limit in alerts:
        if sym != symbol:
            continue
        if (direction == "above" and price > limit) or (
            direction == "below" and price < limit
        ):
            triggered.append(
                f"ALERT: {symbol} is {direction} {limit:,.2f} (now {price:,.2f})"
            )
    return triggered


# ---------- Data fetching ----------
def fetch_price(symbol, session):
    resp = session.get(API_URL, params={"symbol": symbol}, timeout=10)
    resp.raise_for_status()
    return float(resp.json()["price"])


# ---------- Main loop ----------
def setup_logging(log_file):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )


def run(symbols, interval, window, alerts, iterations=None):
    history = defaultdict(lambda: deque(maxlen=window))
    session = requests.Session()
    count = 0
    while iterations is None or count < iterations:
        for symbol in symbols:
            try:
                price = fetch_price(symbol, session)
            except (requests.RequestException, KeyError, ValueError) as exc:
                logging.error("%s fetch failed: %s", symbol, exc)
                continue
            history[symbol].append(price)
            prices = list(history[symbol])
            direction, change = trend(prices)
            logging.info(
                "%s price=%.2f avg=%.2f volatility=%.3f%% trend=%s (%+.2f%%)",
                symbol, price, average_price(prices),
                volatility_pct(prices), direction, change,
            )
            for msg in check_alerts(symbol, price, alerts):
                logging.warning(msg)
        count += 1
        if iterations is None or count < iterations:
            time.sleep(interval)


def main():
    p = argparse.ArgumentParser(description="Real-time crypto tracker & analyzer")
    p.add_argument("-s", "--symbols", nargs="+", default=["BTCUSDT"],
                   help="Binance symbols, e.g. BTCUSDT ETHUSDT")
    p.add_argument("-i", "--interval", type=int, default=10,
                   help="Seconds between price checks")
    p.add_argument("-w", "--window", type=int, default=20,
                   help="Number of recent prices used for analysis")
    p.add_argument("-a", "--alert", action="append", default=[],
                   type=parse_alert, help="SYMBOL:above|below:PRICE (repeatable)")
    p.add_argument("-n", "--iterations", type=int, default=None,
                   help="Stop after N rounds (default: run until Ctrl+C)")
    p.add_argument("-l", "--log-file", default="tracker.log")
    args = p.parse_args()

    setup_logging(args.log_file)
    symbols = [s.upper() for s in args.symbols]
    try:
        run(symbols, args.interval, args.window, args.alert, args.iterations)
    except KeyboardInterrupt:
        logging.info("Tracker stopped by user.")


if __name__ == "__main__":
    main()
