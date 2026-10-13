import copy
import unittest
from datetime import datetime,timezone
from official_bls import SERIES,parse

NOW=datetime(2026,10,13,tzinfo=timezone.utc)
def fixture():
    return {'status':'REQUEST_SUCCEEDED','message':[],
            'Results':{'series':[{'seriesID':k,'data':[
                {'year':'2026','period':'M08','value':'330.123','footnotes':[]}]
                } for k in SERIES]}}

class OfficialBlsTests(unittest.TestCase):
    def test_explicit_official_missing_history_remains_missing(self):
        p=fixture()
        p['Results']['series'][0]['data'].append({'year':'2025','period':'M10',
            'value':'-','footnotes':[{'code':'X','text':'Data unavailable due to lapse'}]})
        r=parse(p,NOW)
        self.assertEqual(r['missing_historical_periods']['headline_seasonally_adjusted'][0]['period'],'2025-10')
        p['Results']['series'][0]['data'][-1]['footnotes']=[]
        with self.assertRaises(ValueError):parse(p,NOW)

    def test_index_history_never_becomes_release_or_consensus(self):
        r=parse(fixture(),NOW)
        self.assertEqual(r['latest_period'],'2026-08')
        self.assertFalse(r['current_release_confirmation'])
        self.assertFalse(r['release_actual_verified'])
        self.assertIsNone(r['publication_utc']);self.assertIsNone(r['market_consensus'])
    def test_missing_duplicate_or_conflicting_series_rejected(self):
        for change in ('missing','duplicate','conflict'):
            p=fixture();rows=p['Results']['series']
            if change=='missing':rows.pop()
            elif change=='duplicate':rows.append(copy.deepcopy(rows[0]))
            else:rows[0]['data'][0]['period']='M09'
            with self.assertRaises(ValueError):parse(p,NOW)
    def test_stale_future_duplicate_or_nonfinite_values_rejected(self):
        for change in ('stale','future','duplicate','nan','negative'):
            p=fixture();rows=p['Results']['series'][0]['data'];r=rows[0]
            if change=='stale':r['period']='M01'
            elif change=='future':r['period']='M10'
            elif change=='duplicate':rows.append(copy.deepcopy(r))
            elif change=='nan':r['value']='NaN'
            else:r['value']='-1'
            with self.assertRaises(ValueError):parse(p,NOW)
    def test_error_response_never_promoted(self):
        p=fixture();p['message']=['Data truncated']
        with self.assertRaises(ValueError):parse(p,NOW)

if __name__=='__main__':unittest.main()
