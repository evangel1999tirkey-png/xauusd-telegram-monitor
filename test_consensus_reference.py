import copy
import json
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from consensus_reference import match,context

class NamedSurveyTests(unittest.TestCase):
    def setUp(self):
        self.ledger=json.loads(Path(__file__).with_name('verified_consensus.json').read_text())
        self.row={**self.ledger['records'][0],'actual':None,'provider_forecast':3.5}
        self.now=datetime(2026,10,13,11,tzinfo=timezone.utc)
        self.event=datetime.fromtimestamp(self.row['event_utc_epoch'],timezone.utc)
    def test_named_forecast_does_not_create_pre_release_surprise(self):
        result=match(self.row,self.ledger,self.now)
        self.assertTrue(result['named_consensus_verified'])
        self.assertEqual(result['market_consensus'],3.7)
        self.assertFalse(result['news_comparison_ready'])
        self.assertNotIn('surprise_vs_named_market_survey',result)
        text=context(self.now)
        self.assertIn('14 Oct 18:00 IST',text)
        self.assertIn('confirmation incomplete',text)
        self.assertNotIn('3.7',context(self.event+timedelta(minutes=31)))
    def test_actual_revision_and_publication_all_required(self):
        self.row.update(actual=3.8,official_actual_verified=True,
                        prior_revision_verified=True,official_publication_verified=True)
        result=match(self.row,self.ledger,self.event+timedelta(minutes=5))
        self.assertAlmostEqual(result['surprise_vs_named_market_survey'],.1)
        self.assertFalse(result['eligible_for_combined_bias'])
        for flag in ('official_actual_verified','prior_revision_verified','official_publication_verified'):
            row={**self.row,flag:False}
            self.assertFalse(match(row,self.ledger,self.event+timedelta(minutes=5))['news_comparison_ready'])
    def test_new_period_ambiguous_sources_and_expired_reference_rejected(self):
        row={**self.row,'period_server':'2026.10.01'}
        self.assertFalse(match(row,self.ledger,self.now)['named_consensus_verified'])
        ledger=copy.deepcopy(self.ledger);ledger['records'].append(copy.deepcopy(ledger['records'][0]))
        ledger['records'][-1]['market_consensus']=3.6
        self.assertFalse(match(self.row,ledger,self.now)['named_consensus_verified'])
        self.assertFalse(match(self.row,self.ledger,self.event+timedelta(minutes=31))['named_consensus_verified'])
    def test_missing_timezone_post_release_edit_and_nonfinite_value_rejected(self):
        for key,value in [('source_publication_utc','2026-10-09T10:06:00'),
                          ('source_updated_utc','2026-10-14T13:00:00+00:00'),
                          ('market_consensus',float('nan')),('full_text_verified',False)]:
            ledger=copy.deepcopy(self.ledger);ledger['records'][0][key]=value
            self.assertFalse(match(self.row,ledger,self.now)['named_consensus_verified'])

if __name__=='__main__':unittest.main()
