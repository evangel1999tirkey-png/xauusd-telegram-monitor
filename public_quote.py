"""Free public gold quote cross-check; never substitutes for OHLC or spread."""
import json
import math
import urllib.request
from datetime import datetime, timedelta

QUOTE_URL = 'https://api.gold-api.com/price/XAU/USD'


def validate_quote(payload, now):
    if payload.get('symbol') != 'XAU' or payload.get('currency') != 'USD':
        raise ValueError('wrong_symbol_or_currency')
    price = float(payload['price'])
    if not math.isfinite(price) or price <= 0:
        raise ValueError('invalid_quote')
    stamp = datetime.fromisoformat(payload['updatedAt'].replace('Z', '+00:00'))
    if stamp.tzinfo is None or not timedelta(0) <= now - stamp <= timedelta(seconds=90):
        raise ValueError('stale_or_future_quote')
    return price, stamp


def fetch_quote(now):
    # One request per scheduled run; exceeds the provider's 30-second cache.
    with urllib.request.urlopen(QUOTE_URL, timeout=10) as response:
        payload = json.load(response)
    return validate_quote(payload, now)
