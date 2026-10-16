"""Session entry-setup research. Fixed heuristics, not a validated trading system."""
from datetime import datetime, timedelta
from math import isfinite
from zoneinfo import ZoneInfo
from signal_rules import context_direction, technical_evidence

IST = ZoneInfo('Asia/Kolkata')
VERSION = 'session_break_retest_1m_v1'


def in_window(now):
    return 9 <= now.astimezone(IST).hour < 15


def checked_bars(rows, interval, now, max_age):
    if len(rows) < 30 or now.tzinfo is None:
        raise ValueError('insufficient_or_undated_bars')
    for bar in rows:
        if bar['time'].tzinfo is None or bar['time']+timedelta(minutes=interval) > now:
            raise ValueError('unclosed_or_undated_bar')
        o,h,l,c = (bar[k] for k in ('o','h','l','c'))
        if not all(isfinite(v) and v > 0 for v in (o,h,l,c)) or not l <= min(o,c) <= max(o,c) <= h:
            raise ValueError('invalid_ohlc')
    if any(a['time'] >= b['time'] for a,b in zip(rows,rows[1:])):
        raise ValueError('unordered_or_duplicate_bars')
    # Match the connector's recent continuity horizon. Older closed-market
    # gaps must not eliminate the entire early sitting's EMA history.
    if any(b['time']-a['time'] != timedelta(minutes=interval) for a,b in zip(rows[-12:],rows[-11:])):
        raise ValueError('recent_gap')
    close = rows[-1]['time']+timedelta(minutes=interval)
    if not timedelta(0) <= now-close <= timedelta(seconds=max_age):
        raise ValueError('stale_bars')
    return close


def assess(five, fifteen, one, now):
    result = dict(version=VERSION, mode='SHADOW_ONLY', status='OUTSIDE_WINDOW',
                  checked_ist=now.astimezone(IST).isoformat(), direction=None,
                  source='Twelve Data XAU/USD reference candles', execution_verified=False)
    if not in_window(now):
        return result
    try:
        close5 = checked_bars(five, 5, now, 330)
        close15 = checked_bars(fifteen, 15, now, 930)
    except (KeyError, TypeError, ValueError, OverflowError):
        return dict(result, status='DATA_UNAVAILABLE')
    direction5, direction15 = context_direction(five), context_direction(fifteen)
    result.update(closed_5m_ist=close5.astimezone(IST).isoformat(),
                  closed_15m_ist=close15.astimezone(IST).isoformat())
    if direction5 not in ('BUY','SELL') or direction5 != direction15:
        return dict(result, status='DIRECTION_NOT_ALIGNED')
    direction = {'BUY':'UP','SELL':'DOWN'}[direction5]
    result.update(direction=direction, status='DIRECTION_ONLY')
    structure = technical_evidence(five, fifteen)
    if structure.direction != direction5 or structure.invalidation is None:
        return result
    # The whole breakout/retest/continuation pattern must form in this sitting.
    start = now.astimezone(IST).replace(hour=9, minute=0, second=0, microsecond=0)
    if five[-3]['time'] < start:
        return dict(result, status='PATTERN_STARTED_BEFORE_SESSION')
    history = five[:-3]
    tr = [max(b['h']-b['l'], abs(b['h']-a['c']), abs(b['l']-a['c']))
          for a,b in zip(history, history[1:])]
    atr = sum(tr[-14:])/14
    level = (max(b['h'] for b in five[-9:-3]) if direction=='UP'
             else min(b['l'] for b in five[-9:-3]))
    result.update(status='ENTRY_PENDING', invalidation=structure.invalidation,
                  breakout_level=level, five_atr=atr,
                  setup_id=VERSION+':'+direction+':'+five[-3]['time'].isoformat())
    if one is None:
        return result
    try:
        close1 = checked_bars(one, 1, now, 75)
    except (KeyError, TypeError, ValueError, OverflowError):
        return dict(result, status='ENTRY_DATA_UNAVAILABLE')
    if close1 <= close5:
        return result
    prev, last = one[-2:]
    # Reject a pattern already invalidated on ANY observed 1m candle since retest.
    observed = [b for b in one if b['time'] >= five[-2]['time']]
    if (direction=='UP' and any(b['l'] <= structure.invalidation for b in observed
                               if b['time'] >= five[-1]['time'])) or (
            direction=='DOWN' and any(b['h'] >= structure.invalidation for b in observed
                                     if b['time'] >= five[-1]['time'])):
        return dict(result, status='STRUCTURE_INVALIDATED')
    if abs(last['c']-five[-1]['c']) > .5*atr:
        return dict(result, status='ENTRY_EXTENDED')
    if last['h']-last['l'] > 3*atr:
        return dict(result, status='ENTRY_SPIKE')
    continuation = (last['l'] > prev['l'] and last['c'] > prev['h']
                    and last['c'] > structure.invalidation if direction=='UP' else
                    last['h'] < prev['h'] and last['c'] < prev['l']
                    and last['c'] < structure.invalidation)
    if not continuation:
        return result
    return dict(result, status='TECHNICAL_SETUP_CANDIDATE',
                reference_close_utc=close1.isoformat(), reference_price=last['c'],
                closed_1m_ist=close1.astimezone(IST).isoformat())


def record_candidate(study, observation, now, cap=3):
    """Research selections only: never counts orders, trades or Telegram sends."""
    from copy import deepcopy
    if cap not in (2,3):
        raise ValueError('invalid_session_cap')
    day = now.astimezone(IST).date().isoformat()
    result = deepcopy(study)
    records = result.setdefault('candidates', [])
    today = [r for r in records if r['session_date_ist']==day]
    status = observation['status']
    if not in_window(now):
        status = 'OUTSIDE_WINDOW'
    elif status == 'TECHNICAL_SETUP_CANDIDATE':
        if any(r['setup_id']==observation['setup_id'] for r in records):
            status = 'DUPLICATE_SETUP'
        elif len(today) >= cap:
            status = 'SESSION_CAP_REACHED'
        elif today and now-datetime.fromisoformat(today[-1]['selected_utc']) < timedelta(minutes=30):
            status = 'COOLDOWN'
        else:
            records.append(dict(observation, session_date_ist=day,
                                selected_utc=now.isoformat(), outcomes={}))
            status = 'SHADOW_CANDIDATE_RECORDED'
    result.update(version=VERSION, mode='SHADOW_ONLY', max_per_session=cap,
                  cooldown_minutes=30, latest=dict(observation, status=status))
    result['candidates'] = records[-500:]
    return result


def update_outcomes(study, one, now):
    """Forward 1m reference-price outcomes for research selections, never fills."""
    from copy import deepcopy
    result = deepcopy(study)
    checked_bars(one, 1, now, 75)
    bars = [(b['time']+timedelta(minutes=1), b['c']) for b in one]
    records = result.get('candidates', [])
    for record in records:
        selected = datetime.fromisoformat(record['selected_utc'])
        reference = datetime.fromisoformat(record['reference_close_utc'])
        end = selected.astimezone(IST).replace(hour=15,minute=0,second=0,microsecond=0)
        outcomes = record.setdefault('outcomes', {})
        for m in (5,10,15):
            if str(m) in outcomes:
                continue
            target = selected+timedelta(minutes=m)
            eligible = [(t,p) for t,p in bars if target <= t < target+timedelta(minutes=1) and t <= now]
            if target > end:
                outcomes[str(m)] = {'status':'OUTSIDE_SESSION'}
            elif eligible:
                close, price = eligible[0]
                if close > end:
                    outcomes[str(m)] = {'status':'OUTSIDE_SESSION'}
                    continue
                path = [t for t,_ in bars if reference <= t <= close]
                expected = int((close-reference).total_seconds()//60)+1
                if not path or path[0] != reference or len(path) != expected or any(
                        b-a != timedelta(minutes=1) for a,b in zip(path,path[1:])):
                    outcomes[str(m)] = {'status':'UNAVAILABLE'}
                    continue
                change = (price-record['reference_price'])*(1 if record['direction']=='UP' else -1)
                outcomes[str(m)] = dict(status='MEASURED', signed_change_usd_per_oz=round(change,6),
                    evaluated_close_utc=close.isoformat(), reference_price=price,
                    minutes_after_selection=round((close-selected).total_seconds()/60,3),
                    outcome='FAVOURABLE' if change > 0 else 'ADVERSE' if change < 0 else 'FLAT')
            elif now >= target+timedelta(minutes=1):
                outcomes[str(m)] = {'status':'UNAVAILABLE'}
    summary = {}
    for m in (5,10,15):
        outcomes = [r.get('outcomes',{}).get(str(m),{}) for r in records]
        measured = [o for o in outcomes if o.get('status')=='MEASURED']
        good = sum(o['outcome']=='FAVOURABLE' for o in measured)
        summary[str(m)] = dict(measured=len(measured), favourable=good,
            adverse=sum(o['outcome']=='ADVERSE' for o in measured),
            flat=sum(o['outcome']=='FLAT' for o in measured), pending=sum(not o for o in outcomes),
            unavailable=sum(o.get('status')=='UNAVAILABLE' for o in outcomes),
            outside_session=sum(o.get('status')=='OUTSIDE_SESSION' for o in outcomes),
            favourable_pct=round(100*good/len(measured),2) if measured else None)
    result.update(summary=summary, measurement_scope='1m reference closes 5/10/15 minutes after shadow selection, rounded up to next completed minute; no fills, costs, trades or profitability. Not a matched baseline comparison.')
    return result
