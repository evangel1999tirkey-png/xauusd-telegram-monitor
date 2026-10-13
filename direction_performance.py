"""Forward candle outcomes for delivered alerts; not fills, profit or predictions."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import math
from direction_filter import comparison

HORIZONS = (5, 10, 15)
LIMIT = 500


def stamp(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError('naive_tracking_timestamp')
    return parsed.astimezone(timezone.utc)


def add_alert(state, direction, delivered, reference_close, reference_price, shadow_filter=None):
    if direction not in ('UP', 'DOWN') or not math.isfinite(reference_price) or reference_price <= 0:
        raise ValueError('invalid_tracking_reference')
    if delivered < reference_close:
        raise ValueError('invalid_tracking_time')
    result = deepcopy(state)
    records = result.setdefault('performance', {}).setdefault('alerts', [])
    records.append(dict(direction=direction, delivered_utc=delivered.isoformat(),
                        reference_close_utc=reference_close.isoformat(),
                        reference_price=reference_price,
                        reference_age_seconds=(delivered - reference_close).total_seconds(), outcomes={}))
    if shadow_filter is not None:
        records[-1]['shadow_filter'] = deepcopy(shadow_filter)
    result['performance']['alerts'] = records[-LIMIT:]
    return result


def update_outcomes(state, rows, now):
    result = deepcopy(state)
    records = result.get('performance', {}).get('alerts', [])
    bars = [(row['time'] + timedelta(minutes=5), row['c']) for row in rows]
    for record in records:
        delivered = stamp(record['delivered_utc'])
        reference = stamp(record['reference_close_utc'])
        price = record['reference_price']
        if not math.isfinite(price) or price <= 0 or record['direction'] not in ('UP', 'DOWN'):
            raise ValueError('invalid_tracking_record')
        for minutes in HORIZONS:
            key = str(minutes)
            if key in record['outcomes']:
                continue
            target = delivered + timedelta(minutes=minutes)
            # First completed 5m close at/after the delivery horizon, never an
            # interpolated price. It must be less than 5m after the target.
            eligible = [(t, p) for t, p in bars if target <= t < target + timedelta(minutes=5) and t <= now]
            if not eligible:
                if now >= target + timedelta(minutes=5):
                    record['outcomes'][key] = {'status': 'UNAVAILABLE'}
                continue
            endpoint, ending_price = eligible[0]
            path = [t for t, _ in bars if reference <= t <= endpoint]
            expected = int((endpoint - reference).total_seconds() // 300) + 1
            if (not path or path[0] != reference or len(path) != expected
                    or any(b - a != timedelta(minutes=5) for a, b in zip(path, path[1:]))):
                record['outcomes'][key] = {'status': 'UNAVAILABLE'}
                continue
            change = ending_price - price
            signed = change if record['direction'] == 'UP' else -change
            record['outcomes'][key] = dict(status='MEASURED',
                evaluated_close_utc=endpoint.isoformat(), evaluated_price=ending_price,
                minutes_after_delivery=round((endpoint - delivered).total_seconds() / 60, 3),
                signed_change_usd_per_oz=round(signed, 6),
                outcome='FAVOURABLE' if signed > 0 else 'ADVERSE' if signed < 0 else 'FLAT')
    if 'performance' in result:
        summary = {}
        for minutes in HORIZONS:
            outcomes = [r['outcomes'].get(str(minutes), {}) for r in records]
            measured = [o for o in outcomes if o.get('status') == 'MEASURED']
            favourable = sum(o['outcome'] == 'FAVOURABLE' for o in measured)
            summary[str(minutes)] = dict(measured=len(measured), favourable=favourable,
                adverse=sum(o['outcome'] == 'ADVERSE' for o in measured),
                flat=sum(o['outcome'] == 'FLAT' for o in measured),
                unavailable=sum(o.get('status') == 'UNAVAILABLE' for o in outcomes),
                pending=sum(not o for o in outcomes),
                favourable_pct=round(100 * favourable / len(measured), 2) if measured else None)
        result['performance'].update(schema=1, summary=summary,
            scope='Forward completed-5m reference-price movement after confirmed delivery; no execution costs or fills. Up to 500 latest delivered alerts. Not predictive accuracy or profitability.')
        if any('shadow_filter' in r for r in records):
            result['performance']['shadow_comparison'] = {str(m): comparison(records, m) for m in HORIZONS}
    return result
