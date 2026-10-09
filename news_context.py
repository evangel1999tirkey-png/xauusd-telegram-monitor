"""Public calendar and official release context; never infer a news surprise."""
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

CALENDAR = 'https://nfs.faireconomy.media/ff_calendar_thisweek.json'
FEEDS = {
    'Fed monetary policy': 'https://www.federalreserve.gov/feeds/press_monetary.xml',
    'BLS employment': 'https://www.bls.gov/feed/empsit.rss',
    'BLS CPI': 'https://www.bls.gov/feed/cpi.rss',
    'BEA economic releases': 'https://apps.bea.gov/rss/rss.xml',
}


def calendar_events(payload, now):
    if not isinstance(payload, list) or not payload:
        raise ValueError('calendar_empty')
    rows = []
    all_dates = []
    for event in payload:
        stamp = datetime.fromisoformat(event['date'])
        if stamp.tzinfo is None:
            raise ValueError('calendar_timezone_missing')
        all_dates.append(stamp)
        if event.get('country') == 'USD':
            rows.append({**event, 'time': stamp})
    # Require evidence for this week's calendar, rather than treating an old
    # successful download as a current schedule. No claim of complete coverage.
    if not min(all_dates)-timedelta(days=1) <= now <= max(all_dates)+timedelta(days=2):
        raise ValueError('calendar_outdated')
    return sorted(rows, key=lambda row: row['time'])


def blackout(events, now):
    return [event for event in events if event.get('impact') == 'High'
            and -timedelta(minutes=15) <= event['time']-now <= timedelta(minutes=15)]


def release_items(data, now):
    rows = []
    for item in ET.fromstring(data).findall('.//item'):
        date = item.findtext('pubDate')
        if not date:
            continue
        stamp = parsedate_to_datetime(date)
        if stamp.tzinfo is None or stamp > now:
            continue
        title, link = item.findtext('title') or '', item.findtext('link') or ''
        if not link.startswith(('https://www.bls.gov/', 'https://www.federalreserve.gov/', 'https://www.bea.gov/')):
            continue
        rows.append((stamp, title[:180], link))
    if not rows:
        raise ValueError('release_dates_unverified')
    return sorted(rows, reverse=True)


def download(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'PersonalGoldMonitor/1.0'})
    with urllib.request.urlopen(req, timeout=10) as response:
        return response.read()


def context(now):
    ist = ZoneInfo('Asia/Kolkata')
    lines = []
    try:
        events = calendar_events(json.loads(download(CALENDAR)), now)
        blocked = blackout(events, now)
        upcoming = [event for event in events if event['time'] >= now]
        lines.append('Calendar checked now: Forex Factory weekly export; actuals/revisions unavailable.')
        if blocked:
            lines.append('WAIT: high-impact USD event within the 15-minute pre/post-release window: '
                         + ', '.join(event['title'] for event in blocked) + '.')
        if upcoming:
            event = upcoming[0]
            lines.append('Next listed USD event: ' + event['title'] + ', '
                         + event['time'].astimezone(ist).strftime('%d %b %H:%M IST') + '.')
        else:
            lines.append('No later USD event listed this week; this does not verify absence of unscheduled news.')
        lines.append('https://www.forexfactory.com/calendar')
    except Exception:
        lines.append('Economic calendar unavailable/outdated; event risk unverified.')
    for name, url in FEEDS.items():
        try:
            latest = release_items(download(url), now)[0]
            lines.append(name + ' latest publication: ' + latest[0].astimezone(ist).strftime('%d %b %H:%M IST')
                         + '; ' + latest[1] + '. ' + latest[2])
        except Exception:
            lines.append(name + ' release feed unavailable or dates unverified.')
    lines.append('RSS is publication context, not consensus/revision analysis, live yield reaction or complete news coverage.')
    return '\n'.join(lines)


def dollar_proxy(now):
    # Once each quarter hour: up to 96 additional daily credits. Together with
    # the two gold requests/check this totals at most 672/day before retries.
    # This is a single currency pair, never DXY or a yield-reaction substitute.
    if now.minute % 15 >= 5:
        return 'EUR/USD cross-check not refreshed this check; live dollar/yield confirmation unverified.'
    try:
        from candle_feed import fetch
        bars, close = fetch(15, now, size=80, symbol='EUR/USD')
        change = (bars[-1]['c']/bars[-4]['c']-1)*100
        return ('EUR/USD 45-minute change: ' + f'{change:+.3f}%' + '; completed through '
                + close.astimezone(ZoneInfo('Asia/Kolkata')).strftime('%H:%M IST')
                + '. Single-pair dollar proxy only; not DXY, news confirmation or yields.')
    except Exception:
        return 'EUR/USD cross-check unavailable/stale; live dollar/yield confirmation unverified.'
