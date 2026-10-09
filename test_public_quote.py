import unittest
from datetime import datetime, timezone
from public_quote import validate_quote


class QuoteValidation(unittest.TestCase):
    def test_rejects_unusable_quotes(self):
        now = datetime(2026, 10, 9, 19, 14, 20, tzinfo=timezone.utc)
        good = dict(symbol='XAU', currency='USD', price=4199,
                    updatedAt='2026-10-09T19:14:10Z')
        self.assertEqual(validate_quote(good, now)[0], 4199)
        for change in (dict(symbol='XAG'), dict(currency='INR'),
                       dict(price=float('nan')), dict(price=-1),
                       dict(updatedAt='2026-10-09T19:10:00Z'),
                       dict(updatedAt='2026-10-09T19:15:00Z'),
                       dict(updatedAt='2026-10-09T19:14:10')):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_quote({**good, **change}, now)


if __name__ == '__main__':
    unittest.main()
