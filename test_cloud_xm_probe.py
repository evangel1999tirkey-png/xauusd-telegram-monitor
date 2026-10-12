import unittest
from unittest.mock import Mock,patch
import cloud_xm_probe


class CloudCredentialGate(unittest.TestCase):
    def test_no_authentication_before_specific_approval(self):
        mt=Mock();mt.__version__='test'
        with patch.dict('sys.modules',{'MetaTrader5':mt}),\
             patch.dict('os.environ',{'XM_TERMINAL_PATH':'test-terminal',
                        'BROKER_CLOUD_APPROVED':'0','XM_DEMO_LOGIN':'123',
                        'XM_DEMO_SERVER':'test','XM_INVESTOR_PASSWORD':'test-only'},clear=True),\
             patch.object(cloud_xm_probe.Path,'is_file',return_value=True):
            result=cloud_xm_probe.collect()
        self.assertEqual(result['status'],'CLOUD_RUNTIME_READY')
        mt.initialize.assert_not_called()

    def test_startup_failure_does_not_attempt_login(self):
        mt=Mock();mt.initialize.return_value=False
        mt.last_error.return_value=(-6,'private error detail')
        with patch.dict('sys.modules',{'MetaTrader5':mt}),\
             patch.dict('os.environ',{'XM_TERMINAL_PATH':'test-terminal',
                        'BROKER_CLOUD_APPROVED':'1','XM_DEMO_LOGIN':'123',
                        'XM_DEMO_SERVER':'test','XM_INVESTOR_PASSWORD':'test-only'},clear=True),\
             patch.object(cloud_xm_probe.Path,'is_file',return_value=True):
            result=cloud_xm_probe.collect()
        self.assertEqual(result['sdk_error_code'],-6)
        mt.login.assert_not_called()
        self.assertNotIn('private error detail',str(result))
        self.assertNotIn('test-only',str(result))

    def test_login_failure_does_not_read_quotes_or_expose_password(self):
        mt=Mock();mt.initialize.return_value=True;mt.login.return_value=False
        mt.last_error.return_value=(-6,'private error detail')
        with patch.dict('sys.modules',{'MetaTrader5':mt}),\
             patch.dict('os.environ',{'XM_TERMINAL_PATH':'test-terminal',
                        'BROKER_CLOUD_APPROVED':'1','XM_DEMO_LOGIN':'123',
                        'XM_DEMO_SERVER':'test','XM_INVESTOR_PASSWORD':'test-only'},clear=True),\
             patch.object(cloud_xm_probe.Path,'is_file',return_value=True),\
             patch.object(cloud_xm_probe,'probe') as quote_probe:
            result=cloud_xm_probe.collect()
        self.assertEqual(result['reason'],'broker_authentication_not_verified')
        quote_probe.assert_not_called()
        self.assertNotIn('private error detail',str(result))
        self.assertNotIn('test-only',str(result))
        self.assertNotIn('test-only',str(result))

    def test_missing_secret_does_not_attempt_login(self):
        mt=Mock()
        with patch.dict('sys.modules',{'MetaTrader5':mt}),\
             patch.dict('os.environ',{'XM_TERMINAL_PATH':'test-terminal',
                                    'BROKER_CLOUD_APPROVED':'1'},clear=True),\
             patch.object(cloud_xm_probe.Path,'is_file',return_value=True):
            result=cloud_xm_probe.collect()
        self.assertEqual(result['reason'],'encrypted_broker_secrets_missing')
        self.assertEqual(result['missing_secret_names'],
                         ['XM_DEMO_LOGIN','XM_DEMO_SERVER','XM_INVESTOR_PASSWORD'])
        mt.initialize.assert_not_called()


if __name__=='__main__':unittest.main()