"""Free official CPI index history; never impersonate a current release/consensus."""
import json
import math
import urllib.request
from datetime import datetime,timezone
from zoneinfo import ZoneInfo

SOURCE='https://api.bls.gov/publicAPI/v2/timeseries/data/'
SERIES={'CUSR0000SA0':'headline_seasonally_adjusted',
        'CUSR0000SA0L1E':'core_seasonally_adjusted',
        'CUUR0000SA0':'headline_unadjusted',
        'CUUR0000SA0L1E':'core_unadjusted'}


def parse(payload,now):
    if now.tzinfo is None:raise ValueError('bls_check_timezone_missing')
    now=now.astimezone(timezone.utc)
    if payload.get('status')!='REQUEST_SUCCEEDED' or payload.get('message'):
        raise ValueError('bls_request_not_verified')
    results=payload.get('Results')
    if type(results) is not dict or type(results.get('series')) is not list:
        raise ValueError('bls_result_shape_unverified')
    parsed={}
    for series in results['series']:
        code=series.get('seriesID')
        if code not in SERIES or code in parsed:
            raise ValueError('bls_series_identity_unverified')
        rows={};seen=set();missing=[]
        for row in series.get('data',[]):
            period=row.get('period','')
            if period=='M13':continue # Annual average is not a monthly CPI value.
            if len(period)!=3 or not period.startswith('M') or not period[1:].isdigit():
                raise ValueError('bls_month_unverified')
            year=int(row['year']);month=int(period[1:])
            if not 1<=month<=12:raise ValueError('bls_month_unverified')
            stamp=(year,month)
            if stamp>=(now.year,now.month) or stamp in seen:
                raise ValueError('bls_future_or_duplicate_month')
            seen.add(stamp)
            if row['value']=='-':
                notes=row.get('footnotes',[])
                if (type(notes) is not list or len(notes)!=1 or notes[0].get('code')!='X'
                    or not notes[0].get('text','').startswith('Data unavailable')):
                    raise ValueError('bls_missing_value_reason_unverified')
                missing.append({'period':f'{year:04d}-{month:02d}','reason':notes[0]['text']})
                continue
            value=float(row['value'])
            if not math.isfinite(value) or value<=0:
                raise ValueError('bls_index_value_unverified')
            rows[stamp]={'index':value,'footnotes':row.get('footnotes',[])}
        if not rows:raise ValueError('bls_months_missing')
        latest=max(rows)
        age=(now.year-latest[0])*12+now.month-latest[1]
        if not 1<=age<=2:raise ValueError('bls_index_history_stale')
        parsed[code]=(latest,rows,missing)
    if set(parsed)!=set(SERIES) or len({v[0] for v in parsed.values()})!=1:
        raise ValueError('bls_series_incomplete_or_period_conflict')
    latest=next(iter(parsed.values()))[0]
    return {'status':'OFFICIAL_CPI_INDEX_HISTORY_VERIFIED',
            'source':SOURCE,'retrieved_utc':now.isoformat(),
            'latest_period':f'{latest[0]:04d}-{latest[1]:02d}',
            'indices':{SERIES[k]:v[1][latest] for k,v in parsed.items()},
            'missing_historical_periods':{SERIES[k]:v[2] for k,v in parsed.items()},
            'unit':'index_level_not_percent_change',
            'publication_utc':None,'market_consensus':None,
            'release_actual_verified':False,'release_revision_verified':False,
            'current_release_confirmation':False,
            'note':'Official monthly index history only; retrieval time is not publication time.'}


def fetch(now=None):
    now=now or datetime.now(timezone.utc)
    body=json.dumps({'seriesid':list(SERIES),'startyear':str(now.year-1),
                     'endyear':str(now.year)}).encode()
    request=urllib.request.Request(SOURCE,data=body,
                                  headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=20) as response:
        if response.status!=200:raise ValueError('bls_http_unverified')
        payload=json.load(response)
    return parse(payload,now)


def context(now,cpi_window=False):
    # Normally twelve refresh windows/day, plus a listed CPI event window.
    # No retries or every-five-minute API polling. Diagnostics share its quota.
    if not cpi_window and not (now.hour%2==0 and now.minute<5):
        return 'BLS CPI index history unrefreshed this check; release actual/consensus/revision confirmation incomplete.'
    try:
        result=fetch(now)
        checked=now.astimezone(ZoneInfo('Asia/Kolkata')).strftime('%d %b %H:%M IST')
        return ('BLS official CPI index history retrieved '+checked+'; latest period '
                +result['latest_period']+'. Monthly index levels only, not current release confirmation; '
                +'publication time, market consensus and release revisions unverified. '+SOURCE)
    except Exception:
        return 'BLS CPI index API unavailable/invalid this check; release confirmation incomplete.'


if __name__=='__main__':
    try:result=fetch()
    except Exception:result={'status':'OFFICIAL_CPI_INDEX_HISTORY_UNAVAILABLE',
                            'current_release_confirmation':False}
    print(json.dumps(result))
