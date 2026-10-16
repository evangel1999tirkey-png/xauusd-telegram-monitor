import unittest
from copy import deepcopy
from session_performance import report, WINDOW


def alert(delivered='2026-10-19T03:35:00+00:00', endpoint='2026-10-19T03:40:00+00:00'):
    return dict(alert_window=WINDOW, direction='UP', delivered_utc=delivered,
                reference_close_utc='2026-10-19T03:35:00+00:00',
                outcomes={'5': dict(status='MEASURED', outcome='FAVOURABLE', evaluated_close_utc=endpoint)})


class SessionTests(unittest.TestCase):
    def test_legacy_excluded_empty_is_not_zero_accuracy(self):
        old = alert()
        old.pop('alert_window')
        result = report([old])
        self.assertEqual(result['baseline']['alerts'], 0)
        self.assertIsNone(result['baseline']['outcomes']['5']['favourable_pct'])
        self.assertEqual(result['conclusion'], 'NO_FORWARD_WINDOW_DATA')

    def test_hour_uses_ist_and_separates_directions(self):
        first = alert()
        second = alert('2026-10-20T08:35:00+00:00', '2026-10-20T08:40:00+00:00')
        second['direction'] = 'DOWN'
        result = report([first, second])
        self.assertEqual(result['hourly']['09:00-10:00']['alerts'], 1)
        self.assertEqual(result['hourly']['14:00-15:00']['alerts'], 1)
        self.assertEqual(result['baseline']['session_days'], 2)
        self.assertEqual(result['by_direction']['DOWN']['alerts'], 1)

    def test_endpoints_after_session_excluded_without_mutation(self):
        source = alert('2026-10-19T09:25:00+00:00', '2026-10-19T09:35:00+00:00')
        saved = deepcopy(source)
        result = report([source])
        self.assertEqual(result['baseline']['outcomes']['5']['outside_session'], 1)
        self.assertEqual(result['baseline']['outcomes']['5']['measured'], 0)
        self.assertEqual(source, saved)
        source['outcomes']['5']['evaluated_close_utc'] = '2026-10-19T09:30:00+00:00'
        self.assertEqual(report([source])['baseline']['outcomes']['5']['measured'], 1)

    def test_wrong_or_naive_delivery_excluded(self):
        before = alert('2026-10-19T03:29:59+00:00')
        after = alert('2026-10-19T09:30:00+00:00')
        naive = alert('2026-10-19T09:00:00')
        result = report([before, after, naive])
        self.assertEqual(result['excluded_tagged_records'], 3)
        self.assertEqual(result['baseline']['alerts'], 0)

    def test_pending_missing_and_flat_are_separate(self):
        a, b, c = alert(), alert(), alert()
        a['outcomes'] = {}
        b['outcomes']['5'] = {'status': 'UNAVAILABLE'}
        c['outcomes']['5']['outcome'] = 'FLAT'
        stats = report([a,b,c])['baseline']['outcomes']['5']
        self.assertEqual((stats['pending'], stats['unavailable'], stats['flat']), (1,1,1))
        self.assertEqual(stats['favourable_pct'], 0)

    def test_shadow_comparison_only_window_and_in_session_outcomes(self):
        a, b = alert(), alert('2026-10-19T09:25:00+00:00', '2026-10-19T09:35:00+00:00')
        for r in (a,b):
            r['shadow_15m'] = dict(version='completed15m_ema20_agreement_v1', status='WOULD_KEEP')
        stats = report([a,b])['shadow_15m_comparison']['5']
        self.assertEqual(stats['baseline']['measured'], 1)

    def test_delivery_candle_age_is_measured_not_claimed_schedule_delay(self):
        a = alert('2026-10-19T03:37:00+00:00')
        timing = report([a])['candle_close_to_confirmed_delivery_seconds']
        self.assertEqual(timing['median'], 120)


if __name__ == '__main__':
    unittest.main()
