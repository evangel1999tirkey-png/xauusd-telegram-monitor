"""Independent 15m-agreement experiment, collected AFTER baseline delivery."""
from datetime import datetime, timedelta, timezone
from signal_rules import context_direction
from direction_filter import comparison

VERSION = 'completed15m_ema20_agreement_v1'


def review(rows, decision, direction):
    out = dict(version=VERSION, mode='SHADOW_ONLY', status='UNAVAILABLE',
               decision_utc=decision.isoformat())
    try:
        closed = [r for r in rows if r['time'] + timedelta(minutes=15) <= decision]
        if len(closed) < 30 or direction not in ('UP', 'DOWN'):
            return out
        latest = closed[-1]['time'] + timedelta(minutes=15)
        if not timedelta(0) <= decision-latest <= timedelta(minutes=17):
            return out
        if any(b['time']-a['time'] != timedelta(minutes=15)
               for a,b in zip(closed[-12:],closed[-11:])):
            return out
        trend = context_direction(closed)
        if trend == 'UNVERIFIED':
            return out
        lean = {'BUY':'UP','SELL':'DOWN','NEUTRAL':'FLAT'}[trend]
        out.update(status='WOULD_KEEP' if lean == direction else 'WOULD_SUPPRESS',
                   trend15=lean, closed_through_utc=latest.isoformat(),
                   sample_size=len(closed))
        return out
    except (KeyError, TypeError, ValueError, OverflowError):
        return out


def summarize(records, horizon):
    # Reuse the exact endpoint/count logic but use an independent experiment
    # version and field; never combine it with the earlier weak-slope filter.
    return comparison(records,horizon,field='shadow_15m',version=VERSION)


def collect_after_delivery(decision, delivered, direction, load, save, feed):
    # Baseline notification AND its state have already been committed. This
    # bounded, best-effort collection cannot suppress or delay the live send.
    try:
        reviewed=datetime.now(timezone.utc)
        trial=dict(version=VERSION,mode='SHADOW_ONLY',status='UNAVAILABLE',
                   decision_utc=decision.isoformat())
        try:
            rows,_=feed(15,reviewed,size=80)
            trial=review(rows,decision,direction)
        except Exception:
            pass  # No provider exception strings: may contain credential URLs.
        trial['reviewed_utc']=datetime.now(timezone.utc).isoformat()
        trial['collection']='after confirmed delivery; only candles closed by decision time'
        state,sha=load()
        records=state.get('performance',{}).get('alerts',[])
        matching=[r for r in records if r.get('delivered_utc') == delivered.isoformat()
                  and r.get('direction') == direction]
        if len(matching) != 1 or 'shadow_15m' in matching[0]:
            return
        matching[0]['shadow_15m']=trial
        state['performance']['shadow_15m_comparison']={str(m):summarize(records,m) for m in (5,10,15)}
        save(state,sha)
        print('Independent 15m experiment recorded: '+trial['status']+'; baseline unchanged.')
    except Exception:
        print('15m shadow collection unavailable; baseline delivery state preserved.')
