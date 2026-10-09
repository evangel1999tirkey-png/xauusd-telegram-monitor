import unittest
from datetime import datetime, timedelta, timezone
from candle_feed import validate, aggregate

class TrialFeedChecks(unittest.TestCase):
    def test_currency_cannot_be_mistaken_for_gold(self):
        now=datetime(2026,10,9,19,22,tzinfo=timezone.utc)
        start=now.replace(minute=20)-timedelta(minutes=200)
        raw=[dict(datetime=(start+timedelta(minutes=5*i)).isoformat(),
                  open='1.1',high='1.2',low='1.0',close='1.15') for i in range(40)]
        payload=dict(status='ok',meta=dict(symbol='EUR/USD',interval='5min',timezone='UTC'),values=raw)
        with self.assertRaises(ValueError):
            validate(payload,5,now)
        self.assertEqual(len(validate(payload,5,now,symbol='EUR/USD')[0]),40)

    def test_closed_bars_and_identity_guards(self):
        now=datetime(2026,10,9,19,22,tzinfo=timezone.utc)
        start=now.replace(minute=20)-timedelta(minutes=200)
        raw=[dict(datetime=(start+timedelta(minutes=5*i)).isoformat(),
                  open='100',high='102',low='99',close='101') for i in range(41)]
        good=dict(status='ok',meta=dict(symbol='XAU/USD',interval='5min',timezone='UTC'),values=raw)
        rows,close=validate(good,5,now)
        self.assertEqual(len(rows),40)
        self.assertEqual(close,now.replace(minute=20))
        for changes in (dict(meta=dict(symbol='XAG/USD',interval='5min')),
                        dict(status='error'),dict(values=raw[:-3]),
                        dict(values=raw+raw[:1]),
                        dict(values=[{**raw[0], 'low':'200'}]+raw[1:])):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate({**good,**changes},5,now)

    def test_aggregation_drops_missing_and_open_segments(self):
        start=datetime(2026,10,1,tzinfo=timezone.utc)
        bars=[dict(time=start+timedelta(minutes=5*i),o=100,h=102,l=99,c=101)
              for i in range(48*32+2)]
        now=bars[-1]['time']+timedelta(minutes=5)
        grouped,close=aggregate(bars,240,now)
        self.assertEqual(len(grouped),32)
        self.assertEqual(close,start+timedelta(hours=128))
        grouped,_=aggregate(bars[:50]+bars[51:],240,now)
        self.assertEqual(len(grouped),31)

if __name__=='__main__': unittest.main()
