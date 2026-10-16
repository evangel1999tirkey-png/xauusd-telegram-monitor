import io
import unittest
from copy import deepcopy
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from setup_strategy import assess, record_candidate, update_outcomes
from setup_watch import run

UTC = timezone.utc


def sample():
    close = datetime(2026,10,19,4,30,tzinfo=UTC)
    five = [dict(time=close-timedelta(minutes=5*(30-i)),o=100.,h=102.,l=98.,c=100.) for i in range(30)]
    for bar, values in zip(five[-3:],[(101.,103.,100.,102.5),(102.5,102.8,102.,102.6),(102.6,103.2,102.3,103.1)]):
        bar.update(dict(zip(('o','h','l','c'),values)))
    fifteen = [dict(time=close-timedelta(minutes=15*(30-i)),o=96+i*.2,h=98+i*.2,l=95+i*.2,c=97+i*.2) for i in range(30)]
    one = [dict(time=close+timedelta(minutes=i-29),o=102.8,h=103.,l=102.5,c=102.9) for i in range(30)]
    one[-2].update(o=102.9,h=103.1,l=102.8,c=102.95)
    one[-1].update(o=103.,h=103.3,l=102.9,c=103.2)
    now = close+timedelta(minutes=1,seconds=5)
    return five, fifteen, one, now


class SetupTests(unittest.TestCase):
    def test_valid_up_and_down_reference_patterns(self):
        five,fifteen,one,now = sample()
        result = assess(five,fifteen,one,now)
        self.assertEqual(result['status'],'TECHNICAL_SETUP_CANDIDATE')
        self.assertEqual(result['direction'],'UP')
        self.assertEqual(result['invalidation'],102.)
        self.assertFalse(result['execution_verified'])
        def invert(rows):
            return [dict(time=r['time'],o=200-r['o'],h=200-r['l'],l=200-r['h'],c=200-r['c']) for r in rows]
        bearish=assess(invert(five),invert(fifteen),invert(one),now)
        self.assertEqual((bearish['status'],bearish['direction']),('TECHNICAL_SETUP_CANDIDATE','DOWN'))

    def test_missing_entry_is_pending_not_confirmed(self):
        five,fifteen,one,now=sample()
        self.assertEqual(assess(five,fifteen,None,now)['status'],'ENTRY_PENDING')
        self.assertEqual(assess(five,fifteen,[],now)['status'],'ENTRY_DATA_UNAVAILABLE')

    def test_conflicting_direction_and_failed_retest(self):
        five,fifteen,one,now=sample()
        opposite=[dict(r,c=200-r['c'],o=200-r['o'],h=200-r['l'],l=200-r['h']) for r in fifteen]
        self.assertEqual(assess(five,opposite,one,now)['status'],'DIRECTION_NOT_ALIGNED')
        five[-2]['c']=101.
        five[-2]['l']=100.9
        self.assertEqual(assess(five,fifteen,one,now)['status'],'DIRECTION_ONLY')

    def test_stale_future_gap_and_invalid_ohlc_block(self):
        for change in ('stale','future','gap','ohlc'):
            five,fifteen,one,now=sample()
            if change=='stale':now+=timedelta(minutes=7)
            if change=='future':five[-1]['time']=now
            if change=='gap':five[-2]['time']-=timedelta(minutes=1)
            if change=='ohlc':five[-1]['l']=999.
            with self.subTest(change=change):
                self.assertEqual(assess(five,fifteen,one,now)['status'],'DATA_UNAVAILABLE')

    def test_intrabar_invalidation_extension_and_entry_age(self):
        for change,expected in [('invalidation','STRUCTURE_INVALIDATED'),('extension','ENTRY_EXTENDED'),('stale','ENTRY_DATA_UNAVAILABLE')]:
            five,fifteen,one,now=sample()
            if change=='invalidation':one[-3]['l']=101.9
            if change=='extension':one[-1].update(h=106.,c=105.5)
            if change=='stale':now+=timedelta(seconds=80)
            self.assertEqual(assess(five,fifteen,one,now)['status'],expected)

    def test_pre_session_pattern_and_outside_window_rejected(self):
        five,fifteen,one,now=sample()
        shifted=[[dict(r,time=r['time']-timedelta(hours=1)) for r in rows] for rows in (five,fifteen,one)]
        self.assertEqual(assess(*shifted,now-timedelta(hours=1))['status'],'PATTERN_STARTED_BEFORE_SESSION')
        self.assertEqual(assess(five,fifteen,one,now.replace(hour=9,minute=30))['status'],'OUTSIDE_WINDOW')

    def test_cap_cooldown_duplicate_and_next_session_reset(self):
        *_,now=sample()
        candidate=assess(*sample())
        study=record_candidate({},candidate,now)
        original=deepcopy(study)
        duplicate=record_candidate(study,candidate,now+timedelta(minutes=31))
        self.assertEqual(duplicate['latest']['status'],'DUPLICATE_SETUP')
        self.assertEqual(study,original)
        new=dict(candidate,setup_id='second')
        self.assertEqual(record_candidate(study,new,now+timedelta(minutes=29))['latest']['status'],'COOLDOWN')
        study=record_candidate(study,new,now+timedelta(minutes=30))
        study=record_candidate(study,dict(candidate,setup_id='third'),now+timedelta(minutes=60))
        full=record_candidate(study,dict(candidate,setup_id='fourth'),now+timedelta(minutes=90))
        self.assertEqual(full['latest']['status'],'SESSION_CAP_REACHED')
        self.assertEqual(len(full['candidates']),3)
        next_day=record_candidate(study,dict(candidate,setup_id='new-day'),now+timedelta(days=1))
        self.assertEqual(next_day['latest']['status'],'SHADOW_CANDIDATE_RECORDED')

    def test_cloud_runner_preserves_baseline_and_never_sends(self):
        five,fifteen,one,now=sample()
        state=dict(last_notified='DOWN',utc_date='2026-10-19',other='preserve')
        save=Mock()
        feed=Mock(side_effect=[(five,now),(fifteen,now),(one,now)])
        with redirect_stdout(io.StringIO()):
            result=run(now,load=Mock(return_value=(state,'sha')),save=save,feed=feed,clock=lambda:now)
        self.assertEqual(result,0)
        stored=save.call_args.args[0]
        self.assertEqual((stored['last_notified'],stored['other']),('DOWN','preserve'))
        self.assertEqual(len(stored['setup_study']['candidates']),1)

    def test_cloud_runner_outside_window_no_access(self):
        *_,now=sample()
        load,save,feed=Mock(),Mock(),Mock()
        with redirect_stdout(io.StringIO()):
            self.assertEqual(run(now.replace(hour=10),load,save,feed),0)
        load.assert_not_called();save.assert_not_called();feed.assert_not_called()

    def test_cloud_failure_is_contained_and_does_not_overwrite_state(self):
        *_,now=sample()
        save=Mock()
        with redirect_stdout(io.StringIO()):
            result=run(now,load=Mock(return_value=({},'sha')),save=save,feed=Mock(side_effect=ValueError('sensitive')))
        self.assertEqual(result,1)
        save.assert_not_called()

    def test_forward_outcomes_elapsed_missing_and_immutable(self):
        five,fifteen,one,now=sample()
        study=record_candidate({},assess(five,fifteen,one,now),now)
        close=datetime.fromisoformat(study['candidates'][0]['reference_close_utc'])
        rows=[dict(time=close+timedelta(minutes=i-1),o=103.2+i*.1,
                   h=104.+i*.1,l=102.+i*.1,c=103.2+i*.1) for i in range(-12,22)]
        checked=close+timedelta(minutes=21,seconds=5)
        evaluated=update_outcomes(study,rows,checked)
        outcome=evaluated['candidates'][0]['outcomes']['5']
        self.assertEqual(outcome['status'],'MEASURED')
        self.assertGreater(outcome['minutes_after_selection'],5)
        self.assertLess(outcome['minutes_after_selection'],6)
        self.assertEqual(study['candidates'][0]['outcomes'],{})
        revised=update_outcomes(evaluated,[dict(r,c=r['c']+.1) for r in rows],checked)
        self.assertEqual(evaluated['candidates'],revised['candidates'])
        # Missing reference history cannot turn into a measured win.
        later=[dict(r,time=r['time']+timedelta(hours=1)) for r in rows]
        missing=update_outcomes(study,later,checked+timedelta(hours=1))
        self.assertEqual(missing['candidates'][0]['outcomes']['5']['status'],'UNAVAILABLE')

    def test_outcomes_beyond_end_of_sitting_excluded(self):
        five,fifteen,one,now=sample()
        study=record_candidate({},assess(five,fifteen,one,now),now)
        record=study['candidates'][0]
        record['selected_utc']=now.replace(hour=9,minute=29).isoformat()
        record['reference_close_utc']=now.replace(hour=9,minute=29,second=0).isoformat()
        checked=now.replace(hour=9,minute=29)
        shifted=[dict(r,time=r['time']+timedelta(hours=5,minutes=-2)) for r in one]
        measured=update_outcomes(study,shifted,checked)
        self.assertEqual(measured['candidates'][0]['outcomes']['5']['status'],'OUTSIDE_SESSION')


if __name__=='__main__':unittest.main()
