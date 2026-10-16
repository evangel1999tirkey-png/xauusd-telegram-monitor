"""Cloud 5m technical lean; Twelve Data reference feed, no broker connection."""
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from candle_feed import fetch
from signal_rules import context_direction
from direction_performance import add_alert, update_outcomes
from direction_filter import review as review_filter
from shadow_fifteen import collect_after_delivery

UTC = timezone.utc
IST = ZoneInfo('Asia/Kolkata')
NY = ZoneInfo('America/New_York')
STATE_PATH = 'cloud-direction-state.json'
ALERT_WINDOW = 'IST_0900_1500_v1'


def alert_window_open(now):
    local = now.astimezone(IST)
    return 9 <= local.hour < 15


def already_notified(state, direction, checked):
    return (state.get('alert_window') == ALERT_WINDOW
            and state.get('session_date_ist') == checked.astimezone(IST).date().isoformat()
            and state.get('last_notified') == direction)


def session_open(now):
    local = now.astimezone(NY)
    day, hour = local.weekday(), local.hour
    return not (day == 5 or (day == 6 and hour < 18)
                or (day == 4 and hour >= 17) or hour == 17)


def candidate(rows, close, now):
    if not timedelta(0) <= now - close <= timedelta(seconds=330):
        return None
    return {'BUY': 'UP', 'SELL': 'DOWN'}.get(context_direction(rows))


def request_json(url, body=None, headers=None):
    request = urllib.request.Request(url, data=body, headers=headers or {})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def state_api(body=None):
    repo = os.environ['GITHUB_REPOSITORY']
    if repo != 'evangel1999tirkey-png/xauusd-telegram-monitor':
        raise ValueError('wrong_repository')
    headers = {'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'],
               'Accept': 'application/vnd.github+json',
               'Content-Type': 'application/json',
               'X-GitHub-Api-Version': '2022-11-28'}
    url = 'https://api.github.com/repos/' + repo + '/contents/' + STATE_PATH
    if body is None:
        url += '?ref=main'
    return request_json(url, body, headers)


def read_state():
    try:
        result = state_api()
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return {}, None
        raise
    state = json.loads(base64.b64decode(result['content']))
    if state.get('last_notified') not in ('UP', 'DOWN'):
        raise ValueError('invalid_notification_state')
    return state, result['sha']


def write_state(state, sha):
    body = dict(message='Record cloud direction outcomes [skip ci]', branch='main',
                content=base64.b64encode(json.dumps(state, indent=2).encode()).decode())
    if sha:
        body['sha'] = sha
    # Contents updates require PUT, not the default POST used for Telegram.
    repo = os.environ['GITHUB_REPOSITORY']
    url = 'https://api.github.com/repos/' + repo + '/contents/' + STATE_PATH
    request = urllib.request.Request(url, method='PUT', data=json.dumps(body).encode(),
        headers={'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'],
                 'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json',
                 'X-GitHub-Api-Version': '2022-11-28'})
    with urllib.request.urlopen(request, timeout=20) as response:
        json.load(response)


def send(message):
    token, chat = os.environ['TELEGRAM_BOT_TOKEN'], os.environ['TELEGRAM_CHAT_ID']
    if not token or not chat:
        raise ValueError('missing_telegram_configuration')
    body = json.dumps(dict(chat_id=chat, text=message, disable_notification=False)).encode()
    result = request_json('https://api.telegram.org/bot' + token + '/sendMessage', body,
                          {'Content-Type': 'application/json'})
    if result.get('ok') is not True:
        raise ValueError('delivery_not_confirmed')


def run(now, load=read_state, save=write_state, deliver=send, feed=fetch, shadow_feed=None):
    if not session_open(now):
        print('Market session excluded; no notification.')
        return 0
    # A failed state read blocks sends: do not treat it as an empty history.
    try:
        state, sha = load()
    except Exception:
        print('Notification state unavailable; no notification.')
        return 1
    # Outside the user's window, only finish outcomes of earlier alerts.
    pending = any(any(str(m) not in r.get('outcomes', {}) for m in (5, 10, 15))
                  for r in state.get('performance', {}).get('alerts', []))
    if not alert_window_open(now) and not pending:
        print('Outside 09:00-15:00 IST; no notification.')
        return 0
    try:
        rows, close = feed(5, now, size=80)
        checked = datetime.now(UTC)
        direction = candidate(rows, close, checked)
    except Exception:
        # Provider URLs may contain a key. Never print exception details.
        print('DATA UNAVAILABLE: cloud gold candles invalid, unavailable or stale; no notification.')
        return 0
    try:
        updated = update_outcomes(state, rows, checked)
    except Exception:
        print('Performance record invalid; no notification or state overwrite.')
        return 1
    if not alert_window_open(checked) or not direction or already_notified(state, direction, checked):
        if updated != state:
            try:
                save(updated, sha)
                print('Forward alert outcomes saved; direction rule unchanged.')
            except Exception:
                print('Outcome state write failed; no notification.')
                return 1
    if not alert_window_open(checked):
        print('Outside 09:00-15:00 IST; outcome maintenance only, no notification.')
        return 0
    if not direction:
        print('No clear fresh 5m direction; no notification.')
        return 0
    print('Fresh Twelve Data XAU/USD 5m closed through ' + close.astimezone(IST).isoformat())
    if already_notified(state, direction, checked):
        print('Direction unchanged: ' + direction + '; no notification.')
        return 0
    message = direction + ' direction — 5m technical lean (' + checked.astimezone(IST).strftime('%H:%M IST') + ')'
    # Calculate from the same completed candles BEFORE delivery. Its result
    # is recorded for comparison only and does not suppress any live alert.
    shadow_filter = review_filter(rows, direction)
    # Recheck the boundary immediately before starting Telegram delivery.
    if not alert_window_open(datetime.now(UTC)):
        print('Alert window ended before delivery; no notification.')
        return 0
    try:
        deliver(message)
    except Exception:
        print('Telegram delivery unconfirmed; notification state unchanged.')
        return 1
    print(message)
    print('Telegram delivery confirmed.')
    try:
        delivered = datetime.now(UTC)
        updated.update(utc_date=checked.date().isoformat(), last_notified=direction,
                       alert_window=ALERT_WINDOW,
                       session_date_ist=checked.astimezone(IST).date().isoformat(),
                       notified_ist=checked.astimezone(IST).isoformat(),
                       delivered_ist=delivered.astimezone(IST).isoformat(),
                       source='Twelve Data XAU/USD 5m')
        updated = add_alert(updated, direction, delivered, close, rows[-1]['c'], shadow_filter,
                            alert_window=ALERT_WINDOW)
        updated = update_outcomes(updated, rows, delivered)
        save(updated, sha)
    except Exception:
        print('STATE WRITE FAILED after confirmed delivery; duplicate possible on next run.')
        return 1
    print('Delivered direction state saved.')
    if shadow_feed is not None:
        collect_after_delivery(checked, delivered, direction, load, save, shadow_feed)
    return 0


if __name__ == '__main__':
    sys.exit(run(datetime.now(UTC), shadow_feed=fetch))
