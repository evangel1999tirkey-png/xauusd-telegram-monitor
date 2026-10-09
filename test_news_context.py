import unittest
from datetime import datetime, timedelta, timezone
from news_context import calendar_events, blackout, release_items


class NewsTests(unittest.TestCase):
    def test_calendar_staleness_and_release_window(self):
        now = datetime(2026, 10, 9, 12, tzinfo=timezone.utc)
        payload = [{'country': 'USD', 'title': 'CPI', 'impact': 'High', 'date': now.isoformat()}]
        events = calendar_events(payload, now)
        self.assertEqual(len(blackout(events, now+timedelta(minutes=14))), 1)
        self.assertFalse(blackout(events, now+timedelta(minutes=16)))
        with self.assertRaises(ValueError):
            calendar_events(payload, now+timedelta(days=8))
        payload[0]['date'] = '2026-10-09T12:00:00'
        with self.assertRaises(ValueError):
            calendar_events(payload, now)

    def test_future_or_wrong_publisher_not_used(self):
        now = datetime(2026, 10, 9, 12, tzinfo=timezone.utc)
        xml = b'<rss><channel><item><title>CPI</title><link>https://www.bls.gov/news.release/cpi.htm</link><pubDate>Fri, 09 Oct 2026 11:30:00 GMT</pubDate></item></channel></rss>'
        self.assertEqual(len(release_items(xml, now)), 1)
        with self.assertRaises(ValueError):
            release_items(xml.replace(b'11:30:00', b'12:30:00'), now)
        with self.assertRaises(ValueError):
            release_items(xml.replace(b'www.bls.gov', b'example.com'), now)
