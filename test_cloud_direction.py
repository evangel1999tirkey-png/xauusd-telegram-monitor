import unittest
import io
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from cloud_direction import candidate, run, session_open, alert_window_open, ALERT_WINDOW


class CloudDirectionTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 13, 4, 0, tzinfo=timezone.utc)
        self.rows = [{'c': 4000 + i, 'time': self.now - timedelta(minutes=5*(80-i))} for i in range(80)]

    def test_lean_and_freshness(self):
        self.assertEqual(candidate(self.rows, self.now, self.now), 'UP')
        self.assertEqual(candidate(list(reversed(self.rows)), self.now, self.now), 'DOWN')
        self.assertIsNone(candidate([{'c': 4000}] * 80, self.now, self.now))
        self.assertIsNone(candidate(self.rows, self.now - timedelta(seconds=331), self.now))
        self.assertIsNone(candidate(self.rows, self.now + timedelta(seconds=1), self.now))

    def invoke(self, state=None, delivery=None, load=None):
        deliver = delivery or Mock()
        save = Mock()
        with patch('cloud_direction.datetime') as dt, redirect_stdout(io.StringIO()):
            dt.now.return_value = self.now
            result = run(self.now, load=load or Mock(return_value=(state or {}, 'sha')),
                         save=save, deliver=deliver,
                         feed=Mock(return_value=(self.rows, self.now)))
        return result, deliver, save

    def test_no_duplicate_and_new_day(self):
        _, deliver, save = self.invoke(dict(alert_window=ALERT_WINDOW, session_date_ist="2026-10-13", utc_date='2026-10-13', last_notified='UP'))
        deliver.assert_not_called()
        save.assert_not_called()
        _, deliver, save = self.invoke(dict(alert_window=ALERT_WINDOW, session_date_ist="2026-10-12", utc_date='2026-10-12', last_notified='UP'))
        deliver.assert_called_once()
        save.assert_called_once()

    def test_delivery_failure_preserves_state(self):
        result, _, save = self.invoke(delivery=Mock(side_effect=ValueError()))
        self.assertEqual(result, 1)
        save.assert_not_called()

    def test_state_failure_blocks_send(self):
        result, deliver, _ = self.invoke(load=Mock(side_effect=ValueError()))
        self.assertEqual(result, 1)
        deliver.assert_not_called()

    def test_delivery_records_reference_without_changing_rule(self):
        _, deliver, save = self.invoke()
        deliver.assert_called_once()
        state = save.call_args.args[0]
        record = state['performance']['alerts'][0]
        self.assertEqual(state['last_notified'], 'UP')
        self.assertEqual(record['reference_price'], self.rows[-1]['c'])
        self.assertEqual(record['delivered_utc'], self.now.isoformat())
        self.assertEqual(record['outcomes'], {})

    def test_shadow_rejection_does_not_suppress_live_alert(self):
        with patch('cloud_direction.review_filter', return_value={
                'version':'ema20_slope3_tr14_v1', 'status':'WOULD_SUPPRESS', 'mode':'SHADOW_ONLY'}):
            _, deliver, save = self.invoke()
        deliver.assert_called_once()
        self.assertEqual(save.call_args.args[0]['performance']['alerts'][0]['shadow_filter']['status'],
                         'WOULD_SUPPRESS')

    def test_tracking_updates_without_duplicate_delivery(self):
        state = dict(alert_window=ALERT_WINDOW, session_date_ist="2026-10-13", utc_date='2026-10-13', last_notified='UP', performance={'alerts': [
            dict(direction='UP', delivered_utc=(self.now-timedelta(minutes=16)).isoformat(),
                 reference_close_utc=(self.now-timedelta(minutes=20)).isoformat(),
                 reference_price=self.rows[-5]['c'], outcomes={})]})
        _, deliver, save = self.invoke(state)
        deliver.assert_not_called()
        self.assertEqual(save.call_args.args[0]['last_notified'], 'UP')
        self.assertEqual(save.call_args.args[0]['performance']['summary']['15']['measured'], 1)

    def test_weekend_and_daily_closure(self):
        self.assertFalse(session_open(datetime(2026, 10, 17, 14, tzinfo=timezone.utc)))
        self.assertFalse(session_open(datetime(2026, 10, 13, 21, tzinfo=timezone.utc)))
        self.assertTrue(session_open(self.now))

    def test_ist_window_boundaries(self):
        for hour, minute, expected in [(3,29,False),(3,30,True),(9,29,True),(9,30,False)]:
            moment = self.now.replace(hour=hour, minute=minute)
            self.assertEqual(alert_window_open(moment), expected)

    def test_outside_window_no_send_or_feed(self):
        feed, deliver = Mock(), Mock()
        with redirect_stdout(io.StringIO()):
            result = run(self.now.replace(hour=10), load=Mock(return_value=({}, None)),
                         feed=feed, deliver=deliver)
        self.assertEqual(result, 0)
        feed.assert_not_called()
        deliver.assert_not_called()

    def test_feed_crossing_end_boundary_blocks_delivery(self):
        checked = self.now.replace(hour=9, minute=30)
        deliver = Mock()
        with patch('cloud_direction.datetime') as dt, redirect_stdout(io.StringIO()):
            dt.now.return_value = checked
            run(checked-timedelta(seconds=1), load=Mock(return_value=({}, None)),
                deliver=deliver, feed=Mock(return_value=(self.rows, checked)))
        deliver.assert_not_called()

    def test_outside_window_completes_prior_outcomes_without_alert(self):
        self.now = self.now.replace(hour=9, minute=35)
        self.rows = [{'c': 4000+i, 'time': self.now-timedelta(minutes=5*(80-i))} for i in range(80)]
        state = dict(last_notified='DOWN', performance={'alerts': [
            dict(direction='UP', delivered_utc=(self.now-timedelta(minutes=16)).isoformat(),
                 reference_close_utc=(self.now-timedelta(minutes=20)).isoformat(),
                 reference_price=self.rows[-5]['c'], outcomes={})]})
        _, deliver, save = self.invoke(state)
        deliver.assert_not_called()
        save.assert_called_once()
        self.assertEqual(save.call_args.args[0]['performance']['summary']['15']['measured'], 1)

    def test_delivery_boundary_rechecked_after_analysis(self):
        before = self.now.replace(hour=9, minute=29, second=59)
        after = before+timedelta(seconds=1)
        deliver = Mock()
        with patch('cloud_direction.datetime') as dt, redirect_stdout(io.StringIO()):
            dt.now.side_effect = [before, after]
            run(before, load=Mock(return_value=({}, None)), deliver=deliver,
                feed=Mock(return_value=(self.rows, before)))
        deliver.assert_not_called()


if __name__ == '__main__':
    unittest.main()
