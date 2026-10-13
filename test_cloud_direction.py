import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from cloud_direction import candidate, run, session_open


class CloudDirectionTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 13, 14, 0, tzinfo=timezone.utc)
        self.rows = [{'c': 4000 + i} for i in range(80)]

    def test_lean_and_freshness(self):
        self.assertEqual(candidate(self.rows, self.now, self.now), 'UP')
        self.assertEqual(candidate(list(reversed(self.rows)), self.now, self.now), 'DOWN')
        self.assertIsNone(candidate([{'c': 4000}] * 80, self.now, self.now))
        self.assertIsNone(candidate(self.rows, self.now - timedelta(seconds=331), self.now))
        self.assertIsNone(candidate(self.rows, self.now + timedelta(seconds=1), self.now))

    def invoke(self, state=None, delivery=None, load=None):
        deliver = delivery or Mock()
        save = Mock()
        with patch('cloud_direction.datetime') as dt:
            dt.now.return_value = self.now
            result = run(self.now, load=load or Mock(return_value=(state or {}, 'sha')),
                         save=save, deliver=deliver,
                         feed=Mock(return_value=(self.rows, self.now)))
        return result, deliver, save

    def test_no_duplicate_and_new_day(self):
        _, deliver, save = self.invoke(dict(utc_date='2026-10-13', last_notified='UP'))
        deliver.assert_not_called()
        save.assert_not_called()
        _, deliver, save = self.invoke(dict(utc_date='2026-10-12', last_notified='UP'))
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

    def test_weekend_and_daily_closure(self):
        self.assertFalse(session_open(datetime(2026, 10, 17, 14, tzinfo=timezone.utc)))
        self.assertFalse(session_open(datetime(2026, 10, 13, 21, tzinfo=timezone.utc)))
        self.assertTrue(session_open(self.now))


if __name__ == '__main__':
    unittest.main()
