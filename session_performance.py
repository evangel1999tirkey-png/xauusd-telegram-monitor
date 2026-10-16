"""Read-only evaluation of forward alerts in the user's six-hour IST window."""
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo
from statistics import median
from direction_filter import comparison
from shadow_fifteen import summarize as summarize_fifteen

WINDOW = 'IST_0900_1500_v1'
IST = ZoneInfo('Asia/Kolkata')
HORIZONS = (5, 10, 15)


def timestamp(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError('timestamp_requires_timezone')
    return parsed.astimezone(IST)


def counts(records, horizon):
    outcomes = [r.get('outcomes', {}).get(str(horizon), {}) for r in records]
    measured = [o for o in outcomes if o.get('status') == 'MEASURED']
    favourable = sum(o.get('outcome') == 'FAVOURABLE' for o in measured)
    return dict(measured=len(measured), favourable=favourable,
                adverse=sum(o.get('outcome') == 'ADVERSE' for o in measured),
                flat=sum(o.get('outcome') == 'FLAT' for o in measured),
                unavailable=sum(o.get('status') == 'UNAVAILABLE' for o in outcomes),
                outside_session=sum(o.get('status') == 'OUTSIDE_SESSION' for o in outcomes),
                pending=sum(not o for o in outcomes),
                favourable_pct=round(100*favourable/len(measured), 2) if measured else None)


def report(records):
    eligible, excluded = [], 0
    for source in records:
        if source.get('alert_window') != WINDOW:
            continue  # Never reinterpret old all-hours alerts as forward window tests.
        try:
            delivered = timestamp(source['delivered_utc'])
            if not 9 <= delivered.hour < 15 or source.get('direction') not in ('UP', 'DOWN'):
                excluded += 1
                continue
            record = deepcopy(source)
            record['_delivered_ist'] = delivered
            outcomes = record.setdefault('outcomes', {})
            for key, value in outcomes.items():
                if value.get('status') == 'MEASURED':
                    endpoint = timestamp(value['evaluated_close_utc'])
                    if endpoint < delivered or value.get('outcome') not in ('FAVOURABLE', 'ADVERSE', 'FLAT'):
                        raise ValueError('invalid_outcome')
                    # A 15:00 close is observable at the end of the sitting;
                    # later endpoints are excluded from this session-only view.
                    end = delivered.replace(hour=15, minute=0, second=0, microsecond=0)
                    if endpoint > end:
                        outcomes[key] = {'status': 'OUTSIDE_SESSION'}
            eligible.append(record)
        except (KeyError, TypeError, ValueError, OverflowError):
            excluded += 1

    def group(subset):
        return dict(alerts=len(subset),
                    session_days=len({r['_delivered_ist'].date() for r in subset}),
                    outcomes={str(m): counts(subset, m) for m in HORIZONS})

    ages = []
    for r in eligible:
        try:
            age = (r['_delivered_ist']-timestamp(r['reference_close_utc'])).total_seconds()
            if age >= 0:
                ages.append(age)
        except (KeyError, TypeError, ValueError, OverflowError):
            pass
    return dict(window=WINDOW, timezone='Asia/Kolkata', mode='MEASUREMENT_ONLY',
                baseline=group(eligible), excluded_tagged_records=excluded,
                hourly={f'{h:02d}:00-{h+1:02d}:00': group([
                    r for r in eligible if r['_delivered_ist'].hour == h]) for h in range(9, 15)},
                by_direction={d: group([r for r in eligible if r['direction'] == d]) for d in ('UP', 'DOWN')},
                candle_close_to_confirmed_delivery_seconds=dict(
                    observations=len(ages), median=median(ages) if ages else None,
                    maximum=max(ages) if ages else None),
                shadow_15m_comparison={str(m): summarize_fifteen(eligible, m) for m in HORIZONS},
                weak_slope_comparison={str(m): comparison(eligible, m) for m in HORIZONS},
                conclusion='NO_FORWARD_WINDOW_DATA' if not eligible else 'DESCRIPTIVE_ONLY_NO_IMPROVEMENT_ESTABLISHED',
                scope='Only new window-tagged confirmed alerts. Outcomes after 15:00 IST excluded here; original records unchanged. '
                      'Candle age is not scheduler latency or phone receipt time. No fills/costs/profit measurement. '
                      'Hourly subsets and shadow comparisons do not prove improvement; validate on later untouched sessions.')


if __name__ == '__main__':
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('state', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding='utf-8'))
    rendered = json.dumps(report(state.get('performance', {}).get('alerts', [])), indent=2)
    if args.output:
        args.output.write_text(rendered+'\n', encoding='utf-8')
    else:
        print(rendered)
