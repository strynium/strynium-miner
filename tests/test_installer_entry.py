"""Process-substitution regression in a disposable chroot; sudo/curl are fixtures.

Run as root on Linux. No host users, sudo rules, packages or services are changed.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

INSTALLER = Path(__file__).resolve().parents[1] / 'install.sh'


def copy_binary(root, path):
    destination = root / path.lstrip('/')
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)
    for library in re.findall(r'(/[^\s()]+)', subprocess.check_output(['ldd', path], text=True)):
        destination = root / library.lstrip('/')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(library, destination)


class EntryTests(unittest.TestCase):
    def run_entry(self, stream=True, ordinary=True, failure=None):
        self.assertEqual(os.geteuid(), 0, 'Run this isolated chroot test as root')
        with tempfile.TemporaryDirectory(prefix='strynium-entry-test-') as temporary:
            root = Path(temporary)
            root.chmod(0o755)
            for binary in ('/bin/bash', '/usr/bin/cat', '/usr/bin/cp', '/usr/bin/cmp', '/usr/bin/mktemp', '/usr/bin/rm', '/usr/bin/uname'):
                copy_binary(root, binary)
            (root / 'tmp').mkdir(mode=0o1777)
            (root / 'tmp').chmod(0o1777)
            (root / 'dev').mkdir()
            (root / 'dev/null').touch(); (root / 'dev/null').chmod(0o666)
            (root / 'dev/fd').symlink_to('/proc/self/fd')
            # Bash process substitution uses /dev/fd, requiring an isolated proc mount.
            (root / 'proc').mkdir()
            subprocess.run(['mount', '-t', 'proc', 'proc', str(root / 'proc')], check=True)
            try:
                (root / 'fixture').mkdir()
                # Exercise the unchanged platform checks and full elevation block,
                # stopping before package management to keep this regression isolated.
                source = INSTALLER.read_text().split('[[ -d /run/systemd/system ]]')[0] + 'echo ROOT_OK\n# FULL_SOURCE_MARKER\n'
                for target in ('install.sh', 'fixture/full.sh'):
                    (root / target).write_text(source); (root / target).chmod(0o644)
                curl = '''#!/bin/bash
[[ ! -f /fixture/download-fail ]] || exit 22
cp /fixture/full.sh "${@: -1}"
'''
                sudo = '''#!/bin/bash
[[ $1 == -- ]] || exit 80
shift
[[ $1 == bash ]] || exit 81
shift
script=$1
shift
[[ -f $script && $script == /tmp/strynium-elevate.*/install.sh ]] || exit 82
cmp -s -- "$script" /fixture/full.sh || exit 83
[[ $1 == --version ]] || exit 84
[[ ! -f /fixture/sudo-fail ]] || exit 7
echo SUDO_STAGED_OK
'''
                for name, text in [('curl', curl), ('sudo', sudo)]:
                    (root / ('usr/bin/' + name)).write_text(text)
                    (root / ('usr/bin/' + name)).chmod(0o755)
                if failure: (root / ('fixture/' + failure)).touch()
                expression = 'bash <(cat /install.sh) --version' if stream else 'bash /install.sh --version'
                args = ['chroot'] + (['--userspec=65534:65534'] if ordinary else [])
                result = subprocess.run(args + [str(root), '/bin/bash', '-c', expression], capture_output=True, text=True)
                expected = 22 if failure == 'download-fail' else 7 if failure else 0
                self.assertEqual(result.returncode, expected, result.stderr)
                if not failure:
                    self.assertIn('SUDO_STAGED_OK' if ordinary else 'ROOT_OK', result.stdout)
                self.assertEqual(list((root / 'tmp').iterdir()), [], 'Temporary elevated script must be cleaned up')
            finally:
                subprocess.run(['umount', str(root / 'proc')], check=True)

    def test_root_stream(self): self.run_entry(ordinary=False)
    def test_ordinary_user_stream_stages_complete_file(self): self.run_entry()
    def test_ordinary_user_saved_file(self): self.run_entry(stream=False)
    def test_download_failure_stops_and_cleans(self): self.run_entry(failure='download-fail')
    def test_sudo_failure_retains_exit_code_and_cleans(self): self.run_entry(failure='sudo-fail')


if __name__ == '__main__':
    unittest.main(verbosity=2)
