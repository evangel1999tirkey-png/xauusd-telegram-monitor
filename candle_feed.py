"""Read-only Twelve Data trial connector. Entitlement must be tested per account."""
import json
import math
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

UTC = timezone.utc


def validate(payload, interval, now, symbol='XAU/USD'):
    meta = payload.get('meta', {})
    if (payload.get('status') != 'ok' or meta.get('symbol') != symbol
            or meta.get('interval') != f'{interval}min'):
        raise ValueError('feed_identity_or_access_invalid')
    rows = []
    for raw in payload.get('values', []):
        stamp = datetime.fromisoformat(raw['datetime'])
        # Requests explicitly use timezone=UTC; reject contradictory metadata.
        if meta.get('timezone') not in (None, 'UTC', 'Etc/UTC'):
            raise ValueError('timezone_unverified')
        stamp = stamp.replace(tzinfo=UTC) if stamp.tzinfo is None else stamp.astimezone(UTC)
        if stamp > now:
            raise ValueError('future_bar')
        if stamp + timedelta(minutes=interval) > now:
            continue
        values = dict(zip(('o', 'h', 'l', 'c'),
                          (float(raw[k]) for k in ('open', 'high', 'low', 'close'))))
        if not all(math.isfinite(v) and v > 0 for v in values.values()):
            raise ValueError('invalid_prices')
        if not values['l'] <= min(values['o'], values['c']) <= max(values['o'], values['c']) <= values['h']:
            raise ValueError('invalid_ohlc')
        rows.append(dict(time=stamp, **values))
    rows.sort(key=lambda b: b['time'])
    if len(rows) < 30 or any(a['time'] >= b['time'] for a, b in zip(rows, rows[1:])):
        raise ValueError('insufficient_or_duplicate_bars')
    close = rows[-1]['time'] + timedelta(minutes=interval)
    if not timedelta(0) <= now-close <= timedelta(minutes=interval+2):
        raise ValueError('stale_bars')
    if any(b['time']-a['time'] != timedelta(minutes=interval)
           for a,b in zip(rows[-12:], rows[-11:])):
        raise ValueError('recent_gap')
    return rows, close


def fetch(interval, now, size=80, symbol='XAU/USD'):
    key = os.environ.get('TWELVE_DATA_API_KEY')
    if not key:
        raise ValueError('data_not_configured')
    query = urllib.parse.urlencode(dict(symbol=symbol, interval=f'{interval}min',
                                       outputsize=size, timezone='UTC', apikey=key))
    # Never log this URL or any exception text: the query contains a credential.
    with urllib.request.urlopen('https://api.twelvedata.com/time_series?'+query, timeout=15) as response:
        payload = json.load(response)
    return validate(payload, interval, datetime.now(UTC), symbol)


def aggregate(five, interval, now):
    groups = {}
    for bar in five:
        seconds = int(bar['time'].timestamp())
        start = datetime.fromtimestamp(seconds // (interval*60) * (interval*60), UTC)
        groups.setdefault(start, []).append(bar)
    result = []
    for start, bars in sorted(groups.items()):
        expected = [start+timedelta(minutes=i) for i in range(0, interval, 5)]
        if [b['time'] for b in bars] != expected or start+timedelta(minutes=interval) > now:
            continue
        result.append(dict(time=start, o=bars[0]['o'], h=max(b['h'] for b in bars),
                           l=min(b['l'] for b in bars), c=bars[-1]['c']))
    if len(result) < 30 or now-(result[-1]['time']+timedelta(minutes=interval)) > timedelta(minutes=interval+2):
        raise ValueError('aggregate_insufficient_or_stale')
    return result, result[-1]['time']+timedelta(minutes=interval)
