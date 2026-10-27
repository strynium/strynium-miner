#!/usr/bin/env python3
"""Root-only deployment and offline maintenance for STRYNIUM R14/D11.

Runtime data and installed release directories are separate. This tool never
edits mining accounts, fee targets, TLS identities or TOTP enrollment.
"""
import argparse
import contextlib
import copy
import ctypes
import ctypes.util
import datetime
import fcntl
import getpass
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import platform
import pwd
import re
import resource
import secrets
import shlex
import shutil
import socket
import ssl
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request

VERSION = '1.0.1'
REPO = 'strynium/strynium-miner'
API = 'https://api.github.com/repos/' + REPO + '/releases/latest'
INITIAL_USER = 'strynium'
INITIAL_PASSWORD = 'Strynium2026.'
INITIAL_HASH = '$argon2id$v=19$m=19456,t=2,p=1$FkGWx2GWocm4HgR0/v3Ofw$0Ct/cWeqCVLxAxBUU85UJ9wm0Bi16MiQjrkLikyvs/0'
LABEL = {'server': '服务端', 'local': '本地加密端'}


class Error(Exception):
    pass


def command(args, check=True, capture=True):
    result = subprocess.run([str(a) for a in args], stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.PIPE if capture else None, text=True)
    if check and result.returncode:
        # No command arguments or full service logs: these may include secrets.
        raise Error(f'{Path(args[0]).name} 执行失败（退出码 {result.returncode}）')
    return result


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')


def prompt(text, default='', secret=False):
    try:
        with open('/dev/tty', 'r+') as tty:
            if secret:
                return getpass.getpass(text + '：', stream=tty)
            tty.write(text + (f' [{default}]' if default else '') + '：')
            tty.flush()
            value = tty.readline()
            if not value:
                raise Error('交互已取消')
            return value.strip() or default
    except OSError as exc:
        raise Error('此操作需要交互终端，请直接运行 sudo strynium-manage') from exc


def confirm(text):
    if prompt(text + '，输入 yes 继续', 'no').lower() != 'yes':
        raise Error('已取消，未继续操作')


def safe_path(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or any(c in str(path) for c in '\n\r\0'):
        raise Error('目录必须是无换行的绝对路径')
    for item in [path, *path.parents]:
        if item.is_symlink():
            raise Error('维护目录不能包含符号链接：' + str(item))
    return path


def safe_data(path):
    path = safe_path(path)
    if len(path.parts) < 4 or path in (Path('/usr/local/lib'), Path('/var/lib/systemd')):
        raise Error('拒绝使用系统根目录作为应用数据目录')
    return path


def atomic_bytes(path, data, uid=0, gid=0, mode=0o600):
    path = safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        os.fchmod(fd, mode)
        os.fchown(fd, uid, gid)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def atomic_json(path, value, uid=0, gid=0):
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode(), uid, gid)


def load_settings(data_home):
    path = safe_data(data_home) / 'config/local_settings.json'
    safe_path(path)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077:
        raise Error('登录配置必须是私有普通文件（0600），不能是链接')
    if info.st_size > 4 * 1024 * 1024:
        raise Error('登录配置异常大，拒绝修改')
    value = json.loads(path.read_text())
    if value.get('version') != 1 or not all(isinstance(value.get(k), dict) for k in ('web', 'authentication', 'access', 'totp')):
        raise Error('不支持的服务端配置格式，未修改文件')
    auth = value['authentication']
    if not isinstance(auth.get('password_hash'), str) or not auth['password_hash'].startswith('$argon2id$'):
        raise Error('账号密码格式不兼容，未修改文件')
    return path, value, info


@contextlib.contextmanager
def offline_lock(data_home):
    path = safe_data(data_home) / 'console-owner.lock'
    safe_path(path)
    fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(fd)
        raise Error('另一个服务端进程仍在使用此数据目录，拒绝离线修改') from exc
    try:
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def validate_password(username, password):
    if not re.fullmatch(r'[A-Za-z0-9_.-]{3,64}', username):
        raise Error('账号须为 3–64 位字母、数字或 . _ -')
    encoded = password.encode()
    if not (8 <= len(encoded) <= 1024 and re.search('[A-Z]', password) and re.search('[a-z]', password)
            and re.search('[0-9]', password) and any(not (65 <= b <= 90 or 97 <= b <= 122 or 48 <= b <= 57) for b in encoded)):
        raise Error('密码至少 8 位，并包含大小写字母、数字和特殊字符')
    if password == INITIAL_PASSWORD:
        raise Error('新密码不能使用公开初始密码')


def argon_library():
    name = ctypes.util.find_library('argon2')
    if not name:
        raise Error('缺少 libargon2；Ubuntu/Debian 安装 libargon2-1，Fedora/RHEL 安装 libargon2，Arch 安装 argon2')
    lib = ctypes.CDLL(name)
    lib.argon2id_hash_encoded.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,
        ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t,
        ctypes.c_size_t, ctypes.c_char_p, ctypes.c_size_t]
    lib.argon2id_hash_encoded.restype = ctypes.c_int
    return lib


def hash_password(password):
    lib = argon_library()
    raw = password.encode()
    buf = ctypes.create_string_buffer(raw)
    salt = ctypes.create_string_buffer(secrets.token_bytes(16), 16)
    out = ctypes.create_string_buffer(512)
    try:
        code = lib.argon2id_hash_encoded(2, 19456, 1, buf, len(raw), salt, 16, 32, out, len(out))
        if code != 0:
            raise Error('密码哈希生成失败，未修改文件')
        return out.value.decode('ascii')
    finally:
        ctypes.memset(buf, 0, len(buf))


def edit_settings(data_home, operation, value):
    path, doc, info = load_settings(data_home)
    if operation == 'port':
        if not isinstance(value, int) or not 1024 <= value <= 65535:
            raise Error('Web 端口须为 1024–65535')
        doc['web']['web_port'] = value
        doc['web']['console_configured'] = True
        event = 'console_port_changed_by_local_administrator'
    elif operation == 'account':
        username, encoded_hash = value
        if not re.fullmatch(r'[A-Za-z0-9_.-]{3,64}', username) or not encoded_hash.startswith('$argon2id$v=19$m=19456,t=2,p=1$'):
            raise Error('无效的新账号凭据')
        doc['authentication'].update(username=username, password_hash=encoded_hash,
                                     state='UserSelectedV1', updated_at=now())
        event = 'administrator_credentials_reset_by_local_administrator'
    else:
        raise Error('不支持的离线操作')
    doc['updated_at'] = now()
    events = doc.setdefault('security_events', [])
    events.append({'event': event, 'occurred_at': doc['updated_at']})
    doc['security_events'] = events[-128:]
    atomic_json(path, doc, info.st_uid, info.st_gid)


def port_free(port, host='0.0.0.0'):
    try:
        with socket.socket() as sock:
            sock.bind((host, port))
            return True
    except OSError:
        return False


def random_port(exclude=()):
    for _ in range(256):
        candidate = secrets.randbelow(40001) + 20000
        if candidate not in exclude and port_free(candidate):
            return candidate
    raise Error('未找到可用随机端口')


class GitHubRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)
        if parsed.scheme != 'https' or parsed.username or parsed.port not in (None, 443) or parsed.hostname not in (
                'github.com', 'api.github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'):
            raise Error('下载重定向到非预期地址')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, destination=None, limit=256 * 1024 * 1024):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname not in ('api.github.com', 'github.com') or parsed.username:
        raise Error('拒绝非官方 HTTPS 下载地址')
    req = urllib.request.Request(url, headers={'User-Agent': 'STRYNIUM-Manager/' + VERSION, 'Accept': 'application/vnd.github+json'})
    with urllib.request.build_opener(GitHubRedirect()).open(req, timeout=45) as response:
        redirected = urllib.parse.urlparse(response.geturl())
        if redirected.scheme != 'https' or not (redirected.hostname in ('github.com', 'api.github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com')):
            raise Error('下载重定向到非预期地址')
        if destination is None:
            raw = response.read(limit + 1)
            if len(raw) > limit:
                raise Error('下载文件超过大小上限')
            return raw
        total = 0
        with open(destination, 'xb') as out:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > limit:
                    raise Error('下载文件超过大小上限')
                out.write(block)


def release_asset(component):
    release = json.loads(fetch(API, limit=2 * 1024 * 1024))
    if release.get('draft') or release.get('prerelease'):
        raise Error('不是正式发布版本')
    tag = release['tag_name']
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', tag):
        raise Error('发布版本名不合法')
    matches = [a for a in release['assets'] if re.fullmatch(r'STRYNIUM-[A-Za-z0-9.-]+-MANIFEST\.json', a['name'])]
    if len(matches) != 1:
        raise Error('正式发布缺少唯一软件包清单')
    if matches[0]['browser_download_url'] != f'https://github.com/{REPO}/releases/download/{tag}/{matches[0]["name"]}':
        raise Error('发布清单不属于本仓库当前发布')
    manifest = json.loads(fetch(matches[0]['browser_download_url'], limit=1024 * 1024))
    if manifest.get('release') != tag:
        raise Error('发布清单的版本不匹配')
    selected = [a for a in manifest['assets'] if a.get('component') == component and
                re.fullmatch(r'STRYNIUM-(?:Server|Local)-Linux-x64-[A-Za-z0-9.-]+\.tar\.gz', a['name'])]
    if len(selected) != 1:
        raise Error('发布缺少此组件的 Linux x64 软件包')
    asset = selected[0]
    if not re.fullmatch('[0-9a-f]{64}', asset.get('sha256', '')) or not 0 < asset['bytes'] <= 256 * 1024 * 1024:
        raise Error('无效的软件包校验清单')
    remote = next((a for a in release['assets'] if a['name'] == asset['name']), None)
    if remote is None or remote['size'] != asset['bytes']:
        raise Error('发布文件与清单不一致')
    expected_url = f'https://github.com/{REPO}/releases/download/{tag}/{asset["name"]}'
    if remote['browser_download_url'] != expected_url:
        raise Error('软件包不属于本仓库当前发布')
    return dict(asset, tag=tag, url=expected_url)


def unpack_verified(archive, target, asset):
    if archive.stat().st_size != asset['bytes'] or hashlib.sha256(archive.read_bytes()).hexdigest() != asset['sha256']:
        raise Error('软件包 SHA-256 或大小不符，拒绝安装')
    total = 0
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        if len(members) > 20000:
            raise Error('软件包文件数量异常')
        for m in members:
            p = Path(m.name)
            if p.is_absolute() or '..' in p.parts or '\\' in m.name or not (m.isfile() or m.isdir()):
                raise Error('软件包包含不安全路径、链接或特殊文件')
            total += m.size
            if total > 512 * 1024 * 1024:
                raise Error('解压大小超过上限')
        roots = {Path(m.name).parts[0] for m in members if Path(m.name).parts}
        if len(roots) != 1:
            raise Error('软件包顶层目录异常')
        for m in members:
            out = target / m.name
            if m.isdir():
                out.mkdir(parents=True, exist_ok=True)
                out.chmod(0o755)
            else:
                out.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(m) as src, out.open('xb') as dst:
                    shutil.copyfileobj(src, dst)
                out.chmod(0o755 if m.mode & 0o111 else 0o644)
    package = target / next(iter(roots))
    required_files = ['THIRD-PARTY-LICENSES.txt', 'SHA256SUMS.txt', 'licenses']
    if package.name.startswith('STRYNIUM-Local-'):
        required_files += ['LICENSE.txt', 'USE_TERMS.md']
    for required in required_files:
        if not (package / required).exists():
            raise Error('软件包缺少许可证或校验文件')
    # Verify every internal checksum, rejecting traversal even though extraction is bounded.
    for line in (package / 'SHA256SUMS.txt').read_text().splitlines():
        digest, relative = line.split(None, 1)
        relative = relative.strip().lstrip('*')
        item = package / relative
        try:
            item.resolve().relative_to(package.resolve())
        except ValueError as exc:
            raise Error('软件包内部校验路径无效') from exc
        if not re.fullmatch('[0-9a-fA-F]{64}', digest):
            raise Error('软件包内部校验路径无效')
        if not item.is_file() or hashlib.sha256(item.read_bytes()).hexdigest() != digest.lower():
            raise Error('软件包内部文件校验失败')
    return package


def redact(text):
    text = re.sub(r'(#key=)[^\s]+', r'\1[已隐藏]', text)
    text = re.sub(r'STB[0-9]\.[A-Za-z0-9_.=-]+', '[授权已隐藏]', text)
    return text


class LoopbackHTTPS(http.client.HTTPSConnection):
    """Verify the configured certificate name while connecting over loopback."""
    def connect(self):
        raw = socket.create_connection(('127.0.0.1', self.port), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


class Manager:
    # Alternate directories/unit names are dependency injection for isolated tests;
    # the public CLI always uses the fixed default locations below.
    def __init__(self, root=Path('/'), unit_dir=Path('/etc/systemd/system'), unit_names=None):
        self.root = Path(root)
        self.config = self.root / 'etc/strynium-manager'
        self.packages = self.root / 'opt/strynium-managed'
        self.backups = self.root / 'var/backups/strynium-manager'
        self.unit_dir = Path(unit_dir)
        self.units = unit_names or {'server': 'strynium.service', 'local': 'strynium-local.service'}

    def init_dirs(self):
        for directory in (self.config, self.backups):
            safe_path(directory).mkdir(parents=True, exist_ok=True, mode=0o700)
            directory.chmod(0o700)
        safe_path(self.packages).mkdir(parents=True, exist_ok=True, mode=0o755)
        self.packages.chmod(0o755)

    def state_path(self, component):
        return self.config / (component + '.json')

    def load(self, component):
        path = self.state_path(component)
        if path.exists():
            safe_path(path)
            state = json.loads(path.read_text())
            if state.get('component') != component or state.get('schema') != 1:
                raise Error('管理器状态文件不兼容')
            safe_data(state['data'])
            return state
        return None

    def save(self, state):
        atomic_json(self.state_path(state['component']), state)

    def systemctl(self, *args, check=True):
        if args and args[0] in ('start', 'restart'):
            # An explicit maintenance action may follow several short restarts.
            # Clear systemd's previous start-limit before this requested attempt.
            command(['systemctl', 'reset-failed', *args[1:]], check=False)
        return command(['systemctl', *args], check=check)

    def properties(self, component):
        response = self.systemctl('show', self.units[component], '--property=LoadState,User,Group,FragmentPath,Environment,EnvironmentFiles,ExecStart,ActiveState,MainPID', check=False)
        return dict(line.split('=', 1) for line in response.stdout.splitlines() if '=' in line)

    def active(self, component):
        return self.systemctl('is-active', '--quiet', self.units[component], check=False).returncode == 0

    def settings(self, state):
        return load_settings(state['data'])[1] if state['component'] == 'server' else None

    def effective_port(self, state):
        if state['component'] == 'server':
            d = self.settings(state)
            if d['web'].get('console_configured'):
                return d['web']['web_port']
        return state['port']

    def adopt(self, component):
        props = self.properties(component)
        if props.get('LoadState') != 'loaded':
            return None
        executable = re.search(r'\bpath=([^ ;]+)', props.get('ExecStart', ''))
        if component != 'server' or not executable or executable[1] not in ('/usr/bin/strynium', '/opt/strynium/scripts/start-console.sh'):
            raise Error('发现非本管理器的服务，请先核对现有部署，拒绝覆盖：' + self.units[component])
        if props.get('EnvironmentFiles'):
            raise Error('现有服务使用外部 EnvironmentFile；需先明确数据目录，不自动接管')
        env = dict(x.split('=', 1) for x in shlex.split(props.get('Environment', '')) if '=' in x)
        data = safe_data(env.get('STRYNIUM_DATA_HOME', '/var/lib/strynium'))
        _, doc, info = load_settings(data)
        user = props.get('User') or 'root'
        if pwd.getpwnam(user).pw_uid != info.st_uid:
            raise Error('服务运行用户与数据所有者不符，拒绝接管')
        mode = env.get('STRYNIUM_CONSOLE_MODE', 'local-only')
        if mode not in ('local-only', 'public-cloud'):
            raise Error('现有服务访问模式不兼容')
        state = dict(schema=1, component=component, user=user, data=str(data),
            port=doc['web']['web_port'] if doc['web'].get('console_configured') else int(env.get('STRYNIUM_CONSOLE_HTTPS_PORT', 8443)),
            api_port=int(env.get('STRYNIUM_API_PORT', 18080)), mode=mode,
            public_ip=env.get('STRYNIUM_CONSOLE_PUBLIC_IP', ''), adopted=True, installed=False,
            certificate_bundle=env.get('STRYNIUM_CONSOLE_CERTIFICATE_BUNDLE', ''),
            original_fragment=props['FragmentPath'], tag=None)
        print(f'发现已有服务：{self.units[component]}；用户 {user}；数据 {data}。')
        confirm('接管程序更新，保留原服务配置、端口和数据')
        return state

    def new_state(self, component):
        if component == 'server':
            user = 'strynium'
            try:
                pwd.getpwnam(user)
            except KeyError:
                command(['useradd', '--system', '--user-group', '--home-dir', '/var/lib/strynium', '--shell', '/usr/sbin/nologin', user])
            data = self.root / 'var/lib/strynium'
            if data.exists() and any(data.iterdir()):
                raise Error('发现已有数据但没有可识别服务；拒绝以全新安装覆盖，请先检查服务配置')
            public_ip = prompt('服务器公网 IPv4（留空仅本机管理）')
            if public_ip:
                try:
                    ip = ipaddress.IPv4Address(public_ip)
                    if not ip.is_global:
                        raise ValueError()
                except ValueError as exc:
                    raise Error('请输入有效公网 IPv4；仅本机运行请留空') from exc
            port = random_port()
            api_port = random_port((port,))
        else:
            default = os.environ.get('SUDO_USER', '')
            if default == 'root':
                default = ''
            user = prompt('本地端运行用户（现有普通 Linux 用户）', default)
            try:
                account = pwd.getpwnam(user)
            except KeyError as exc:
                raise Error('用户不存在') from exc
            if account.pw_uid == 0 or not Path(account.pw_dir).is_dir():
                raise Error('本地端需要具有主目录的普通用户')
            data = Path(prompt('本地端数据目录（已有客户端请填写原路径）', str(Path(account.pw_dir) / '.local/state/STRYNIUM/LocalEncryption')))
            port = 17892
            if not port_free(port, '127.0.0.1'):
                raise Error('本地端 17892 已占用，请先退出原客户端，避免重复启动')
            public_ip = '';api_port = None
        data = safe_data(data)
        account = pwd.getpwnam(user)
        if data.exists() and data.stat().st_uid != account.pw_uid:
            raise Error('数据目录所有者不匹配，拒绝自动改变现有数据权限')
        return dict(schema=1, component=component, user=user, data=str(data), port=port, api_port=api_port,
                    mode='public-cloud' if public_ip else 'local-only', public_ip=public_ip,
                    adopted=False, installed=False, tag=None)

    def current(self, component):
        return self.packages / component / 'current'

    def binary(self, component):
        return self.current(component) / ('strynium-server' if component == 'server' else 'strynium-local')

    def unit_file(self, state):
        if state['adopted']:
            return self.unit_dir / (self.units[state['component']] + '.d/90-strynium-manager.conf')
        return self.unit_dir / self.units[state['component']]

    def write_unit(self, state):
        component = state['component']
        def quote(s):
            return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%') + '"'
        args = [self.binary(component)]
        if component == 'server':
            args += ['--profile', 'packaged', '--package-home', self.current(component), '--data-home', state['data'], '--api-bind', '127.0.0.1:' + str(state['api_port'])]
        else:
            args += ['--no-browser', '--port', str(state['port']), '--data-home', state['data']]
        exec_line = 'ExecStart=' + ' '.join(quote(a) for a in args) + '\n'
        if state['adopted']:
            content = '[Service]\nExecStart=\n' + exec_line
        else:
            account = pwd.getpwnam(state['user'])
            env = {'HOME': account.pw_dir, 'STRYNIUM_NO_BROWSER': '1', 'STRYNIUM_NO_PAUSE': '1'}
            if component == 'server':
                env.update(STRYNIUM_CONSOLE_MODE=state['mode'], STRYNIUM_CONSOLE_HTTPS_PORT=str(state['port']))
                if state['public_ip']:
                    env['STRYNIUM_CONSOLE_PUBLIC_IP'] = state['public_ip']
            content = '[Unit]\nDescription=STRYNIUM ' + LABEL[component] + '\nWants=network-online.target\nAfter=network-online.target\n\n[Service]\nType=simple\nUser=' + state['user'] + '\n'
            content += ''.join('Environment=' + quote(k + '=' + v) + '\n' for k, v in env.items())
            content += exec_line + 'Restart=on-failure\nRestartSec=3\nLimitNOFILE=65536\nLimitCORE=0\nUMask=0077\n'
            if component == 'local':
                content += 'LimitMEMLOCK=infinity\n'
            content += '\n[Install]\nWantedBy=multi-user.target\n'
        atomic_bytes(self.unit_file(state), content.encode(), mode=0o644)
        self.systemctl('daemon-reload')

    def switch(self, component, target):
        current = self.current(component)
        if current.exists() and not current.is_symlink():
            raise Error('版本指针不是管理器链接，拒绝覆盖')
        link = current.with_name('.current-' + secrets.token_hex(8))
        link.symlink_to(target)
        os.replace(link, current)

    def snapshot(self, state):
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-') + secrets.token_hex(4)
        backup = self.backups / (state['component'] + '-' + stamp)
        backup.mkdir(mode=0o700)
        data = safe_data(state['data'])
        if data.exists():
            # Store application-owned data only. Never follow links into other trees.
            if any(p.is_symlink() for p in data.rglob('*')):
                raise Error('数据目录中存在符号链接，停止备份以避免误读其他目录')
            command(['tar', '--numeric-owner', '-cpf', backup / 'data.tar', '-C', data.parent, '--', data.name])
        atomic_json(backup / 'state.json', state)
        unit = self.unit_file(state)
        if unit.exists():
            atomic_bytes(backup / 'unit.conf', unit.read_bytes())
        return backup

    def health_once(self, state):
        port = self.effective_port(state)
        if state['component'] == 'local':
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
            try:
                conn.request('GET', '/')
                response = conn.getresponse()
                return response.status == 200 and b'STRYNIUM' in response.read(1024 * 1024)
            finally:
                conn.close()
        data = Path(state['data'])
        public = state.get('public_ip')
        doc = self.settings(state)
        certificate_path = doc.get('tls', {}).get('certificate_path')
        name = public or '127.0.0.1'
        if state.get('certificate_bundle'):
            # The server validates the managed public certificate; retain CA and
            # hostname checks here as well, without sending traffic to its WAN IP.
            context = ssl.create_default_context()
        elif certificate_path:
            context = ssl.create_default_context(cafile=str(safe_path(certificate_path)))
            if doc['web'].get('host_source') == 'manual':
                name = doc['web'].get('access_host') or name
        else:
            identity = data / ('console-tls-public/' + public + '/identity.json' if public else 'console-tls/identity.json')
            document = json.loads(identity.read_text())
            certificate = ssl.DER_cert_to_PEM_cert(bytes(document['certificate']))
            context = ssl.create_default_context(cadata=certificate)
        base = ('/' + doc['access']['secure_path']) if doc['access'].get('enabled') else ''
        route = doc['web'].get('route', '')
        if route and not route.startswith('#'):
            base += '/' + route.strip('/')
        conn = LoopbackHTTPS(name, port, context=context, timeout=2)
        try:
            conn.request('GET', base + '/api/health')
            response = conn.getresponse()
            return response.status == 200 and bool(json.loads(response.read(1024 * 1024)))
        finally:
            conn.close()

    def wait_health(self, state, seconds=35):
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            try:
                if self.active(state['component']) and self.health_once(state):
                    return
            except (OSError, ValueError, KeyError, Error, http.client.HTTPException):
                pass
            time.sleep(.5)
        raise Error('服务未通过本机健康检查，请使用日志/诊断查看原因')

    def restore_snapshot(self, state, backup):
        data = safe_data(state['data'])
        if (backup / 'data.tar').exists():
            if data.exists():
                failed = data.with_name(data.name + '.failed-' + secrets.token_hex(5))
                data.rename(failed)
                print('失败现场已保留：' + str(failed))
            command(['tar', '--same-owner', '-xpf', backup / 'data.tar', '-C', data.parent])
        unit = self.unit_file(state)
        if (backup / 'unit.conf').exists():
            atomic_bytes(unit, (backup / 'unit.conf').read_bytes(), mode=0o644)
        elif unit.exists():
            unit.unlink()
        self.systemctl('daemon-reload')

    def install(self, component, state=None, asset=None):
        self.init_dirs()
        old = self.load(component)
        state = old or state or self.adopt(component) or self.new_state(component)
        asset = asset or release_asset(component)
        if old and old.get('installed') and old.get('tag') == asset['tag']:
            print('已经是当前正式版本：' + asset['tag']);return
        print(f'下载 {LABEL[component]} {asset["tag"]}，校验后安装。')
        releases = self.packages / component / 'releases'
        releases.mkdir(parents=True, exist_ok=True)
        releases.parent.chmod(0o755)
        releases.chmod(0o755)
        target = releases / (asset['tag'] + '-' + asset['sha256'][:12])
        with tempfile.TemporaryDirectory(prefix='.download-', dir=releases) as temporary:
            work = Path(temporary)
            archive = work / 'package.tar.gz'
            fetch(asset['url'], archive)
            package = unpack_verified(archive, work / 'extracted', asset)
            binary = package / ('strynium-server' if component == 'server' else 'strynium-local')
            if not binary.is_file() or not os.access(binary, os.X_OK):
                raise Error('软件包缺少可执行程序')
            command([binary, '--version'])
            if target.exists():
                # Interrupted download/reinstall: verify existing bytes before reuse.
                if (target / binary.name).read_bytes() != binary.read_bytes():
                    raise Error('已有版本目录不匹配，拒绝覆盖')
            else:
                shutil.move(package, target)
        account = pwd.getpwnam(state['user'])
        data = safe_data(state['data'])
        fresh = not (data / 'config/local_settings.json').exists() if component == 'server' else not data.exists()
        missing = []
        parent = data
        while not parent.exists():
            missing.append(parent);parent = parent.parent
        data.mkdir(parents=True, exist_ok=True, mode=0o700)
        for directory in missing:
            # Do not leave root-owned 0700 parents in an ordinary user's home.
            os.chown(directory, account.pw_uid, account.pw_gid)
            directory.chmod(0o700)
        if data.stat().st_uid not in (0, account.pw_uid) or (not fresh and data.stat().st_uid != account.pw_uid):
            raise Error('数据目录所有者不匹配')
        if fresh:
            os.chown(data, account.pw_uid, account.pw_gid);data.chmod(0o700)
        was_active = self.active(component)
        previous = self.current(component).resolve() if self.current(component).is_symlink() else None
        if self.properties(component).get('LoadState') == 'loaded':
            self.systemctl('stop', self.units[component])
        backup = None
        try:
            if component == 'server' and (data / 'console-owner.lock').exists():
                with offline_lock(data):
                    backup = self.snapshot(state)
            else:
                backup = self.snapshot(state)
            self.switch(component, target)
            self.write_unit(state)
            # New installs start; an explicitly stopped existing managed service stays stopped.
            should_start = was_active or (not state['adopted'] and (not old or not old.get('installed')))
            if should_start:
                self.systemctl('start', self.units[component]);self.wait_health(state)
            if not old and not state['adopted']:
                self.systemctl('enable', self.units[component])
            state.update(installed=True, tag=asset['tag'], build=asset['build'], backup=str(backup), updated_at=now())
            self.save(state)
        except BaseException:
            self.systemctl('stop', self.units[component], check=False)
            if not old and not state['adopted']:
                self.systemctl('disable', self.units[component], check=False)
            if backup:
                self.restore_snapshot(state, backup)
            if previous:
                self.switch(component, previous)
            elif self.current(component).is_symlink():
                self.current(component).unlink()
            if was_active:
                self.systemctl('start', self.units[component], check=False)
            raise
        print('安装/更新完成；备份：' + str(backup))
        self.status(component)
        if fresh and component == 'server':
            print(f'初始账号：{INITIAL_USER}\n初始密码：{INITIAL_PASSWORD}\n首次登录必须修改账号和密码；以上公开初始凭据不能作为日常登录凭据。')
        if component == 'local':
            print('本地端服务开机只启动控制台；重启后仍需在页面解锁凭据并应用转发。')
            self.console(component)

    def require_state(self, component):
        state = self.load(component)
        if not state or not state.get('installed'):
            raise Error('此组件尚未由管理器安装；先选择安装/接管')
        return state

    def status(self, component):
        state = self.require_state(component)
        print(f'{LABEL[component]}：{state.get("build", "未知")} / {state["tag"]}')
        print('进程：' + ('运行中' if self.active(component) else '已停止'))
        print('运行用户：' + state['user'] + '\n数据目录：' + state['data'])
        self.show_url(state)

    def show_url(self, state):
        port = self.effective_port(state)
        if state['component'] == 'local':
            print(f'本机控制台：http://127.0.0.1:{port}/（完整登录链接见“打开控制台”）');return
        d = self.settings(state)
        host = d['web']['access_host'] if d['web'].get('host_source') == 'manual' else state.get('public_ip') or '127.0.0.1'
        base = '/' + d['access']['secure_path'] if d['access'].get('enabled') else ''
        route = d['web'].get('route') or ''
        url = f'https://{host}:{port}{base}/' + (route if route.startswith('#') else route.strip('/'))
        print('Web 访问地址：' + url)
        print(f'请按需要在云安全组/防火墙放行 TCP {port}；脚本不修改防火墙。')

    def lifecycle(self, component, action):
        state = self.require_state(component)
        self.systemctl(action, self.units[component])
        if action in ('start', 'restart'):
            self.wait_health(state)
        self.status(component)

    def console(self, component):
        state = self.require_state(component)
        if component == 'server':
            self.show_url(state);return
        if not self.active(component):
            raise Error('本地端已停止，请先启动')
        since = self.systemctl('show', self.units[component], '--property=ActiveEnterTimestamp', '--value').stdout.strip()
        logs = command(['journalctl', '-u', self.units[component], '--since', since, '-n', '100', '--no-pager', '-o', 'cat']).stdout
        links = re.findall(r'http://127\.0\.0\.1:\d+/[^\s]*#key=[A-Za-z0-9_-]+', logs)
        if not links:
            raise Error('未找到本次启动的控制台链接，请检查服务日志')
        print('仅在你自己的管理电脑打开，不要公开此会话链接：\n' + links[-1])
        print(f'远程访问可用 SSH 转发：ssh -L {state["port"]}:127.0.0.1:{state["port"]} 用户@矿场电脑')

    def logs(self, component):
        self.require_state(component)
        text = command(['journalctl', '-u', self.units[component], '-n', '100', '--no-pager', '-o', 'short-iso']).stdout
        print(redact(text))

    def diagnose(self, component):
        state = self.require_state(component)
        self.status(component)
        print('程序存在：' + str(self.binary(component).is_file()))
        print('数据权限：' + oct(Path(state['data']).stat().st_mode & 0o777))
        try:
            healthy = self.health_once(state)
        except (OSError, ValueError, KeyError, Error, http.client.HTTPException):
            healthy = False
        print('本机控制台健康检查：' + ('通过' if healthy else '未通过（检查端口、证书及日志）'))
        if component == 'local':
            print('凭据需在本机页面解锁；Linux 可选浏览模块需要 Chromium/Chrome。')

    def maintain(self, operation, value):
        state = self.require_state('server')
        if operation == 'port' and (value == self.effective_port(state) or not port_free(value)):
            raise Error('端口与当前相同或已占用，未停止服务')
        was_active = self.active('server')
        self.systemctl('stop', self.units['server'])
        backup = None
        try:
            with offline_lock(state['data']):
                backup = self.snapshot(state)
                edit_settings(state['data'], operation, value)
            if was_active:
                self.systemctl('start', self.units['server']);self.wait_health(state)
        except BaseException:
            self.systemctl('stop', self.units['server'], check=False)
            if backup:
                self.restore_snapshot(state, backup)
            if was_active:
                self.systemctl('start', self.units['server'], check=False)
            raise
        state['backup'] = str(backup);self.save(state)
        print('修改已完成；备份：' + str(backup))
        self.show_url(state)
        if operation == 'account':
            print('请使用新账号密码重新登录。两步验证、矿机和抽水配置均已保留。')

    def reset_account(self):
        state = self.require_state('server')
        username = prompt('新控制台账号', self.settings(state)['authentication']['username'])
        print('密码至少 8 位，包含大小写字母、数字及特殊字符；输入不回显。')
        password = prompt('新密码', secret=True)
        if password != prompt('再次输入新密码', secret=True):
            raise Error('两次密码不一致，未修改')
        validate_password(username, password)
        encoded = hash_password(password)
        password = None
        confirm('短暂重启服务端并重置登录账号密码（保留两步验证）')
        self.maintain('account', (username, encoded))

    def change_port(self):
        state = self.require_state('server')
        text = prompt('新的 Web 管理端口（1024–65535，输入 random 随机）', 'random')
        try:
            port = random_port((self.effective_port(state),)) if text == 'random' else int(text)
        except ValueError as exc:
            raise Error('端口必须是整数') from exc
        if not 1024 <= port <= 65535:
            raise Error('端口范围必须为 1024–65535')
        confirm(f'修改 Web 端口为 {port} 并短暂重启服务端')
        self.maintain('port', port)

    def uninstall(self, component):
        state = self.require_state(component)
        confirm(f'停止并卸载 {LABEL[component]}，配置和数据保留在 {state["data"]}')
        was_active = self.active(component)
        self.systemctl('stop', self.units[component])
        try:
            if component == 'server':
                with offline_lock(state['data']):
                    backup = self.snapshot(state)
            else:
                backup = self.snapshot(state)
        except BaseException:
            if was_active:
                self.systemctl('start', self.units[component], check=False)
            raise
        self.systemctl('disable', self.units[component], check=False)
        unit = self.unit_file(state)
        if unit.exists():
            unit.unlink()
        self.systemctl('daemon-reload')
        package_root = safe_path(self.packages / component)
        if package_root.parent != self.packages or component not in LABEL:
            raise Error('拒绝删除非管理器的软件目录')
        if package_root.exists():
            shutil.rmtree(package_root)
        state['installed'] = False;state['backup'] = str(backup);self.save(state)
        print('已卸载管理器部署的软件。配置、数据及备份均已保留。')
        if state['adopted']:
            print('接管前的系统服务已停用；原 DEB 软件包仍保留，未擅自删除既有安装。')


def ensure_argon():
    try:
        argon_library();return
    except Error:
        pass
    print('正在从系统软件源自动准备账号维护组件，请稍候……')
    if shutil.which('apt-get'):
        command(['apt-get', 'update'], capture=False)
        command(['apt-get', 'install', '-y', 'libargon2-1'], capture=False)
    elif shutil.which('dnf'):
        command(['dnf', 'install', '-y', 'libargon2'], capture=False)
    elif shutil.which('yum'):
        command(['yum', 'install', '-y', 'libargon2'], capture=False)
    elif shutil.which('pacman'):
        command(['pacman', '-S', '--needed', '--noconfirm', 'argon2'], capture=False)
    elif shutil.which('zypper'):
        command(['zypper', '--non-interactive', 'install', 'libargon2-1'], capture=False)
    else:
        raise Error('请从系统官方软件源安装 libargon2 后重试')
    argon_library()


def persist_manager():
    directory = Path('/usr/local/lib/strynium-manager')
    safe_path(directory).mkdir(parents=True, exist_ok=True, mode=0o755)
    target = directory / 'manager.py'
    atomic_bytes(target, Path(__file__).read_bytes(), mode=0o644)
    atomic_bytes(Path('/usr/local/sbin/strynium-manage'), b'#!/bin/sh\nexec /usr/bin/env python3 /usr/local/lib/strynium-manager/manager.py "$@"\n', mode=0o755)


def main():
    parser = argparse.ArgumentParser(description='STRYNIUM Linux/Ubuntu 一键安装与管理')
    parser.add_argument('--version', action='version', version=VERSION)
    parser.add_argument('component', nargs='?', choices=list(LABEL))
    parser.add_argument('action', nargs='?', choices=['install','update','start','stop','restart','status','logs','diagnose','console','port','reset-account','uninstall'])
    args = parser.parse_args()
    if os.geteuid() != 0:
        sudo = shutil.which('sudo')
        if not sudo:
            raise Error('请在云服务器控制台使用 root 登录后运行管理命令')
        print('正在申请管理权限；如有提示，请输入当前 Linux 账号的密码。', flush=True)
        os.execv(sudo, [sudo, '--', sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]])
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
        raise Error('当前软件包仅支持 Linux x64')
    if sys.version_info < (3, 8):
        raise Error('管理器需要 Python 3.8 或更新版本')
    if not Path('/run/systemd/system').is_dir():
        raise Error('此管理入口需要运行中的 systemd；无 systemd 环境请用 tar 包手动运行')
    for tool in ('systemctl','journalctl','tar'):
        if not shutil.which(tool):
            raise Error('缺少系统命令：' + tool)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    manager = Manager();manager.init_dirs()
    lock_path = manager.config / 'manager.lock'
    with open(lock_path, 'a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Error('另一个管理操作正在执行') from exc
        persist_manager()
        def dispatch(component, action):
            if action in ('port', 'reset-account') and component != 'server':
                raise Error('本地端没有服务端账号；此操作仅用于服务端')
            if action in ('install', 'update'):
                manager.install(component)
            elif action in ('start', 'stop', 'restart'):
                manager.lifecycle(component, action)
            elif action == 'port':
                manager.change_port()
            elif action == 'reset-account':
                ensure_argon();manager.reset_account()
            else:
                getattr(manager, action)(component)
        if args.component and args.action:
            dispatch(args.component, args.action);return
        while True:
            print('\nSTRYNIUM 安装与管理 ' + VERSION + '\n1. 服务端\n2. 本地加密端\n0. 退出')
            selection = prompt('选择组件', '0')
            if selection == '0':return
            component = {'1':'server','2':'local'}.get(selection)
            if component is None:continue
            while True:
                print('\n' + LABEL[component] + '\n1. 安装 / 更新\n2. 启动\n3. 停止\n4. 重启\n5. 状态\n6. 日志\n7. 诊断\n8. 打开控制台')
                if component == 'server':print('9. 修改 Web 端口\n10. 重置控制台账号密码')
                print('11. 卸载（保留数据）\n0. 返回')
                choice = prompt('选择操作', '0')
                if choice == '0':break
                action = {'1':'install','2':'start','3':'stop','4':'restart','5':'status','6':'logs','7':'diagnose','8':'console','9':'port','10':'reset-account','11':'uninstall'}.get(choice)
                if action:
                    try:
                        dispatch(component, action)
                    except (Error, OSError, ValueError, KeyError) as exc:
                        print('操作未完成：' + str(exc), file=sys.stderr)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n操作已取消。', file=sys.stderr);sys.exit(130)
    except (Error, OSError, ValueError, KeyError) as exc:
        print('STRYNIUM：' + str(exc), file=sys.stderr);sys.exit(1)
