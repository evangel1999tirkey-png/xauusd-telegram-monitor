import unittest
from datetime import datetime,timezone
from official_surveys import parse


class OfficialSurveyChecks(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,12,tzinfo=timezone.utc)
        self.html='<h1>Preliminary Results for October 2026</h1><table id="front_table">'
        rows=[['','Oct','Sep'],['','2026','2026'],
              ['Index of Consumer Sentiment','46.3','48.1'],
              ['Current Economic Conditions','44.7','50.9'],
              ['Index of Consumer Expectations','47.3','46.3']]
        self.html+=''.join('<tr>'+''.join('<td>'+c+'</td>' for c in row)+'</tr>' for row in rows)+'</table>'
    def test_actual_columns_and_no_invented_consensus(self):
        r=parse(self.html,self.now)
        self.assertEqual(r['official_values']['sentiment']['actual'],46.3)
        self.assertEqual(r['official_values']['sentiment']['previous'],48.1)
        self.assertIsNone(r['market_consensus'])
        self.assertIsNone(r['publication_utc'])
        self.assertFalse(r['current_release_confirmation'])
    def test_changed_column_order_rejected(self):
        with self.assertRaises(ValueError):parse(self.html.replace('<td>Oct</td><td>Sep</td>',
                                                        '<td>Sep</td><td>Oct</td>'),self.now)
    def test_future_report_rejected(self):
        with self.assertRaises(ValueError):parse(self.html.replace('October 2026','November 2026'),self.now)
    def test_duplicate_indicator_rejected(self):
        with self.assertRaises(ValueError):parse(self.html.replace('Current Economic Conditions',
                                                        'Index of Consumer Sentiment'),self.now)


if __name__=='__main__':unittest.main()