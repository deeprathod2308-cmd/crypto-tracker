import argparse

import pytest

from crypto_tracker import (average_price, check_alerts, parse_alert, trend,
                            volatility_pct)


def test_average():
    assert average_price([100, 200, 300]) == 200


def test_volatility_zero_for_flat_prices():
    assert volatility_pct([100, 100, 100]) == 0


def test_volatility_positive():
    assert volatility_pct([90, 100, 110]) > 0


def test_trend_up_down_sideways():
    assert trend([100, 105])[0] == "UP"
    assert trend([100, 95])[0] == "DOWN"
    assert trend([100, 100.01])[0] == "SIDEWAYS"


def test_parse_alert_valid():
    assert parse_alert("btcusdt:above:70000") == ("BTCUSDT", "above", 70000.0)


def test_parse_alert_invalid():
    with pytest.raises(argparse.ArgumentTypeError):
        parse_alert("BTCUSDT:sideways:5")


def test_check_alerts():
    alerts = [("BTCUSDT", "above", 70000.0)]
    assert check_alerts("BTCUSDT", 71000, alerts)
    assert not check_alerts("BTCUSDT", 69000, alerts)
    assert not check_alerts("ETHUSDT", 71000, alerts)
