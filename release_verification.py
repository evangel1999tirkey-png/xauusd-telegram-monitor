"""Match dated official-release evidence; never promote provider forecast to consensus."""
import math
from datetime import datetime,timezone,timedelta


def equal(a,b):
    if a is None or b is None:return a is b
    return math.isclose(a,b,rel_tol=0,abs_tol=.000001)


def verify_row(row,ledger,now):
    result={'official_actual_verified':False,'prior_revision_verified':False,
            'consensus_verified':False,'fresh_release':False,
            'eligible_for_combined_bias':False}
    matches=[r for r in ledger['records'] if all(r.get(k)==row.get(k)
             for k in ('event_code','period_server','event_utc_epoch','unit','multiplier'))]
    if len(matches)!=1:return result
    ref=matches[0]
    result['official_actual_verified']=row.get('actual') is not None and equal(row.get('actual'),ref.get('actual'))
    result['prior_revision_verified']=all(equal(row.get(k),ref.get(k))
                                          for k in ('previous','revised_previous'))
    consensus=ref.get('market_consensus')
    result['consensus_verified']=(consensus is not None and bool(ref.get('consensus_source'))
                                   and bool(ref.get('consensus_survey')))
    event=datetime.fromtimestamp(ref['event_utc_epoch'],timezone.utc)
    result['fresh_release']=timedelta(0)<=now-event<=timedelta(minutes=30)
    if result['official_actual_verified'] and result['consensus_verified']:
        result['surprise_vs_named_market_survey']=ref['actual']-consensus
        result['consensus_survey']=ref['consensus_survey']
        result['provider_forecast_is_consensus']=equal(row.get('provider_forecast'),consensus)
    result['official_source']=ref['official_source']
    # A dated release match alone never verifies the dollar/yield reaction,
    # geopolitical context, structure, spread or entry conditions.
    return result