import unittest
from copy import deepcopy
from signal_rules import Evidence, confirmed_bias, technical_evidence


def sample():
    five = [dict(o=100., h=102., l=98., c=100.) for _ in range(30)]
    five[-3:] = [dict(o=101., h=103., l=100., c=102.5),
                 dict(o=102.5, h=102.8, l=102., c=102.6),
                 dict(o=102.6, h=103.2, l=102.3, c=103.1)]
    fifteen = [dict(o=96+i*.2, h=98+i*.2, l=95+i*.2, c=97+i*.2)
               for i in range(30)]
    return five, fifteen


class ConfirmationTests(unittest.TestCase):
    def test_breakout_retest_and_higher_low(self):
        evidence = technical_evidence(*sample())
        self.assertEqual(evidence.direction, 'BUY')
        self.assertEqual(evidence.invalidation, 102.)

    def test_bearish_symmetry(self):
        def invert(rows):
            return [dict(o=200-b['o'], h=200-b['l'], l=200-b['h'], c=200-b['c']) for b in rows]
        five, fifteen = sample()
        self.assertEqual(technical_evidence(invert(five), invert(fifteen)).direction, 'SELL')

    def test_failed_retest_conflict_chasing_and_spike(self):
        for case in ('reclaim', 'conflict', 'chasing', 'spike'):
            five, fifteen = deepcopy(sample())
            if case == 'reclaim':
                five[-2]['c'] = 101.
            elif case == 'conflict':
                fifteen = list(reversed(fifteen))
            elif case == 'chasing':
                five[-1].update(c=109., h=110.)
            else:
                five[-1]['h'] = 120.
            with self.subTest(case=case):
                self.assertEqual(technical_evidence(five, fifteen).direction, 'NEUTRAL')

    def test_news_and_execution_guards(self):
        evidence = Evidence('BUY', 'synthetic evidence')
        confirmed = dict(verified_news_direction='BUY', reaction_verified=True,
                         data_fresh=True, high_impact_due=False, spread_ok=True)
        self.assertEqual(confirmed_bias(evidence), 'NEUTRAL')
        self.assertEqual(confirmed_bias(evidence, **confirmed), 'BUY')
        for key, value in [('verified_news_direction', 'SELL'), ('reaction_verified', False),
                           ('data_fresh', False), ('high_impact_due', True), ('spread_ok', False)]:
            with self.subTest(guard=key):
                self.assertEqual(confirmed_bias(evidence, **{**confirmed, key: value}), 'NEUTRAL')


if __name__ == '__main__':
    unittest.main()
