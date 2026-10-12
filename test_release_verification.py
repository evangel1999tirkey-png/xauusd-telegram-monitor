import unittest
from datetime import datetime,timezone
from release_verification import verify_row


class ReleaseChecks(unittest.TestCase):
    def setUp(self):
        self.ref={'event_code':'claims','period_server':'2026.10.03','event_utc_epoch':1791462600,
                  'unit':0,'multiplier':1,'actual':197.,'previous':197.,'revised_previous':199.,
                  'market_consensus':200.,'consensus_source':'https://example.org/reuters',
                  'consensus_survey':'Reuters economist poll','official_source':'https://www.dol.gov/ui/data.pdf'}
        self.row={**self.ref,'provider_forecast':190.}

    def test_provider_forecast_does_not_reverse_survey_surprise(self):
        result=verify_row(self.row,{'records':[self.ref]},datetime(2026,10,12,tzinfo=timezone.utc))
        self.assertTrue(result['official_actual_verified'])
        self.assertEqual(result['surprise_vs_named_market_survey'],-3.)
        self.assertFalse(result['provider_forecast_is_consensus'])
        self.assertFalse(result['fresh_release'])
        self.assertFalse(result['eligible_for_combined_bias'])

    def test_new_reporting_period_cannot_reuse_old_actual(self):
        self.row['period_server']='2026.10.10'
        result=verify_row(self.row,{'records':[self.ref]},datetime(2026,10,12,tzinfo=timezone.utc))
        self.assertFalse(result['official_actual_verified'])

    def test_conflicting_actual_rejected(self):
        self.row['actual']=199.
        result=verify_row(self.row,{'records':[self.ref]},datetime(2026,10,12,tzinfo=timezone.utc))
        self.assertFalse(result['official_actual_verified'])
        self.assertNotIn('surprise_vs_named_market_survey',result)


if __name__=='__main__':unittest.main()