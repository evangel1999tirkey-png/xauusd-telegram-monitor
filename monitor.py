"""Free cloud data/status monitor; missing evidence never becomes a market signal."""
import json
import math
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from signal_rules import multi_timeframe_evidence, confirmed_bias
from public_quote import fetch_quote
from candle_feed import fetch as fetch_trial, aggregate
from news_context import context as news_context, dollar_proxy

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
    granularity = {5: 'M5', 15: 'M15', 60: 'H1', 240: 'H4'}[interval]
    url = ('https://api-fxpractice.oanda.com/v3/instruments/XAU_USD/candles'
           f'?granularity={granularity}&count=60&price=M')
    result = read_json(url, {'Authorization': 'Bearer ' + token})
    if result.get('instrument') != 'XAU_USD' or result.get('granularity') != granularity:
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
    label = 'DATA UNAVAILABLE — XAU/USD'
    try:
        quote, quote_stamp = fetch_quote(now)
        public = (f'Public gold cross-check: {quote:.2f} USD; source time '
                  + quote_stamp.astimezone(IST).strftime('%d %b %H:%M:%S IST')
                  + '. Not OANDA execution price or candle/spread confirmation.\n'
                  + 'https://gold-api.com/docs\n')
    except Exception:
        public = 'Public gold cross-check unavailable or stale.\n'
    if not (os.environ.get('OANDA_PRACTICE_TOKEN') or os.environ.get('TWELVE_DATA_API_KEY')):
        reason = 'Gold candle feed not connected; current 5m/15m structure unverified.'
        freshness = 'Data freshness: unavailable.'
    else:
        try:
            if os.environ.get('TWELVE_DATA_API_KEY'):
                five, five_close = fetch_trial(5, now, size=2000)
                fifteen, fifteen_close = aggregate(five, 15, now)
                hourly, hour_close = aggregate(five, 60, now)
                four_hour, four_close = aggregate(five, 240, now)
                one, one_close = fetch_trial(1, datetime.now(UTC), size=80)
                source = 'Twelve Data aggregate; not broker execution prices'
            else:
                five, five_close = candles(5, now)
                fifteen, fifteen_close = candles(15, now)
                hourly, hour_close = candles(60, now)
                four_hour, four_close = candles(240, now)
                source = 'OANDA practice midpoint feed'
            evidence = multi_timeframe_evidence(five, fifteen, hourly, four_hour)
            # News, market reaction and spread verification are not connected.
            # Even a strong technical candidate cannot enable a combined signal.
            assert confirmed_bias(evidence) == 'NEUTRAL'
            label = 'CONFIRMATION INCOMPLETE — XAU/USD'
            reason = ('Technical structure: ' + evidence.reason
                      + ' Combined directional confirmation remains unverified.')
            freshness = ('Completed candles: 5m ' + five_close.astimezone(IST).strftime('%H:%M IST')
                         + '; 15m ' + fifteen_close.astimezone(IST).strftime('%H:%M IST')
                         + '; 1h ' + hour_close.astimezone(IST).strftime('%H:%M IST')
                         + '; 4h ' + four_close.astimezone(IST).strftime('%H:%M IST')
                         + '. Source: ' + source + '.')
            if os.environ.get('TWELVE_DATA_API_KEY'):
                freshness += ' 1m completed through ' + one_close.astimezone(IST).strftime('%H:%M IST') + '; entry confirmation still conditional.'
        except Exception:
            # Never log API exception strings: they can contain credential URLs.
            reason = 'Gold data unavailable, invalid or stale; current structure unverified.'
            freshness = 'Freshness verification failed.'
    context_lines=compact_context(news_context(now))
    return (f'{label}\nCheck: {check}\n{reason}\n{freshness}\n'
            + public + dollar_proxy(now) + '\n' + context_lines + '\n'
            'Missing: verified actual/consensus/revision analysis, live Treasury reaction, '
            'XM execution-cost and 1m entry checks. Local XM demo access does not run in this cloud job.\n'
            'Confidence: direction unverified. Wait for completed 5m/15m break and held retest '
            'or failed reclaim; use 1m for entry confirmation only.\n'
            'Free monitoring status, not a confirmed BUY/SELL or a verified neutral market.')


def compact_context(context):
    prefixes=('Calendar checked now:', 'Economic calendar unavailable', 'WAIT:',
              'Next listed USD event:', 'No later USD event', 'US 2y', 'Official Michigan')
    lines=[line for line in context.splitlines() if line.startswith(prefixes)]
    unavailable=sum('release feed unavailable' in line or 'release feed unavailable or' in line
                    for line in context.splitlines())
    if unavailable:
        lines.append(f'Official release feeds unavailable/unverified: {unavailable}.')
    lines.append('https://www.forexfactory.com/calendar')
    return '\n'.join(lines)


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
        if not test:
            # Public market evidence only; no identifiers, keys or request URLs.
            print(message)
        print('Telegram delivery confirmed.')
        return 0
    except Exception:
        print('Telegram delivery failed. Check GitHub secrets and service access; no secret details printed.')
        return 1


if __name__ == '__main__':
    sys.exit(main())