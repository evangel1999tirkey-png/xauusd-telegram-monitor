"""Ephemeral cloud runtime/demo investor test; never sends Telegram or orders."""
import json
import os
from pathlib import Path
import subprocess
import sys
from xm_spread_probe import probe


def collect():
    import MetaTrader5 as mt
    terminal=os.environ.get('XM_TERMINAL_PATH','')
    if not terminal or not Path(terminal).is_file():
        return {'status':'CLOUD_RUNTIME_UNAVAILABLE'}
    if os.environ.get('BROKER_CLOUD_APPROVED')!='1':
        return {'status':'CLOUD_RUNTIME_READY','sdk_version':mt.__version__,
                'broker_authenticated':False,'reason':'specific_credential_transfer_approval_required',
                'telegram_sent':False}
    login,server,password=(os.environ.get(k) for k in ('XM_DEMO_LOGIN','XM_DEMO_SERVER','XM_INVESTOR_PASSWORD'))
    if not all((login,server,password)):
        missing=[name for name,value in zip(
            ('XM_DEMO_LOGIN','XM_DEMO_SERVER','XM_INVESTOR_PASSWORD'),
            (login,server,password)) if not value]
        return {'status':'BROKER_CLOUD_UNCONNECTED','reason':'encrypted_broker_secrets_missing',
                'missing_secret_names':missing}
    try:
        expected_login=int(login)
        if not mt.initialize(terminal,timeout=60000,portable=True):
            error=mt.last_error()
            code=error[0] if isinstance(error,tuple) and type(error[0]) is int else None
            return {'status':'BROKER_CLOUD_UNCONNECTED','reason':'terminal_startup_not_verified',
                    'sdk_error_code':code}
        if not mt.login(expected_login,server=server,password=password,timeout=30000):
            error=mt.last_error()
            code=error[0] if isinstance(error,tuple) and type(error[0]) is int else None
            return {'status':'BROKER_CLOUD_UNCONNECTED','reason':'broker_authentication_not_verified',
                    'sdk_error_code':code}
        # Do not log SDK errors, credentials, account balances, names or numbers.
        mt.shutdown()
        offset=int(os.environ.get('XM_SERVER_OFFSET_SECONDS','0'))
        day=os.environ.get('XM_OFFSET_VERIFIED_DATE')
        result=probe(mt,terminal,expected_login,server,offset,day,portable=True)
        return {**result,'cloud_demo_only':True,'telegram_sent':False}
    finally:
        password=None
        mt.shutdown()


def main():
    if '--worker' not in sys.argv:
        try:
            print(subprocess.check_output([sys.executable,__file__,'--worker'],
                  timeout=120,text=True,stderr=subprocess.DEVNULL).strip())
        except subprocess.TimeoutExpired:
            print(json.dumps({'status':'BROKER_CLOUD_UNCONNECTED','reason':'bounded_connection_timeout'}))
        except subprocess.CalledProcessError:
            print(json.dumps({'status':'BROKER_CLOUD_UNCONNECTED','reason':'probe_failed'}))
        return
    try:result=collect()
    except Exception:result={'status':'BROKER_CLOUD_UNCONNECTED','reason':'probe_failed'}
    print(json.dumps(result))


if __name__=='__main__':main()