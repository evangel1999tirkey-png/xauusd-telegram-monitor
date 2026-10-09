"""Conservative technical evidence; callers must separately verify news/data.

These rules are heuristics, not calibrated trade predictions. Input candles
must already have passed symbol, closed-candle and freshness validation.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Evidence:
    direction: str
    reason: str
    invalidation: float | None = None


def ema(values, period):
    result = [values[0]]
    alpha = 2 / (period + 1)
    for value in values[1:]:
        result.append(alpha * value + (1 - alpha) * result[-1])
    return result


def technical_evidence(five, fifteen):
    if len(five) < 30 or len(fifteen) < 30:
        return Evidence('NEUTRAL', 'Insufficient completed candles.')
    # Freeze the reference range BEFORE the breakout/retest/continuation bars.
    reference = five[-9:-3]
    breakout, retest, follow = five[-3:]
    high = max(bar['h'] for bar in reference)
    low = min(bar['l'] for bar in reference)
    history = five[:-3]
    tr = [max(b['h'] - b['l'], abs(b['h'] - a['c']),
              abs(b['l'] - a['c'])) for a, b in zip(history, history[1:])]
    atr = sum(tr[-14:]) / 14
    if atr <= 0:
        return Evidence('NEUTRAL', 'Volatility cannot be verified.')
    if any(b['h'] - b['l'] > 3 * atr for b in five[-3:]):
        return Evidence('NEUTRAL', 'Reaction too volatile; wait for stabilization.')
    if high - low < atr:
        return Evidence('NEUTRAL', 'Reference range too narrow for confirmation.')
    buffer = 0.1 * atr
    close15 = [b['c'] for b in fifteen]
    trend = ema(close15, 20)
    bull15 = close15[-1] > trend[-1] and trend[-1] > trend[-4]
    bear15 = close15[-1] < trend[-1] and trend[-1] < trend[-4]
    bull5 = (breakout['c'] > high + buffer
             and high - buffer <= retest['l'] <= high + 0.25 * atr
             and retest['c'] > high
             and follow['l'] > retest['l']
             and follow['c'] > max(breakout['c'], retest['h'])
             and follow['c'] - high <= 1.5 * atr)
    bear5 = (breakout['c'] < low - buffer
             and low - 0.25 * atr <= retest['h'] <= low + buffer
             and retest['c'] < low
             and follow['h'] < retest['h']
             and follow['c'] < min(breakout['c'], retest['l'])
             and low - follow['c'] <= 1.5 * atr)
    if bull15 and bull5:
        return Evidence('BUY', '15m trend agrees with a closed 5m breakout, held retest and higher low.', retest['l'])
    if bear15 and bear5:
        return Evidence('SELL', '15m trend agrees with a closed 5m breakdown, failed reclaim and lower high.', retest['h'])
    return Evidence('NEUTRAL', 'No aligned 15m trend and completed 5m retest confirmation.')


def confirmed_bias(evidence, verified_news_direction=None, reaction_verified=False,
                   data_fresh=False, high_impact_due=False, spread_ok=False):
    # Defaults fail closed. No headline keywords, screenshots or technical-only
    # candidate may masquerade as a confirmed combined signal.
    if (not data_fresh or not reaction_verified or not spread_ok
            or high_impact_due or evidence.direction == 'NEUTRAL'
            or verified_news_direction != evidence.direction):
        return 'NEUTRAL'
    return evidence.direction


def context_direction(rows):
    if len(rows) < 30:
        return 'UNVERIFIED'
    closes = [bar['c'] for bar in rows]
    average = ema(closes, 20)
    if closes[-1] > average[-1] and average[-1] > average[-4]:
        return 'BUY'
    if closes[-1] < average[-1] and average[-1] < average[-4]:
        return 'SELL'
    return 'NEUTRAL'


def multi_timeframe_evidence(five, fifteen, hourly, four_hour):
    evidence = technical_evidence(five, fifteen)
    hourly_direction = context_direction(hourly)
    broad_direction = context_direction(four_hour)
    if 'UNVERIFIED' in (hourly_direction, broad_direction):
        return Evidence('NEUTRAL', 'Hourly or four-hour context unverified.')
    if evidence.direction == 'NEUTRAL':
        return evidence
    if hourly_direction != evidence.direction:
        return Evidence('NEUTRAL', 'Hourly context does not support the 5m/15m setup.')
    if broad_direction not in (evidence.direction, 'NEUTRAL'):
        return Evidence('NEUTRAL', 'Intraday recovery conflicts with the broader 4h trend; reversal unconfirmed.')
    return Evidence(evidence.direction,
                    evidence.reason + ' Hourly context agrees; 4h is not opposing.',
                    evidence.invalidation)
