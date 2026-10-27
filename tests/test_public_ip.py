"""Public address selection; network and process discovery are isolated fixtures."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('manager', Path(__file__).resolve().parents[1] / 'scripts/strynium_manager.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
PUBLIC = '47.238.131.32'


def result(output, code=0):
    return subprocess.CompletedProcess([], code, output, '')


class PublicIPTests(unittest.TestCase):
    def test_private_special_and_invalid_addresses_rejected(self):
        for ip in ('127.0.0.1', '0.0.0.0', '10.1.2.3', '172.16.1.1', '192.168.0.1',
                   '100.64.0.1', '169.254.1.1', '224.0.0.1', '240.0.0.1', '::1',
                   '198.18.0.1', '192.0.2.1', 'https://' + PUBLIC, PUBLIC + '\n1.1.1.1'):
            self.assertEqual(m.public_ipv4(ip), '', ip)
        self.assertEqual(m.public_ipv4(PUBLIC + '\n'), PUBLIC)

    def test_ssh_uses_server_not_administrator_address(self):
        with mock.patch.dict(m.os.environ, SSH_CONNECTION='1.1.1.1 2345 ' + PUBLIC + ' 22'), \
                mock.patch.object(m, 'metadata_text', side_effect=AssertionError('unneeded network call')):
            self.assertEqual(m.discover_public_ipv4(), PUBLIC)

    def test_private_ssh_address_falls_back_to_token_metadata(self):
        with mock.patch.dict(m.os.environ, SSH_CONNECTION='1.1.1.1 2345 10.0.0.1 22'), \
                mock.patch.object(m, 'metadata_text', side_effect=['test-token', PUBLIC]) as metadata:
            self.assertEqual(m.discover_public_ipv4(), PUBLIC)
        self.assertEqual(metadata.call_args_list[0].args[:2], ('api/token', 'PUT'))
        self.assertEqual(metadata.call_args_list[1].args[0], 'meta-data/eipv4')
        self.assertEqual(metadata.call_args_list[1].kwargs['headers']['X-aliyun-ecs-metadata-token'], 'test-token')

    def test_unavailable_eip_uses_static_public_metadata(self):
        with mock.patch.dict(m.os.environ, SSH_CONNECTION=''), \
                mock.patch.object(m, 'metadata_text', side_effect=['test-token', OSError(), PUBLIC]):
            self.assertEqual(m.discover_public_ipv4(), PUBLIC)

    def test_one_public_interface_can_be_used_without_external_query(self):
        interfaces = [{'addr_info': [{'local': '10.0.0.1'}, {'local': PUBLIC}]}]
        with mock.patch.dict(m.os.environ, SSH_CONNECTION=''), \
                mock.patch.object(m, 'metadata_text', side_effect=OSError()), \
                mock.patch.object(m.subprocess, 'run', return_value=result(json.dumps(interfaces))) as run:
            self.assertEqual(m.discover_public_ipv4(), PUBLIC)
            self.assertEqual(run.call_count, 1)

    def test_ambiguous_interfaces_do_not_pick_arbitrarily(self):
        interfaces = [{'addr_info': [{'local': '1.1.1.1'}, {'local': PUBLIC}]}]
        with mock.patch.dict(m.os.environ, SSH_CONNECTION=''), \
                mock.patch.object(m, 'metadata_text', side_effect=OSError()), \
                mock.patch.object(m.subprocess, 'run', return_value=result(json.dumps(interfaces))) as run:
            self.assertEqual(m.discover_public_ipv4(), '')
            self.assertEqual(run.call_count, 1)

    def test_https_observations_must_agree_and_bypass_proxies(self):
        for second, expected in [(PUBLIC, PUBLIC), ('1.1.1.1', ''), ('127.0.0.1', '')]:
            with mock.patch.dict(m.os.environ, SSH_CONNECTION=''), \
                    mock.patch.object(m, 'metadata_text', side_effect=OSError()), \
                    mock.patch.object(m.subprocess, 'run', side_effect=[result('[]'), result(PUBLIC), result(second)]) as run:
                self.assertEqual(m.discover_public_ipv4(), expected)
                for call in run.call_args_list[1:]:
                    args = call.args[0]
                    self.assertIn('--noproxy', args)
                    self.assertIn('--max-time', args)
                    self.assertIn('-4', args)
                    self.assertNotIn('--location', args)

    def test_timeout_returns_to_manual_fallback(self):
        with mock.patch.dict(m.os.environ, SSH_CONNECTION=''), \
                mock.patch.object(m, 'metadata_text', side_effect=TimeoutError()), \
                mock.patch.object(m.subprocess, 'run', side_effect=[result('[]'), subprocess.TimeoutExpired('curl', 5)]):
            self.assertEqual(m.discover_public_ipv4(), '')

    def test_detected_ip_never_prompts(self):
        with mock.patch.object(m, 'discover_public_ipv4', return_value=PUBLIC), \
                mock.patch.object(m, 'prompt', side_effect=AssertionError('unexpected IP prompt')):
            self.assertEqual(m.choose_public_ipv4(), PUBLIC)

    def test_fresh_server_state_automatically_uses_public_mode(self):
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.object(m, 'discover_public_ipv4', return_value=PUBLIC), \
                mock.patch.object(m, 'prompt', side_effect=AssertionError('unexpected IP prompt')), \
                mock.patch.object(m.pwd, 'getpwnam', return_value=m.pwd.getpwuid(m.os.getuid())), \
                mock.patch.object(m, 'random_port', side_effect=[45167, 45168]):
            state = m.Manager(Path(root)).new_state('server')
            self.assertEqual((state['mode'], state['public_ip'], state['port']), ('public-cloud', PUBLIC, 45167))

    def test_fallback_requires_ip_or_explicit_local(self):
        with mock.patch.object(m, 'discover_public_ipv4', return_value=''):
            for value, expected in [(PUBLIC, PUBLIC), ('local', '')]:
                with mock.patch.object(m, 'prompt', return_value=value):
                    self.assertEqual(m.choose_public_ipv4(), expected)
            for value in ('', '192.168.1.1'):
                with mock.patch.object(m, 'prompt', return_value=value), self.assertRaises(m.Error):
                    m.choose_public_ipv4()
            with mock.patch.object(m, 'prompt', return_value='local'), self.assertRaises(m.Error):
                m.choose_public_ipv4(allow_local=False)

    def test_metadata_redirect_is_rejected(self):
        with self.assertRaises(OSError):
            m.NoDiscoveryRedirect().redirect_request(None, None, 302, '', {}, 'https://example.com')

    def test_custom_address_and_certificate_are_not_overwritten(self):
        manager = m.Manager()
        old = dict(component='server', mode='local-only', public_ip='')
        for doc in [dict(web=dict(host_source='manual', access_host='example.com'), tls={}),
                    dict(web={}, tls=dict(certificate_path='/custom/cert.pem'))]:
            with mock.patch.object(manager, 'settings', return_value=doc), \
                    mock.patch.object(manager, 'systemctl', side_effect=AssertionError('must not stop')), \
                    self.assertRaises(m.Error):
                manager.set_public_address(old, PUBLIC)

    def test_matching_public_address_does_not_restart(self):
        manager = m.Manager()
        old = dict(component='server', mode='public-cloud', public_ip=PUBLIC)
        with mock.patch.object(manager, 'settings', return_value=dict(web={}, tls={})), \
                mock.patch.object(manager, 'show_url'), \
                mock.patch.object(manager, 'systemctl', side_effect=AssertionError('must not restart')):
            manager.set_public_address(old, PUBLIC)


if __name__ == '__main__':
    unittest.main(verbosity=2)
