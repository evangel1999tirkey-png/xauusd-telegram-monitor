"""Manual cloud entitlement/freshness test. No Telegram, broker login or trades."""
import json
import os
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime,timezone
from candle_feed import validate


def check(symbol):
    key=os.environ.get('TWELVE_DATA_API_KEY')
    if not key:return {'symbol':symbol,'access':'key_missing'}
    query=urllib.parse.urlencode({'symbol':symbol,'interval':'5min','outputsize':80,
                                 'timezone':'UTC','apikey':key})
    try:
        req=urllib.request.Request('https://api.twelvedata.com/time_series?'+query,
                                  headers={'User-Agent':'PersonalGoldMonitor/1.0'})
        with urllib.request.urlopen(req,timeout=15) as response:
            data=json.load(response)
    except urllib.error.HTTPError as error:
        # The numeric HTTP status is safe; messages/URLs may include the key.
        return {'symbol':symbol,'access':'http_rejected','http_status':error.code}
    except Exception:
        # Never print exception strings, request URLs or provider error messages.
        return {'symbol':symbol,'access':'request_failed'}
    if data.get('status')!='ok':
        code=data.get('code')
        return {'symbol':symbol,'access':'provider_rejected',
                'provider_code':code if isinstance(code,int) else None}
    meta=data.get('meta',{})
    out={'symbol':symbol,'access':'response_received',
         'identity_verified':meta.get('symbol')==symbol,
         'interval_verified':meta.get('interval')=='5min',
         'utc_verified':meta.get('timezone') in ('UTC','Etc/UTC'),
         'returned_bars':len(data.get('values',[]))}
    try:
        newest=max(datetime.fromisoformat(r['datetime']) for r in data.get('values',[]))
        out['latest_returned_bar_time']=newest.isoformat()
    except Exception:
        out['latest_returned_bar_time']='unverified'
    try:
        rows,close=validate(data,5,datetime.now(timezone.utc),symbol)
        out.update(fresh_complete_bars_verified=True,closed_through_utc=close.isoformat())
        if symbol in ('US2Y','US10Y'):
            out['yield_scale_plausible']=all(0<r['c']<30 for r in rows[-7:])
    except ValueError as error:
        out.update(fresh_complete_bars_verified=False,validation_failure=str(error))
    return out


if __name__=='__main__':
    print(json.dumps({'check_utc':datetime.now(timezone.utc).isoformat(),
                      'scope':'manual data test; monitoring and Telegram stay paused',
                      'results':[check(s) for s in ('US2Y','US10Y')]}))