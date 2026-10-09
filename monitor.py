"""Read-only cloud monitor. No order endpoints and no paid AI calls.

This initial version verifies candles but has no verified news-analysis feed.
It deliberately reports NEUTRAL rather than treating a technical move as a
news-confirmed BUY/SELL. Deployment is not complete until live data is tested.
"""
import json
import math
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from signal_rules import technical_evidence, confirmed_bias

UTC = timezone.utc
IST = ZoneInfo('Asia/Kolkata')
NY = ZoneInfo('America/New_York')


def trading_session(now):
    local = now.astimezone(NY)
    day, hour = local.weekday(), local.hour
    if day == 5 or (day == 6 and hour < 18) or (day == 4 and hour >= 17):
        return False
    # Conservative one-hour daily maintenance exclusion; holidays are also
    # guarded by candle freshness rather than pretending the calendar is live.
    return hour != 17


def read_json(url, headers=None, body=None):
    req = urllib.request.Request(url, headers=headers or {}, data=body)
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def candles(interval, now):
    token = os.environ.get('OANDA_PRACTICE_TOKEN')
    if not token:
        raise ValueError('data_not_configured')
    # Practice only: this token is never used against a live trading endpoint.
    url = ('https://api-fxpractice.oanda.com/v3/instruments/XAU_USD/candles'
           f'?granularity=M{interval}&count=60&price=M')
    result = read_json(url, {'Authorization': 'Bearer ' + token})
    if result.get('instrument') != 'XAU_USD' or result.get('granularity') != f'M{interval}':
        raise ValueError('wrong_instrument')
    rows = []
    for candle in result.get('candles', []):
        if not candle.get('complete'):
            continue
        # OANDA timestamps may have nine fractional digits.
        stamp = datetime.fromisoformat(candle['time'].replace('Z', '+00:00'))
        mid = candle['mid']
        values = {name: float(mid[name]) for name in ('o', 'h', 'l', 'c')}
        if not all(math.isfinite(v) and v > 0 for v in values.values()):
            raise ValueError('invalid_price')
        if not (values['l'] <= min(values['o'], values['c']) <= max(values['o'], values['c']) <= values['h']):
            raise ValueError('invalid_candle')
        rows.append({'time': stamp, **values})
    if len(rows) < 30 or any(a['time'] >= b['time'] for a, b in zip(rows, rows[1:])):
        raise ValueError('insufficient_data')
    close_time = rows[-1]['time'] + timedelta(minutes=interval)
    if not timedelta(0) <= now - close_time <= timedelta(minutes=interval + 2):
        raise ValueError('stale_data')
    if any(b['time'] - a['time'] != timedelta(minutes=interval) for a, b in zip(rows[-12:], rows[-11:])):
        raise ValueError('gapped_data')
    return rows, close_time


def status(now):
    check = now.astimezone(IST).strftime('%d %b %Y, %H:%M IST')
    if not os.environ.get('OANDA_PRACTICE_TOKEN'):
        reason = 'Gold candle feed not connected; current 5m/15m structure unverified.'
        freshness = 'Data freshness: unavailable.'
    else:
        try:
            five, five_close = candles(5, now)
            fifteen, fifteen_close = candles(15, now)
            evidence = technical_evidence(five, fifteen)
            # News, market reaction and spread verification are not connected.
            # Even a strong technical candidate cannot enable a combined signal.
            assert confirmed_bias(evidence) == 'NEUTRAL'
            reason = ('Technical evidence: ' + evidence.reason
                      + ' Combined bias unconfirmed: news/reaction/spread feeds not connected.')
            freshness = ('Completed candles: 5m ' + five_close.astimezone(IST).strftime('%H:%M IST')
                         + '; 15m ' + fifteen_close.astimezone(IST).strftime('%H:%M IST')
                         + '. Source: OANDA practice midpoint feed.')
        except Exception:
            # Never log API exception strings: they can contain credential URLs.
            reason = 'Gold data unavailable, invalid or stale; current structure unverified.'
            freshness = 'Freshness verification failed.'
    return (f'NEUTRAL — XAU/USD\nCheck: {check}\n{reason}\n{freshness}\n'
            'Directional confidence: low. News/source publication time: unverified.\n'
            'Wait for fresh 5m/15m range break and holding retest: higher low for bullish '
            'confirmation, or failed reclaim/lower high for bearish confirmation. '
            'Use 1m only for entry confirmation. Conditional bias, not an order.\n'
            'Cloud setup is in verification mode; it does not yet reproduce the news monitor.')


def send(message):
    token, chat = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat:
        raise ValueError('Telegram configuration missing')
    body = json.dumps({'chat_id': chat, 'text': message, 'disable_notification': False,
                       'link_preview_options': {'is_disabled': True}}).encode('utf-8')
    result = read_json('https://api.telegram.org/bot' + token + '/sendMessage',
                       {'Content-Type': 'application/json'}, body)
    if not result.get('ok'):
        raise ValueError('Telegram did not confirm delivery')


def main():
    now = datetime.now(UTC)
    test = os.environ.get('TEST_DELIVERY') == '1'
    if not test and not trading_session(now):
        print('Outside the monitoring session; no message sent.')
        return 0
    message = ('TEST — Cloud Telegram connection works. This is not a trading signal. '
               'Cloud news and gold-data verification is still required.') if test else status(now)
    try:
        send(message)
        print('Telegram delivery confirmed.')
        return 0
    except Exception:
        print('Telegram delivery failed. Check GitHub secrets and service access; no secret details printed.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
