"""Local XM demo quote verification. No credentials or order calls.

Requires the user to sign in to the terminal with an investor password first.
This probe never enables signal delivery or treats demo spread as real spread.
"""
import argparse
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone


def validate_tick(tick, now, max_age=15, server_offset_seconds=0,
                  offset_verified_date=None):
    if server_offset_seconds not in (0, 7200, 10800):
        raise ValueError('unsupported_server_time_mapping')
    if server_offset_seconds and offset_verified_date != now.date().isoformat():
        raise ValueError('server_time_mapping_requires_session_verification')
    bid, ask = float(tick.bid), float(tick.ask)
    stamp = float(tick.time_msc) / 1000 - server_offset_seconds
    if not all(math.isfinite(v) for v in (bid, ask, stamp)):
        raise ValueError('nonfinite_quote')
    if bid <= 0 or ask < bid:
        raise ValueError('invalid_bid_ask')
    if not 0 <= now.timestamp() - stamp <= max_age:
        raise ValueError('stale_or_future_tick')
    return {'bid': bid, 'ask': ask, 'spread_usd_per_oz': ask-bid,
            'server_offset_seconds': server_offset_seconds,
            'tick_utc': datetime.fromtimestamp(stamp, timezone.utc).isoformat()}


def validate_account(account, expected_login, expected_server, demo_mode):
    if account is None:
        raise ValueError('terminal_login_required')
    if account.login != expected_login or account.server != expected_server:
        raise ValueError('wrong_selected_account')
    if account.trade_mode != demo_mode:
        raise ValueError('demo_account_required')
    if account.trade_allowed:
        raise ValueError('read_only_session_required')


def probe(mt, terminal, expected_login, expected_server, server_offset_seconds=0,
          offset_verified_date=None):
    if not mt.initialize(terminal, timeout=10000):
        raise ValueError('terminal_connection_unavailable')
    try:
        validate_account(mt.account_info(), expected_login, expected_server,
                         mt.ACCOUNT_TRADE_MODE_DEMO)
        info = mt.terminal_info()
        if info is None or not info.connected:
            raise ValueError('broker_connection_unavailable')
        # XM's inspected standard demo GOLD contract uses USD as currency_base,
        # unlike aggregated XAU/USD feeds. Accept its exact broker identifier
        # only with matching description/profit currency; never match stock names
        # containing "Gold" or substitute the separate 24/7 contract.
        candidates = [s for s in (mt.symbols_get() or ())
                      if (s.currency_base == 'XAU'
                          or (s.name == 'GOLD.i#' and s.description == 'GOLD'))
                      and s.currency_profit == 'USD' and s.visible]
        if len(candidates) != 1:
            raise ValueError('select_one_gold_usd_symbol_in_market_watch')
        symbol = candidates[0].name
        first = mt.symbol_info_tick(symbol)
        if first is None:
            raise ValueError('gold_tick_unavailable')
        validate_tick(first, datetime.now(timezone.utc),
                      server_offset_seconds=server_offset_seconds,
                      offset_verified_date=offset_verified_date)
        time.sleep(3)
        second = mt.symbol_info_tick(symbol)
        if second is None or second.time_msc <= first.time_msc:
            raise ValueError('quote_updates_unverified')
        # Recheck identity in case the user changed accounts during the probe.
        validate_account(mt.account_info(), expected_login, expected_server,
                         mt.ACCOUNT_TRADE_MODE_DEMO)
        result = validate_tick(second, datetime.now(timezone.utc),
                               server_offset_seconds=server_offset_seconds,
                               offset_verified_date=offset_verified_date)
        return {'status': 'DEMO_QUOTE_VERIFIED', 'symbol': symbol,
                'scope': 'XM selected demo account only', **result,
                'execution_cost_acceptable': False,
                'note': 'No real-account spread or scalping-cost threshold verified.'}
    finally:
        mt.shutdown()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected-login', type=int, required=True)
    parser.add_argument('--expected-server', required=True)
    parser.add_argument('--terminal', default='C:/Program Files/XM Global MT5/terminal64.exe')
    parser.add_argument('--server-offset-seconds', type=int, default=0)
    parser.add_argument('--offset-verified-date')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.worker:
        # The SDK's internal timeout can hang behind a terminal login dialog.
        # Bound the worker externally without terminating the user's terminal.
        try:
            output = subprocess.check_output(
                [sys.executable, __file__, *sys.argv[1:], '--worker'],
                timeout=20, text=True, stderr=subprocess.DEVNULL)
            print(output.strip())
        except subprocess.TimeoutExpired:
            print(json.dumps({'status': 'DATA_UNAVAILABLE',
                              'reason': 'terminal_connection_timed_out'}))
        except subprocess.CalledProcessError:
            print(json.dumps({'status': 'DATA_UNAVAILABLE', 'reason': 'probe_failed'}))
        return
    try:
        import MetaTrader5 as mt
        result = probe(mt, args.terminal, args.expected_login, args.expected_server,
                       args.server_offset_seconds, args.offset_verified_date)
    except ImportError:
        result = {'status': 'DATA_UNAVAILABLE', 'reason': 'connector_not_installed'}
    except ValueError as error:
        result = {'status': 'DATA_UNAVAILABLE', 'reason': str(error)}
    except Exception:
        # Do not dump account information or SDK exceptions into logs.
        result = {'status': 'DATA_UNAVAILABLE', 'reason': 'probe_failed'}
    print(json.dumps(result))


if __name__ == '__main__':
    main()