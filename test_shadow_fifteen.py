import io
import unittest
from contextlib import redirect_stdout
from datetime import datetime,timedelta,timezone
from unittest.mock import Mock,patch
from shadow_fifteen import review, summarize, collect_after_delivery, VERSION
from cloud_direction import run


class FifteenTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,16,12,tzinfo=timezone.utc)
        self.rows=[dict(time=self.now-timedelta(minutes=15*(80-i)),c=4000+i)
                   for i in range(80)]

    def test_agreement_opposition_flat(self):
        self.assertEqual(review(self.rows,self.now,'UP')['status'],'WOULD_KEEP')
        self.assertEqual(review(self.rows,self.now,'DOWN')['status'],'WOULD_SUPPRESS')
        self.assertEqual(review([dict(r,c=4000) for r in self.rows],self.now,'UP')['trend15'],'FLAT')

    def test_no_future_candles_stale_gap_or_insufficient_data(self):
        future=self.rows+[dict(time=self.now,c=1)]
        self.assertEqual(review(future,self.now,'UP'),review(self.rows,self.now,'UP'))
        self.assertEqual(review(self.rows,self.now+timedelta(minutes=18),'UP')['status'],'UNAVAILABLE')
        self.assertEqual(review(self.rows[:-3]+self.rows[-2:],self.now,'UP')['status'],'UNAVAILABLE')
        self.assertEqual(review(self.rows[-29:],self.now,'UP')['status'],'UNAVAILABLE')

    def test_comparisons_are_independent_and_do_not_backfill(self):
        legacy=dict(shadow_filter={'version':'ema20_slope3_tr14_v1','status':'WOULD_KEEP'},
                    outcomes={'5':{'status':'MEASURED','outcome':'FAVOURABLE'}})
        self.assertEqual(summarize([legacy],5)['baseline']['measured'],0)
        record=dict(legacy,shadow_15m={'version':VERSION,'status':'WOULD_SUPPRESS'})
        self.assertEqual(summarize([record],5)['would_suppress']['measured'],1)
        self.assertEqual(record['shadow_filter'],legacy['shadow_filter'])

    def test_collection_failure_preserves_baseline_and_marks_unavailable(self):
        state={'last_notified':'UP','performance':{'alerts':[
            dict(direction='UP',delivered_utc=self.now.isoformat(),outcomes={})]}}
        save=Mock()
        with redirect_stdout(io.StringIO()):
            collect_after_delivery(self.now,self.now,'UP',Mock(return_value=(state,'newsha')),
                                   save,Mock(side_effect=ValueError()))
        self.assertEqual(save.call_args.args[0]['last_notified'],'UP')
        self.assertEqual(save.call_args.args[0]['performance']['alerts'][0]['shadow_15m']['status'],'UNAVAILABLE')

    def test_live_send_and_baseline_save_precede_any_shadow_request(self):
        events=[]
        state={}
        def load():return state,'sha'
        def save(value,sha):state.update(value);events.append('save')
        def send(message):events.append('send')
        def shadow(interval,now,size):events.append('shadow');raise ValueError()
        rows=[dict(time=self.now-timedelta(minutes=5*(80-i)),c=4000+i) for i in range(80)]
        with patch('cloud_direction.datetime') as clock, redirect_stdout(io.StringIO()):
            clock.now.return_value=self.now
            result=run(self.now,load,save,send,Mock(return_value=(rows,self.now)),shadow)
        self.assertEqual(result,0)
        self.assertEqual(events[:3],['send','save','shadow'])
        self.assertEqual(state['last_notified'],'UP')
        self.assertEqual(events.count('send'),1)


if __name__=='__main__':unittest.main()
