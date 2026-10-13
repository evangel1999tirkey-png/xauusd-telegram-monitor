import unittest
from direction_filter import review, comparison, VERSION


class DirectionFilterTests(unittest.TestCase):
    def rows(self, step=1, width=1):
        return [dict(c=4000+i*step, h=4000+i*step+width, l=4000+i*step-width) for i in range(80)]

    def test_one_filter_separates_strong_and_weak_slope(self):
        self.assertEqual(review(self.rows(), 'UP')['status'], 'WOULD_KEEP')
        self.assertEqual(review(self.rows(step=0.01, width=2), 'UP')['status'], 'WOULD_SUPPRESS')
        self.assertEqual(review(self.rows(step=-1), 'DOWN')['status'], 'WOULD_KEEP')
        self.assertEqual(review(self.rows(), 'DOWN')['status'], 'WOULD_SUPPRESS')

    def test_scale_invariance_and_missing_data(self):
        original = review(self.rows(), 'UP')
        scaled = review([{k:v*2 for k,v in r.items()} for r in self.rows()], 'UP')
        self.assertAlmostEqual(original['slope_to_range'], scaled['slope_to_range'])
        self.assertEqual(review([{'c':1}]*80, 'UP')['status'], 'UNAVAILABLE')
        self.assertEqual(review(self.rows(step=0, width=0), 'UP')['status'], 'UNAVAILABLE')

    def test_matched_baseline_flat_missing_and_retention(self):
        def record(status, outcome, version=VERSION):
            return dict(shadow_filter={'version':version, 'status':status},
                        outcomes={'5':dict(status='MEASURED',outcome=outcome)})
        rows = [record('WOULD_KEEP','FAVOURABLE'),record('WOULD_KEEP','FLAT'),
                record('WOULD_SUPPRESS','ADVERSE'),record('WOULD_KEEP','FAVOURABLE','old')]
        result = comparison(rows,5)
        self.assertEqual(result['baseline']['measured'],3)
        self.assertEqual(result['would_keep']['flat'],1)
        self.assertAlmostEqual(result['observed_difference_percentage_points'],50-100/3)
        self.assertAlmostEqual(result['measured_retained_pct'],200/3)
        self.assertIsNone(comparison([],5)['observed_difference_percentage_points'])

    def test_future_data_does_not_replace_recorded_attestation(self):
        from direction_performance import add_alert
        from datetime import datetime, timezone
        now=datetime(2026,10,13,14,tzinfo=timezone.utc)
        observed=review(self.rows(step=0.01,width=2),'UP')
        state=add_alert({},'UP',now,now,4000,observed)
        observed['status']='WOULD_KEEP'
        self.assertEqual(state['performance']['alerts'][0]['shadow_filter']['status'],'WOULD_SUPPRESS')


if __name__ == '__main__':
    unittest.main()
