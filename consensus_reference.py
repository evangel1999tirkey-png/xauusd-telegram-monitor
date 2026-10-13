"""Match a dated named survey to an exact release; never substitute forecasts."""
import math
import json
from datetime import datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

IDENTITY=('event_code','period_server','event_utc_epoch','unit','multiplier')

def match(row,ledger,now):
    out={'named_consensus_verified':False,'news_comparison_ready':False,
         'eligible_for_combined_bias':False}
    refs=[r for r in ledger.get('records',[]) if all(
        row.get(k) is not None and row.get(k)==r.get(k) for k in IDENTITY)]
    if len(refs)!=1:return {**out,'consensus_reason':'missing_or_ambiguous_exact_reference'}
    ref=refs[0]
    try:
        value=ref['market_consensus']
        if type(value) not in (int,float) or not math.isfinite(value):raise ValueError()
        event=datetime.fromtimestamp(ref['event_utc_epoch'],timezone.utc)
        published=datetime.fromisoformat(ref['source_publication_utc'])
        updated=datetime.fromisoformat(ref['source_updated_utc'])
        checked=datetime.fromisoformat(ledger['verified_at_utc'])
        if any(t.tzinfo is None for t in (now,published,updated,checked)):raise ValueError()
        if not (event-timedelta(days=7)<=published<=updated<=checked<=now
                and updated<event and now<=event+timedelta(minutes=30)):
            raise ValueError()
        source=urlparse(ref['consensus_source'])
        if (source.scheme!='https' or not source.hostname
            or not (source.hostname=='reuters.com' or source.hostname.endswith('.reuters.com')
                    or source.hostname=='marketscreener.com' or source.hostname.endswith('.marketscreener.com'))
            or ref.get('publisher')!='Reuters' or not ref.get('consensus_survey')
            or ref.get('full_text_verified') is not True):raise ValueError()
    except (KeyError,ValueError,TypeError,OverflowError):
        return {**out,'consensus_reason':'source_value_publication_or_freshness_unverified'}
    out.update(named_consensus_verified=True,market_consensus=value,
               consensus_survey=ref['consensus_survey'],consensus_source=ref['consensus_source'],
               consensus_source_publication_utc=published.isoformat(),
               consensus_reason='dated_exact_release_reference_not_continuous_poll_feed')
    actual=row.get('actual')
    ready=(event<=now and row.get('official_actual_verified') is True
           and row.get('prior_revision_verified') is True
           and row.get('official_publication_verified') is True
           and type(actual) in (int,float) and math.isfinite(actual))
    if ready:
        out.update(news_comparison_ready=True,surprise_vs_named_market_survey=actual-value)
    # Reaction, news context, structure and execution-cost checks remain separate.
    return out


def context(now):
    try:
        ledger=json.loads(Path(__file__).with_name('verified_consensus.json').read_text())
        lines=[]
        for ref in ledger['records']:
            event=datetime.fromtimestamp(ref['event_utc_epoch'],timezone.utc)
            if not -timedelta(minutes=30)<=event-now<=timedelta(hours=48):continue
            result=match({**ref,'actual':None},ledger,now)
            if not result['named_consensus_verified']:continue
            label={'consumer-price-index-yy':'Headline CPI y/y',
                   'consumer-price-index-ex-food-energy-yy':'Core CPI y/y'}.get(ref['event_code'])
            if label is None:continue
            when=event.astimezone(ZoneInfo('Asia/Kolkata')).strftime('%d %b %H:%M IST')
            lines.append(label+' dated Reuters poll reference: '+str(result['market_consensus'])
                         +'%; release '+when+'. '+result['consensus_source'])
        return ('\n'.join(lines)+'\nPoll reference only; current actual/revision/publication and reaction confirmation incomplete.'
                if lines else 'No active exact dated consensus reference; market-consensus confirmation incomplete.')
    except Exception:
        return 'Dated consensus reference unavailable/invalid; market-consensus confirmation incomplete.'
