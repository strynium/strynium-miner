"""Offline management safety regressions; run on Linux with Python 3.8+."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import ssl
import tempfile
import unittest
import urllib.request
from unittest import mock

spec = importlib.util.spec_from_file_location('manager', Path(__file__).resolve().parents[1] / 'scripts/strynium_manager.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / 'runtime'
        self.file = self.data / 'config/local_settings.json'
        self.file.parent.mkdir(parents=True)
        self.doc = dict(version=1, authentication=dict(username='old-admin', password_hash=m.INITIAL_HASH, state='UserSelectedV1'),
                        web=dict(web_port=8443, console_configured=True, route='console', access_host=''),
                        access=dict(enabled=True, secure_path='existing-path'),
                        totp=dict(enabled=True, secret_base32='ACCEPTANCE-ONLY', recovery_code_hashes=['keep-hash']),
                        tls=dict(certificate_path='/existing/identity'), custom_pools=[dict(id='keep-pool')],
                        client_identity=dict(uuid='keep-identity'), mp_tunnel=dict(devices=['keep-device']), security_events=[])
        self.file.write_text(json.dumps(self.doc))
        self.file.chmod(0o600)

    def tearDown(self):
        self.tmp.cleanup()

    def test_reset_preserves_enabled_totp_and_all_other_configuration(self):
        m.edit_settings(self.data, 'account', ('new-admin', m.INITIAL_HASH.replace('0Ct', '1Ct')))
        after = json.loads(self.file.read_text())
        for key in self.doc:
            if key not in ('authentication', 'security_events'):
                self.assertEqual(after[key], self.doc[key], key)
        self.assertEqual(after['authentication']['username'], 'new-admin')
        self.assertEqual(after['authentication']['state'], 'UserSelectedV1')
        self.assertEqual(self.file.stat().st_mode & 0o777, 0o600)

    def test_port_edit_preserves_route_access_and_authentication(self):
        m.edit_settings(self.data, 'port', 32123)
        after = json.loads(self.file.read_text())
        self.assertEqual(after['web'], dict(self.doc['web'], web_port=32123))
        self.assertEqual(after['authentication'], self.doc['authentication'])
        self.assertEqual(after['access'], self.doc['access'])

    def test_unknown_schema_and_permissive_file_fail_without_writing(self):
        for value, mode in [(dict(self.doc, version=2), 0o600), (self.doc, 0o644)]:
            self.file.write_text(json.dumps(value)); self.file.chmod(mode)
            before = self.file.read_bytes()
            with self.assertRaises(m.Error):
                m.edit_settings(self.data, 'port', 32123)
            self.assertEqual(before, self.file.read_bytes())

    def test_symlink_and_hardlink_settings_fail_without_writing(self):
        target = self.file.with_name('real.json')
        self.file.rename(target)
        for link in ('symlink', 'hardlink'):
            if link == 'symlink': self.file.symlink_to(target)
            else: os.link(target, self.file)
            before = target.read_bytes()
            with self.assertRaises(m.Error): m.load_settings(self.data)
            self.assertEqual(before, target.read_bytes())
            self.file.unlink()

    def test_replace_failure_keeps_original_file(self):
        before = self.file.read_bytes()
        with mock.patch.object(m.os, 'replace', side_effect=OSError('injected disk failure')):
            with self.assertRaises(OSError): m.edit_settings(self.data, 'port', 32123)
        self.assertEqual(before, self.file.read_bytes())
        self.assertEqual(list(self.file.parent.iterdir()), [self.file])

    def test_untrusted_redirect_never_followed(self):
        redirect = m.GitHubRedirect()
        req = urllib.request.Request('https://github.com/strynium/strynium-miner')
        for url in ['http://github.com/unsafe', 'https://attacker.example/payload', 'https://github.com:8443/file', 'https://user@github.com/file']:
            with self.assertRaises(m.Error): redirect.redirect_request(req, None, 302, '', {}, url)

    def test_credentials_and_session_links_redacted(self):
        raw = 'http://127.0.0.1:17892/#key=abc123\nSTB3.secret.payload.signature'
        text = m.redact(raw)
        self.assertNotIn('abc123', text)
        self.assertNotIn('secret.payload', text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
