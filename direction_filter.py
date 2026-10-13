"""One fixed shadow experiment; never gates live alerts."""
import math
from signal_rules import ema

VERSION = 'ema20_slope3_tr14_v1'
THRESHOLD = 0.10


def review(rows, direction):
    result = dict(version=VERSION, mode='SHADOW_ONLY', threshold=THRESHOLD,
                  status='UNAVAILABLE', slope_to_range=None)
    try:
        if len(rows) < 30 or direction not in ('UP', 'DOWN'):
            return result
        values = [float(r['c']) for r in rows]
        if not all(math.isfinite(v) and v > 0 for v in values):
            return result
        ranges = [max(b['h']-b['l'], abs(b['h']-a['c']), abs(b['l']-a['c']))
                  for a, b in zip(rows[-15:], rows[-14:])]
        if not all(math.isfinite(v) and v >= 0 for v in ranges):
            return result
        volatility = sum(ranges) / 14
        if volatility <= 0:
            return result
        average = ema(values, 20)
        slope = average[-1] - average[-4]
        signed = slope if direction == 'UP' else -slope
        score = signed / volatility
        result.update(status='WOULD_KEEP' if score >= THRESHOLD else 'WOULD_SUPPRESS',
                      slope_to_range=score, mean_true_range14=volatility)
        return result
    except (KeyError, TypeError, ValueError, OverflowError):
        return result


def comparison(records, horizon):
    # Only contemporaneously classified alerts in this exact experiment are
    # compared. Older/unclassified alerts cannot inflate the baseline.
    classified = [r for r in records if r.get('shadow_filter', {}).get('version') == VERSION
                  and r['shadow_filter'].get('status') in ('WOULD_KEEP', 'WOULD_SUPPRESS')]
    measured = [r for r in classified if r.get('outcomes', {}).get(str(horizon), {}).get('status') == 'MEASURED']
    kept = [r for r in measured if r['shadow_filter']['status'] == 'WOULD_KEEP']
    suppressed = [r for r in measured if r['shadow_filter']['status'] == 'WOULD_SUPPRESS']

    def counts(group):
        outcomes = [r['outcomes'][str(horizon)]['outcome'] for r in group]
        good = outcomes.count('FAVOURABLE')
        return dict(measured=len(group), favourable=good, adverse=outcomes.count('ADVERSE'),
                    flat=outcomes.count('FLAT'),
                    favourable_pct=100*good/len(group) if group else None)

    baseline, filtered = counts(measured), counts(kept)
    gain = (filtered['favourable_pct'] - baseline['favourable_pct']
            if kept and measured else None)
    return dict(version=VERSION, mode='SHADOW_ONLY', baseline=baseline, would_keep=filtered,
                would_suppress=counts(suppressed),
                measured_retained_pct=100*len(kept)/len(measured) if measured else None,
                observed_difference_percentage_points=gain,
                classified_alerts=len(classified),
                pending=sum(not r.get('outcomes', {}).get(str(horizon)) for r in classified),
                unavailable=sum(r.get('outcomes', {}).get(str(horizon), {}).get('status') == 'UNAVAILABLE'
                                for r in classified),
                interpretation='Descriptive fixed-filter comparison only; not proven improvement or an independently executed filtered strategy.')
