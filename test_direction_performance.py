import unittest
from datetime import datetime, timedelta, timezone
from direction_performance import add_alert, update_outcomes


class DirectionPerformanceTests(unittest.TestCase):
    def setUp(self):
        self.base = datetime(2026, 10, 13, 14, 0, tzinfo=timezone.utc)
        self.delivered = self.base + timedelta(minutes=2)
        self.state = add_alert({}, 'UP', self.delivered, self.base, 4000)
        self.rows = [{'time': self.base+timedelta(minutes=5*i-5), 'c': 4000+i}
                     for i in range(5)]

    def test_only_future_completed_candles_and_exact_elapsed_times(self):
        before = update_outcomes(self.state, self.rows, self.base+timedelta(minutes=9))
        self.assertEqual(before['performance']['alerts'][0]['outcomes'], {})
        result = update_outcomes(self.state, self.rows, self.base+timedelta(minutes=20))
        outcomes = result['performance']['alerts'][0]['outcomes']
        self.assertEqual(outcomes['5']['minutes_after_delivery'], 8)
        self.assertEqual(outcomes['10']['minutes_after_delivery'], 13)
        self.assertEqual(outcomes['15']['minutes_after_delivery'], 18)
        self.assertEqual(outcomes['5']['signed_change_usd_per_oz'], 2)
        self.assertEqual(self.state['performance']['alerts'][0]['outcomes'], {})

    def test_down_flat_and_unavailable_not_counted_as_wins(self):
        down = add_alert({}, 'DOWN', self.delivered, self.base, 4000)
        result = update_outcomes(down, self.rows, self.base+timedelta(minutes=20))
        self.assertEqual(result['performance']['summary']['5']['adverse'], 1)
        flat = [dict(r, c=4000) for r in self.rows]
        result = update_outcomes(self.state, flat, self.base+timedelta(minutes=20))
        self.assertEqual(result['performance']['summary']['5']['flat'], 1)
        missing = update_outcomes(self.state, self.rows[:1], self.base+timedelta(minutes=20))
        self.assertEqual(missing['performance']['summary']['5']['unavailable'], 1)
        self.assertIsNone(missing['performance']['summary']['5']['favourable_pct'])

    def test_gapped_path_rejected_and_completed_outcomes_immutable(self):
        missing = update_outcomes(self.state, self.rows[:1]+self.rows[2:], self.base+timedelta(minutes=20))
        self.assertEqual(missing['performance']['alerts'][0]['outcomes']['5']['status'], 'UNAVAILABLE')
        first = update_outcomes(self.state, self.rows, self.base+timedelta(minutes=20))
        revised = update_outcomes(first, [dict(r, c=9000) for r in self.rows], self.base+timedelta(minutes=25))
        self.assertEqual(first['performance']['alerts'], revised['performance']['alerts'])

    def test_bound_records_and_no_backfilled_historical_alert(self):
        state = {}
        for i in range(502):
            state = add_alert(state, 'UP', self.delivered+timedelta(minutes=i), self.base, 4000)
        self.assertEqual(len(state['performance']['alerts']), 500)
        legacy = {'last_notified': 'UP', 'notified_ist': self.delivered.isoformat()}
        self.assertEqual(update_outcomes(legacy, self.rows, self.base+timedelta(minutes=20)), legacy)


if __name__ == '__main__':
    unittest.main()
