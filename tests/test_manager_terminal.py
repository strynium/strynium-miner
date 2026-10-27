"""Real Linux PTY regressions; menu filesystem writes use a temporary root."""
import importlib.util
import json
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

MANAGER = Path(__file__).resolve().parents[1] / 'scripts/strynium_manager.py'


def child(mode, root):
    spec = importlib.util.spec_from_file_location('manager', MANAGER)
    manager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manager)
    try:
        if mode == 'menu':
            instance = manager.Manager(Path(root), Path(root) / 'units')
            with mock.patch.object(manager, 'Manager', return_value=instance), \
                    mock.patch.object(manager, 'persist_manager'), \
                    mock.patch.object(sys, 'argv', ['manager.py']):
                manager.main()
        else:
            value = manager.prompt('TEST_PROMPT', 'default' if mode == 'default' else '', secret=mode == 'secret')
            print('SECRET_OK' if mode == 'secret' and value == 'Test-Secret-123!' else json.dumps(value), flush=True)
    except manager.Error as exc:
        print(str(exc), flush=True)
        return 1
    return 0


class TerminalTests(unittest.TestCase):
    def interact(self, mode, exchanges, stream=False, expected=0):
        with tempfile.TemporaryDirectory(prefix='strynium-terminal-') as temporary:
            args = [sys.executable, str(Path(__file__).resolve()), '--child', mode, temporary]
            if stream:
                # Match bash <(curl ...) descriptor semantics without a network dependency.
                launcher = Path(temporary) / 'entry.sh'
                launcher.write_text('exec "$@" </dev/null\n')
                args = ['bash', '-c', 'bash <(cat "$1") "${@:2}"', 'entry', str(launcher), *args]
            pid, master = pty.fork()
            if pid == 0:
                os.execvpe(args[0], args, dict(os.environ, PYTHONUNBUFFERED='1'))
            output = bytearray()
            cursor = 0
            finished = False
            try:
                for marker, reply in exchanges:
                    target = marker.encode()
                    deadline = time.monotonic() + 8
                    while target not in output[cursor:]:
                        self.assertLess(time.monotonic(), deadline, output.decode(errors='replace'))
                        if select.select([master], [], [], .1)[0]:
                            try:
                                data = os.read(master, 65536)
                            except OSError:
                                data = b''
                            self.assertTrue(data, output.decode(errors='replace'))
                            output.extend(data)
                    cursor = output.index(target, cursor) + len(target)
                    os.write(master, reply)
                deadline = time.monotonic() + 8
                while True:
                    ended, status = os.waitpid(pid, os.WNOHANG)
                    if ended:
                        finished = True
                        break
                    self.assertLess(time.monotonic(), deadline, output.decode(errors='replace'))
                    if select.select([master], [], [], .1)[0]:
                        try:
                            output.extend(os.read(master, 65536))
                        except OSError:
                            pass
                self.assertEqual(os.waitstatus_to_exitcode(status), expected, output.decode(errors='replace'))
                return output.decode(errors='replace')
            finally:
                if not finished:
                    os.kill(pid, signal.SIGKILL)
                    os.waitpid(pid, 0)
                os.close(master)

    def test_selection_reads_real_terminal(self):
        self.assertIn('"1"', self.interact('plain', [('TEST_PROMPT：', b'1\n')]))

    def test_enter_uses_default(self):
        self.assertIn('"default"', self.interact('default', [('TEST_PROMPT [default]：', b'\n')]))

    def test_password_input_is_not_echoed(self):
        output = self.interact('secret', [('TEST_PROMPT：', b'Test-Secret-123!\n')])
        self.assertIn('SECRET_OK', output)
        self.assertNotIn('Test-Secret-123!', output)

    def test_eof_cancels(self):
        self.assertIn('交互已取消', self.interact('plain', [('TEST_PROMPT：', b'\x04')], expected=1))

    def test_process_substitution_enters_both_menus_and_returns(self):
        output = self.interact('menu', [
            ('选择组件 [0]：', b'1\n'),
            ('选择操作 [0]：', b'0\n'),
            ('选择组件 [0]：', b'2\n'),
            ('选择操作 [0]：', b'0\n'),
            ('选择组件 [0]：', b'0\n'),
        ], stream=True)
        self.assertIn('10. 重置控制台账号密码', output)
        self.assertNotIn('此操作需要交互终端', output)

    def test_no_controlling_terminal_fails_clearly(self):
        result = subprocess.run([sys.executable, __file__, '--child', 'plain', '/unused'],
                                stdin=subprocess.DEVNULL, capture_output=True, text=True, start_new_session=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('此操作需要交互终端', result.stdout)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--child':
        sys.exit(child(sys.argv[2], sys.argv[3]))
    unittest.main(verbosity=2)
