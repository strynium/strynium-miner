#!/usr/bin/env bash
# STRYNIUM Miner v1.0.0 installer. Phase I1: real-machine acceptance pending.
# Release binaries and v1.0.0 tag are immutable. No build or protocol changes.
set -Eeuo pipefail
set +x

VERSION=v1.0.0
ROOT=/opt/strynium
BIN=$ROOT/bin
DATA=/var/lib/strynium
META=/etc/strynium-installer
UNIT=/etc/systemd/system/strynium-server.service
SERVICE=strynium-server.service
SERVER_USER=strynium-server
BASE_URL=https://github.com/strynium/strynium-miner/releases/download/v1.0.0
SERVER_ASSET=strynium-server-v1.0.0-ubuntu24.04-x86_64
TUNNEL_ASSET=strynium-tunnel-v1.0.0-ubuntu24.04-x86_64
SERVER_SIZE=7618264
TUNNEL_SIZE=4130616
SERVER_SHA=07cf5d06dc02f5c0d6cfcee31f3dcefb98dfe1073bc94f6cc25a06c0dfcdf8a5
TUNNEL_SHA=1a1b47629c71a5bdeecdbe27ab74766ce934a40811b48e2faccf61fa2898b0a0
LANGUAGE=zh
TMP=
BLUE='' GREEN='' YELLOW='' RED='' RESET=''
WEB_URL='' WEB_STATE='' LAN_IP=''
OPERATOR='' OP_HOME='' CONFIG_BASE='' STATE_BASE=''

say() { if [[ $LANGUAGE == en ]]; then printf '%s\n' "$2"; else printf '%s\n' "$1"; fi; }
heading() { printf '\n%s' "$BLUE"; say "$1" "$2"; printf '%s' "$RESET"; }
pass() { printf '%s✓ PASS%s ' "$GREEN" "$RESET"; say "$1" "$2"; }
warn() { printf '%s! WARN%s ' "$YELLOW" "$RESET"; say "$1" "$2"; }
fail() { printf '%s× FAIL%s ' "$RED" "$RESET" >&2; say "$1" "$2" >&2; return 1; }
ask() { local prompt; prompt=$(say "$1" "$2"); printf '%s > ' "$prompt"; IFS= read -r REPLY || REPLY=0; }
confirm() { ask '输入 YES 确认；其他输入返回' 'Type YES to confirm; anything else returns'; [[ $REPLY == YES ]]; }
colors() {
    if [[ -t 1 && ${TERM:-dumb} != dumb && ! ${NO_COLOR+x} ]]; then
        BLUE=$'\033[34m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; RESET=$'\033[0m'
    fi
}
language_screen() {
    printf '\n%sSTRYNIUM Miner%s\nSecure Mining Proxy & Tunnel Infrastructure\n%s\n\n' "$BLUE" "$RESET" "$VERSION"
    printf 'Please select your language / 请选择语言：\n1. English\n2. 简体中文\n请选择 [1-2] > '
    IFS= read -r REPLY || REPLY=0
    [[ $REPLY != 0 ]] || return 1
    if [[ $REPLY == 1 ]]; then LANGUAGE=en; else LANGUAGE=zh; fi
}

# All Python input paths originate in fixed installer authority or validated
# operator metadata. No eval/source of runtime configuration; no secret output.
facts() {
    python3 - "$@" <<'PY'
import ipaddress, json, os, pathlib, pwd, re, ssl, stat, sys
cmd, *args = sys.argv[1:]
def load(path):
    with open(path, encoding='utf-8') as f:
        return json.loads(f.read(1024 * 1024 + 1))
def pathcheck(path, owner=None, private=False):
    p = pathlib.Path(path)
    assert p.is_absolute() and str(p) == path and '..' not in p.parts
    for a in [p, *p.parents]:
        if a.exists() or a.is_symlink():
            s = a.lstat()
            assert not stat.S_ISLNK(s.st_mode)
            if owner is not None:
                assert s.st_uid in (0, owner) and s.st_mode & 0o022 == 0
    if p.exists():
        s = p.stat()
        assert stat.S_ISDIR(s.st_mode) or (stat.S_ISREG(s.st_mode) and s.st_nlink == 1)
        if private:
            assert s.st_uid == owner and s.st_mode & 0o077 == 0
    return p
def rfc1918(text):
    ip = ipaddress.IPv4Address(text)
    return any(ip in ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16'))
def operator(data):
    assert set(data) == {'user','home','config','state'}
    user = data['user']
    assert re.fullmatch(r'[a-z_][a-z0-9_-]{0,30}', user)
    account = pwd.getpwnam(user)
    assert account.pw_uid >= 1000 and account.pw_dir == data['home']
    home = pathcheck(data['home'], account.pw_uid)
    assert home.is_dir() and home.stat().st_uid == account.pw_uid and str(home) != '/'
    for key in ('config','state'):
        # Existing XDG bases outside this real home require manual management.
        p = pathcheck(data[key], account.pw_uid)
        assert home in p.parents
        assert not any(c in str(p) for c in '\r\n\t')
    return data, account
try:
    if cmd == 'platform':
        values = {}
        for line in pathlib.Path(args[0]).read_text().splitlines():
            if '=' in line:
                k,v = line.split('=',1); values[k] = v.strip('"\x27')
        assert values.get('ID') == 'ubuntu' and values.get('VERSION_ID','').startswith('24.04')
    elif cmd == 'safe':
        pathcheck(args[0], int(args[1]), len(args) > 2)
    elif cmd == 'lan':
        interfaces, routes = load(args[0]), load(args[1]); candidates = []
        for r in routes:
            gateway = ipaddress.IPv4Address(r.get('gateway','0.0.0.0'))
            if (r.get('dst') != 'default' or r.get('type','unicast') != 'unicast'
                or 'linkdown' in r.get('flags',[]) or gateway.is_unspecified
                or gateway.is_loopback or gateway.is_link_local or gateway.is_multicast
                or str(gateway) == '255.255.255.255' or r.get('metric',0) == 4294967295): continue
            for i in interfaces:
                if (r.get('dev') != i['ifname'] or i.get('operstate') != 'UP'
                    or 'UP' not in i.get('flags',[]) or 'LOOPBACK' in i.get('flags',[])): continue
                for a in i.get('addr_info',[]):
                    if a.get('family') != 'inet' or a.get('scope') != 'global': continue
                    if not rfc1918(a['local']) or not 0 < a['prefixlen'] <= 32: continue
                    if r.get('prefsrc', a['local']) != a['local']: continue
                    ip = ipaddress.IPv4Address(a['local']); n = ipaddress.ip_network(f'{ip}/{a["prefixlen"]}',strict=False)
                    if a['prefixlen'] < 31 and ip in (n.network_address,n.broadcast_address): continue
                    candidates.append((r.get('metric',0),i['ifindex'],ip))
        assert candidates
        print(min(candidates)[2])
    elif cmd == 'listeners':
        pid = args[1]; assert re.fullmatch(r'[1-9][0-9]*',pid)
        for line in pathlib.Path(args[0]).read_text().splitlines():
            if re.search(r'pid='+pid+r',',line):
                parts = line.split()
                if len(parts) >= 4 and re.fullmatch(r'[0-9.]+:[0-9]+',parts[3]): print(parts[3])
    elif cmd == 'readiness':
        d = load(args[0]); lan = args[1]
        assert d['product'] == 'STRYNIUM' and d['state'] in ('DEFAULT_ADMIN_AVAILABLE','READY_TO_LOGIN')
        m = re.fullmatch(r'https://([0-9.]+):([0-9]{1,5})/?',d['console_url'])
        assert m and m[1] == lan and rfc1918(lan) and 0 < int(m[2]) <= 65535
        print(f'https://{lan}:{int(m[2])}/ {d["state"]}')
    elif cmd == 'certificate':
        uid = int(args[1]); pathcheck(args[0],uid,True)
        d = load(args[0]); cert = bytes(d['certificate'])
        assert 0 < len(cert) < 65536
        # Only the public certificate leaves the process; never identity JSON.
        print(ssl.DER_cert_to_PEM_cert(cert),end='')
    elif cmd == 'operator-save':
        d,_ = operator(dict(zip(('user','home','config','state'),args)))
        print(json.dumps(d))
    elif cmd == 'operator-load':
        pathcheck(args[0],0,True); d,_ = operator(load(args[0]))
        for k in ('user','home','config','state'): print(d[k])
    elif cmd == 'pids':
        exe, user = args; uid = None if user == '*' else pwd.getpwnam(user).pw_uid
        for p in pathlib.Path('/proc').iterdir():
            if not p.name.isdecimal(): continue
            try:
                if (uid is None or p.stat().st_uid == uid) and os.readlink(p/'exe') in (exe,exe+' (deleted)'): print(p.name)
            except (FileNotFoundError,PermissionError,ProcessLookupError): pass
    elif cmd == 'store':
        root, user = args; uid = pwd.getpwnam(user).pw_uid
        p = pathcheck(root,uid,True)
        if not p.exists(): print('NOT_CONFIGURED')
        else:
            for f in p.rglob('*'):
                pathcheck(str(f),uid,True)
            print('PRESENT_LOCKED_UNVERIFIED')  # Never decrypt or infer authenticated state.
    elif cmd == 'journal':
        # Whitelist metadata only. MESSAGE, command lines and dynamic fields are
        # never rendered, including on malformed/adversarial journal entries.
        counts = {str(n):0 for n in range(8)}
        for line in pathlib.Path(args[0]).read_text().splitlines():
            try:
                p = str(json.loads(line).get('PRIORITY',''))
                if p in counts: counts[p] += 1
            except (ValueError,TypeError): pass
        print('Journal priority counts (last 100 records): '+', '.join(k+'='+str(v) for k,v in counts.items()))
    else: raise ValueError('unknown operation')
except Exception:
    # Do not echo exceptions, files, input values or tracebacks: they may contain secrets.
    sys.exit(1)
PY
}

safe_path() { facts safe "$1" "${2:-0}" "${@:3}"; }
cleanup() {
    if [[ -n $TMP && $TMP == /tmp/strynium-installer.* && ! -L $TMP && -d $TMP ]]; then
        if [[ $(realpath -e -- "$TMP") == "$TMP" && $(stat -c %u -- "$TMP") == "$EUID" ]]; then
            find "$TMP" -xdev -depth -delete 2>/dev/null || true
        fi
    fi
}
platform_check() { facts platform /etc/os-release || fail '仅支持 Ubuntu 24.04。' 'Only Ubuntu 24.04 is supported.'; }
arch_check() { [[ $(uname -m) == x86_64 ]] || fail '仅支持 x86_64。' 'Only x86_64 is supported.'; }
verify_file() {
    local file=$1 size=$2 sha=$3 actual
    [[ -f $file && ! -L $file && $(stat -c %s -- "$file") == "$size" ]] || return 1
    actual=$(sha256sum -- "$file") || return 1
    [[ ${actual%% *} == "$sha" ]]
}
verify_component() {
    if [[ $1 == server ]]; then verify_file "$BIN/strynium-server" "$SERVER_SIZE" "$SERVER_SHA"
    else verify_file "$BIN/strynium-tunnel" "$TUNNEL_SIZE" "$TUNNEL_SHA"; fi
}
download() {
    local url=$1 out=$2
    if command -v curl >/dev/null; then
        curl -q --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
            --retry 5 --retry-all-errors --connect-timeout 30 --max-time 600 --output "$out" "$url" 2>/dev/null
    else
        wget --no-config --https-only --quiet --tries=6 --timeout=30 --output-document="$out" "$url" 2>/dev/null
    fi
}
fetch_component() {
    local component=$1 asset size sha
    if [[ $component == server ]]; then asset=$SERVER_ASSET; size=$SERVER_SIZE; sha=$SERVER_SHA
    else asset=$TUNNEL_ASSET; size=$TUNNEL_SIZE; sha=$TUNNEL_SHA; fi
    if ! download "$BASE_URL/$asset" "$TMP/$component"; then
        rm -f -- "$TMP/$component"
        fail '下载失败；未安装、未启动。' 'Download failed; nothing installed or started.'; return 1
    fi
    if ! verify_file "$TMP/$component" "$size" "$sha"; then
        rm -f -- "$TMP/$component"
        fail '安全验证失败。下载文件大小或 SHA-256 与 STRYNIUM V1.0.0 官方发布值不一致。安装已停止。' \
            'Security verification failed: size or SHA-256 differs from the official V1.0.0 value. Installation stopped.'
        return 1
    fi
}
atomic_install() {
    local component=$1 stage
    safe_path "$BIN" && safe_path "$BIN/strynium-$component" || return 1
    install -d -m 0755 -o root -g root -- "$ROOT" "$BIN" || return 1
    stage=$(mktemp "$BIN/.strynium-$component.XXXXXXXX") || return 1
    if ! install -m 0755 -o root -g root -- "$TMP/$component" "$stage"; then rm -f -- "$stage"; return 1; fi
    if ! mv -fT -- "$stage" "$BIN/strynium-$component"; then rm -f -- "$stage"; return 1; fi
}
unit_text() {
    printf '%s\n' '# Managed by STRYNIUM installer v1.0.0' '[Unit]' 'Description=STRYNIUM Server' \
        'After=network-online.target' 'Wants=network-online.target' '[Service]' 'Type=simple' \
        "User=$SERVER_USER" "Group=$SERVER_USER" "WorkingDirectory=$DATA" "ExecStart=$BIN/strynium-server" \
        'Restart=on-failure' 'RestartSec=5s' 'TimeoutStopSec=45s' 'UMask=0077' \
        'LimitCORE=0' 'NoNewPrivileges=true' 'PrivateTmp=true' 'ProtectSystem=strict' \
        "ReadWritePaths=$DATA" 'ProtectHome=true' 'StandardOutput=journal' 'StandardError=journal' \
        '[Install]' 'WantedBy=multi-user.target'
}
managed_service() {
    local fragment drops
    safe_path "$UNIT" || return 1
    fragment=$(systemctl show "$SERVICE" -p FragmentPath --value 2>/dev/null) || return 1
    drops=$(systemctl show "$SERVICE" -p DropInPaths --value 2>/dev/null) || return 1
    [[ -z $drops && ( -z $fragment || $fragment == "$UNIT" ) ]] || return 1
    if [[ -e $UNIT ]]; then unit_text > "$TMP/unit.expected"; cmp -s "$TMP/unit.expected" "$UNIT" || return 1; fi
}
server_preflight() {
    [[ -d /run/systemd/system ]] || return 1
    managed_service || return 1
    [[ ! -e $DATA || -d $DATA ]] || return 1
    if [[ -d $DATA ]]; then
        id "$SERVER_USER" >/dev/null 2>&1 || return 1
        safe_path "$DATA" "$(id -u "$SERVER_USER")" private || return 1
    else safe_path "$DATA" || return 1; fi
    # Refuse an existing identity with an unexpected home (no silent takeover).
    if id "$SERVER_USER" >/dev/null 2>&1; then
        [[ $(getent passwd "$SERVER_USER" | cut -d: -f6) == "$DATA" ]] || return 1
    fi
}
prepare_server() {
    if ! id "$SERVER_USER" >/dev/null 2>&1; then
        useradd --system --user-group --home-dir "$DATA" --no-create-home --shell /usr/sbin/nologin "$SERVER_USER" >/dev/null 2>&1 || return 1
    fi
    if [[ ! -d $DATA ]]; then install -d -m 0700 -o "$SERVER_USER" -g "$SERVER_USER" "$DATA" || return 1; fi
    unit_text > "$TMP/unit"
    install -m 0644 -o root -g root "$TMP/unit" "$UNIT" || return 1
    systemctl daemon-reload >/dev/null 2>&1 || return 1
}
local_get() {
    local url=$1 out=$2 ca=${3:-}
    if command -v curl >/dev/null; then
        local opts=(-q --fail --silent --noproxy '*' --connect-timeout 2 --max-time 4 --max-filesize 65536)
        [[ -z $ca ]] || opts+=(--cacert "$ca")
        curl "${opts[@]}" --output "$out" "$url" 2>/dev/null
    else
        local opts=(--no-config --quiet --no-proxy --timeout=4 --tries=1)
        [[ -z $ca ]] || opts+=(--ca-certificate="$ca")
        wget "${opts[@]}" --output-document="$out" "$url" 2>/dev/null
    fi
}
discover_web() {
    local pid addr result check endpoint
    local -a listeners
    WEB_URL='' WEB_STATE='' LAN_IP=''
    pid=$(systemctl show "$SERVICE" -p MainPID --value 2>/dev/null) || return 1
    [[ $pid =~ ^[1-9][0-9]*$ && $(readlink "/proc/$pid/exe") == "$BIN/strynium-server" ]] || return 1
    ip -j -4 address show > "$TMP/addresses" 2>/dev/null || return 1
    ip -j -4 route show default > "$TMP/routes" 2>/dev/null || return 1
    LAN_IP=$(facts lan "$TMP/addresses" "$TMP/routes") || return 1
    ss -H -ltnp > "$TMP/sockets" 2>/dev/null || return 1
    facts listeners "$TMP/sockets" "$pid" > "$TMP/listeners" || return 1
    mapfile -t listeners < "$TMP/listeners"
    for addr in "${listeners[@]}"; do
        [[ $addr == 127.0.0.1:* ]] || continue
        if ! local_get "http://$addr/api/console/readiness" "$TMP/readiness"; then continue; fi
        result=$(facts readiness "$TMP/readiness" "$LAN_IP") || continue
        read -r WEB_URL WEB_STATE <<< "$result"
        endpoint=${WEB_URL#https://}; endpoint=${endpoint%/}
        if [[ " ${listeners[*]} " != *" $endpoint "* ]]; then WEB_URL='' WEB_STATE=''; continue; fi
        facts certificate "$DATA/console-tls/identity.json" "$(id -u "$SERVER_USER")" > "$TMP/console-ca.pem" || return 1
        local_get "${WEB_URL}api/console/readiness" "$TMP/https-readiness" "$TMP/console-ca.pem" || return 1
        check=$(facts readiness "$TMP/https-readiness" "$LAN_IP") || return 1
        [[ $check == "$result" ]] || return 1
        return 0
    done
    WEB_URL='' WEB_STATE=''
    return 1
}
access_screen() {
    if ! discover_web; then
        WEB_URL='' WEB_STATE=''
        fail '无法验证实际 LAN HTTPS 端点；访问验收未通过。请检查服务、路由、监听和证书。' \
            'Cannot verify the actual LAN HTTPS endpoint. Access acceptance failed; check service, route, listeners and certificate.'
        return 1
    fi
    heading 'Web 管理控制台' 'Web Management Console'
    printf '\n  %s%s%s\n\n' "$BLUE" "$WEB_URL" "$RESET"
    if [[ $WEB_STATE == DEFAULT_ADMIN_AVAILABLE ]]; then
        say '  初始用户名： strynium' '  Initial username: strynium'
        say '  初始密码：   Strynium2026.' '  Initial password: Strynium2026.'
        warn '首次登录后必须同时修改管理员用户名和密码；修改完成后初始凭据立即失效，再进入 Dashboard。' \
            'First login requires changing BOTH username and password. Initial credentials then expire; proceed to Dashboard.'
    else
        say '管理员账户：已初始化；初始凭据：已失效。' 'Administrator initialized; initial credentials are invalid.'
        say '当前管理员密码不会由安装器显示或恢复。' 'The installer will not display or recover the current password.'
    fi
    warn '证书已对照本机产品身份验证。远端浏览器需独立核验证书；未修改信任库或防火墙。仅限授权管理网络访问。' \
        'Certificate verified against local product identity. Independently verify it in your browser; trust stores and firewall are unchanged. Authorized management networks only.'
}
progress() { printf '[%02d/08] ' "$1"; pass "$2" "$3"; }
server_confirmation() {
    heading '安装 STRYNIUM Server' 'Install STRYNIUM Server'
    printf '%s | Ubuntu 24.04 x86_64\n%s\n%s\n' "$VERSION" "$BIN/strynium-server" "$SERVICE"
    say "运行目录：$DATA；Web：实际 LAN HTTPS；开机启动：启用" "Runtime: $DATA; Web: actual LAN HTTPS; autostart: enabled"
    say '计划：下载 → 校验大小/SHA-256 → 安装 → 创建服务与权限 → 启动 → 验证 HTTPS' \
        'Plan: download → size/SHA-256 → install → service/permissions → start → verify HTTPS'
    ask '1. 是，开始安装  2. 返回' '1. Yes, install  2. Back'
    [[ $REPLY == 1 ]]
}
install_server() {
    server_confirmation || return 2
    platform_check || return 1; progress 1 '检查系统环境' 'Operating system'
    arch_check || return 1; progress 2 '检查系统架构' 'Architecture'
    server_preflight || { fail '已有服务/数据不能安全接管，或 systemd 不可用；未更改。' 'Existing service/data cannot be safely managed, or systemd unavailable; unchanged.'; return 1; }
    fetch_component server || return 1
    progress 3 '下载 Server' 'Download Server'; progress 4 '验证大小与 SHA-256' 'Verify size and SHA-256'
    if systemctl is-active --quiet "$SERVICE"; then systemctl stop "$SERVICE" >/dev/null 2>&1 || return 1; fi
    atomic_install server || return 1; progress 5 '安装程序' 'Install program'
    prepare_server || return 1; progress 6 '创建 systemd 服务' 'Create systemd service'
    verify_component server || return 1
    systemctl enable "$SERVICE" >/dev/null 2>&1 || return 1
    systemctl start "$SERVICE" >/dev/null 2>&1 || return 1
    # Starting precedes probing; progress never claims a listener before start.
    local attempt ready=no
    for ((attempt=0; attempt<15; attempt++)); do if discover_web; then ready=yes; break; fi; sleep 1; done
    [[ $ready == yes ]] || { fail '程序已安装，但 HTTPS 访问验证失败；安装未通过。保留数据，使用诊断菜单。' 'Program installed, but HTTPS access verification failed. Installation NOT accepted. Data preserved; use diagnostics.'; return 1; }
    progress 7 '检测 Web 服务' 'Verify Web service'
    systemctl is-active --quiet "$SERVICE" || return 1
    progress 8 '启动 Server' 'Server started'
    access_screen
}

load_operator() {
    local values
    values=$(facts operator-load "$META/tunnel.json") || return 1
    mapfile -t OP_FIELDS <<< "$values"
    [[ ${#OP_FIELDS[@]} == 4 ]] || return 1
    OPERATOR=${OP_FIELDS[0]}; OP_HOME=${OP_FIELDS[1]}; CONFIG_BASE=${OP_FIELDS[2]}; STATE_BASE=${OP_FIELDS[3]}
}
choose_operator() {
    if [[ -e $META/tunnel.json || -L $META/tunnel.json ]]; then load_operator; return; fi
    warn '使用专用非 root 用户；已有安装必须选择原用户与原 XDG 目录。不会迁移或重置。' \
        'Use a dedicated non-root user. Existing installations MUST use the original user and XDG directories; no migration/reset.'
    ask '操作用户名（默认 strynium-tunnel；不存在则创建锁定密码的账户）' 'Operator username (default strynium-tunnel; create password-locked account if absent)'
    OPERATOR=${REPLY:-strynium-tunnel}
    [[ $OPERATOR =~ ^[a-z_][a-z0-9_-]{0,30}$ ]] || return 1
    if ! id "$OPERATOR" >/dev/null 2>&1; then
        useradd --create-home --user-group --shell /bin/bash "$OPERATOR" >/dev/null 2>&1 || return 1
    fi
    OP_HOME=$(getent passwd "$OPERATOR" | cut -d: -f6) || return 1
    ask "XDG_CONFIG_HOME（回车：$OP_HOME/.config；已有自定义目录必须填入）" "XDG_CONFIG_HOME (Enter: $OP_HOME/.config; specify existing custom directory)"
    CONFIG_BASE=${REPLY:-$OP_HOME/.config}
    ask "XDG_STATE_HOME（回车：$OP_HOME/.local/state）" "XDG_STATE_HOME (Enter: $OP_HOME/.local/state)"
    STATE_BASE=${REPLY:-$OP_HOME/.local/state}
    facts operator-save "$OPERATOR" "$OP_HOME" "$CONFIG_BASE" "$STATE_BASE" > "$TMP/operator" || return 1
    safe_path "$META" && safe_path "$META/tunnel.json" || return 1
    install -d -m 0700 -o root -g root "$META" || return 1
    install -m 0600 -o root -g root "$TMP/operator" "$META/tunnel.json" || return 1
}
tunnel_warning() {
    heading 'STRYNIUM Tunnel — 加密凭据存储' 'STRYNIUM Tunnel — encrypted credential store'
    printf '%s | Ubuntu 24.04 x86_64\n%s\nPASSPHRASE_UNLOCKED_ENCRYPTED_STORE\n' "$VERSION" "$BIN/strynium-tunnel"
    warn '新的 Tunnel 进程启动 / 系统重启后需要通过隐藏终端输入重新解锁；不明文保存密码，不创建自动解锁服务。' \
        'Every new process/reboot requires hidden terminal unlock. No plaintext passphrase storage and no autostart/unattended unlock service.'
}
install_tunnel() {
    tunnel_warning; confirm || return 2
    platform_check && arch_check || return 1
    fetch_component tunnel || return 1
    choose_operator || { fail '操作用户/目录不安全；外部 XDG 目录请手工管理。' 'Unsafe operator/paths; manage XDG locations outside the home manually.'; return 1; }
    local pids
    pids=$(facts pids "$BIN/strynium-tunnel" '*') || return 1
    [[ -z $pids ]] || { fail '请先停止 Tunnel 再更新。' 'Stop Tunnel before updating.'; return 1; }
    atomic_install tunnel && verify_component tunnel || return 1
    pass 'Tunnel 已安装；未启动，等待导入/交互解锁。' 'Tunnel installed; not started. Import/interactive unlock required.'
    printf 'INSTALLED / LOCKED\n'
}
run_as_operator() {
    # setpriv preserves the root-provisioned resource limit (runuser may reset it).
    # A clean environment carries paths only, never credentials or inherited secrets.
    (
        ulimit -l unlimited || exit 1
        ulimit -c 0 || exit 1
        cd -- "$OP_HOME" || exit 1
        exec env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME="$OP_HOME" USER="$OPERATOR" LOGNAME="$OPERATOR" \
            XDG_CONFIG_HOME="$CONFIG_BASE" XDG_STATE_HOME="$STATE_BASE" TERM="${TERM:-dumb}" \
            setpriv --reuid="$OPERATOR" --regid="$(id -g "$OPERATOR")" --init-groups --no-new-privs "$@"
    )
}
tunnel_run() {
    [[ -t 0 && -t 1 && -r /dev/tty ]] || { fail '解锁需要交互终端。' 'Unlock requires an interactive terminal.'; return 1; }
    load_operator && verify_component tunnel || return 1
    [[ -z $(facts pids "$BIN/strynium-tunnel" "$OPERATOR") ]] || return 1
    tunnel_warning
    say '首次导入需要服务端签发的 bootstrap 和已绑定 UUID；不会预填配置。Ctrl+C 安全结束进程。' \
        'First import needs the server-issued bootstrap and bound UUID; no fabricated config. Ctrl+C stops the process.'
    ask '1. 启动/解锁  2. 首次导入/重试导入  0. 返回' '1. Run/unlock  2. First import/retry import  0. Back'
    case $REPLY in
        1) run_as_operator "$BIN/strynium-tunnel" run ;;
        2) run_as_operator systemd-ask-password --echo=no --timeout=0 'STRYNIUM bootstrap:' |
            run_as_operator "$BIN/strynium-tunnel" import-bootstrap --stdin ;;
        *) return 0 ;;
    esac
}
tunnel_stop() {
    load_operator || return 1
    local pid pids
    pids=$(facts pids "$BIN/strynium-tunnel" "$OPERATOR") || return 1
    [[ -n $pids ]] || { warn 'Tunnel 已停止。' 'Tunnel already stopped.'; return 0; }
    confirm || return 2
    while IFS= read -r pid; do
        # Revalidate exact executable and uid immediately before graceful signal.
        [[ $(readlink "/proc/$pid/exe" 2>/dev/null) == "$BIN/strynium-tunnel" ]] || return 1
        [[ $(stat -c %u "/proc/$pid") == "$(id -u "$OPERATOR")" ]] || return 1
        kill -TERM "$pid" || return 1
    done <<< "$pids"
    local i
    for ((i=0; i<30; i++)); do
        [[ -n $(facts pids "$BIN/strynium-tunnel" "$OPERATOR") ]] || return 0
        sleep 1
    done
    fail '进程未在 30 秒内正常退出；不会强杀或删数据。' 'Process did not exit within 30 seconds; no force kill or data deletion.'
}
tunnel_status() {
    [[ -f $BIN/strynium-tunnel ]] || { printf 'NOT_INSTALLED\n'; return; }
    if ! load_operator; then printf 'INSTALLED / OPERATOR_UNKNOWN\n'; return; fi
    local pids
    pids=$(facts pids "$BIN/strynium-tunnel" "$OPERATOR") || { printf 'UNKNOWN\n'; return; }
    if [[ -n $pids ]]; then printf 'PROCESS_RUNNING / CONNECTION_UNKNOWN\n'; else printf 'LOCKED / STOPPED\n'; fi
}
status_screen() {
    heading '系统状态' 'System status'
    if [[ ! -f $BIN/strynium-server ]]; then printf 'Server: NOT_INSTALLED\n'
    elif systemctl is-active --quiet "$SERVICE"; then
        printf '%s● Server: RUNNING%s\n' "$GREEN" "$RESET"
        local stamp
        stamp=$(systemctl show "$SERVICE" -p ActiveEnterTimestampMonotonic --value 2>/dev/null) || stamp=0
        if [[ $stamp =~ ^[0-9]+$ && $stamp != 0 ]]; then
            awk -v start="$stamp" '{printf "Server uptime: %.0f seconds\n", $1-start/1000000}' /proc/uptime
        fi
    else printf 'Server: STOPPED\n'; fi
    printf 'Tunnel: '; tunnel_status
    if [[ -f $BIN/strynium-server ]] && discover_web; then printf 'Web: %s\n' "$WEB_URL"; else printf 'Web: UNKNOWN / NOT_READY\n'; fi
    printf 'Ubuntu / %s\n' "$(uname -m)"
    printf 'Host: %s\nInstall: %s\nServer data: %s\n' "$(hostname)" "$ROOT" "$DATA"
}
logs_screen() {
    heading '安全日志摘要' 'Safe log summaries'
    say '不展示原始 MESSAGE、命令行或动态日志字段，避免泄漏秘密。' 'Raw MESSAGE, command lines and dynamic log fields are never rendered (secret protection).'
    ask '1. Server 日志  2. Tunnel 日志  3. systemd 服务日志  0. 返回' '1. Server logs  2. Tunnel logs  3. systemd service logs  0. Back'
    case $REPLY in
        1|3)
            if journalctl --quiet --no-pager -u "$SERVICE" -n 100 -o json --output-fields=PRIORITY > "$TMP/journal" 2>/dev/null; then
                facts journal "$TMP/journal"; rm -f -- "$TMP/journal"
            else rm -f -- "$TMP/journal"; warn '日志不可用。' 'Journal unavailable.'; fi ;;
        2) tunnel_status; say 'Tunnel 在交互终端运行；安装器不记录其输出或解锁输入。历史日志未由安装器采集。' \
            'Tunnel runs interactively; installer does not record its output or unlock input. Historical logs are not collected.' ;;
    esac
}
diagnostic() {
    heading 'STRYNIUM 系统诊断' 'STRYNIUM diagnostics'
    if platform_check; then pass '操作系统' 'Operating system'; fi
    if arch_check; then pass '架构' 'Architecture'; fi
    local libc
    libc=$(getconf GNU_LIBC_VERSION 2>/dev/null) || libc=UNKNOWN
    if [[ $libc == 'glibc 2.39' ]]; then pass 'GLIBC 2.39' 'GLIBC 2.39'; else warn 'GLIBC 非已验收 2.39 基线。' 'GLIBC differs from qualified 2.39 baseline.'; fi
    local component
    for component in server tunnel; do
        if [[ -f $BIN/strynium-$component ]]; then
            if verify_component "$component"; then pass "$component binary / SHA-256" "$component binary / SHA-256"
            else fail "$component binary / SHA-256" "$component binary / SHA-256" || true; fi
        else warn "$component 未安装" "$component not installed"; fi
    done
    if [[ -d /run/systemd/system ]] && managed_service; then pass 'systemd 服务定义' 'systemd service definition'; else warn 'systemd/服务定义不可管理' 'systemd/service definition not managed'; fi
    if systemctl is-active --quiet "$SERVICE"; then pass 'Server process' 'Server process'; else warn 'Server STOPPED' 'Server STOPPED'; fi
    if discover_web; then pass "HTTPS: $WEB_URL" "HTTPS: $WEB_URL"
    elif systemctl is-active --quiet "$SERVICE"; then fail '运行中 Server 的 HTTPS 端点验证失败' 'Running Server HTTPS endpoint verification failed' || true
    else warn 'HTTPS 端点未验证（服务未运行）' 'HTTPS endpoint unverified (service not running)'; fi
    if [[ ! -e $DATA ]]; then warn '数据目录尚不存在' 'Data directory not created yet'
    elif id "$SERVER_USER" >/dev/null 2>&1 && safe_path "$DATA" "$(id -u "$SERVER_USER")" private && [[ -d $DATA ]]; then
        pass '数据目录权限' 'Data directory permissions'
    else fail '数据目录权限不安全/无法验证' 'Data directory permissions unsafe/unverified' || true; fi
    if download "$BASE_URL/SHA256SUMS.txt" "$TMP/connectivity"; then pass 'GitHub HTTPS 可用' 'GitHub HTTPS available'; else warn 'GitHub 连接失败（不影响已安装字节）' 'GitHub unavailable (installed bytes unchanged)'; fi
    if [[ -f $BIN/strynium-tunnel ]] && load_operator; then
        local store
        if store=$(facts store "$STATE_BASE/strynium/strynium-tunnel/secrets" "$OPERATOR"); then
            warn "Tunnel: $store；未执行解密/连接验收。" "Tunnel: $store; decryption/connection not tested."
        else fail 'Tunnel store 权限不安全/无法验证' 'Tunnel store permissions unsafe/unverified' || true; fi
    fi
    tunnel_status
    warn '未修改防火墙；若远端不可达，请核查仅授权 LAN 到实际 HTTPS 端口的规则，不要开放公网。' \
        'Firewall unchanged. If remote access fails, check authorized LAN rules for the verified HTTPS port; do not expose it publicly.'
}
server_menu() {
    heading 'Server 管理' 'Server management'
    say '1. 启动  2. 停止  3. 重启  4. 状态  5. 日志  6. 访问地址  0. 返回' '1. Start  2. Stop  3. Restart  4. Status  5. Logs  6. Web access  0. Back'
    ask '选择' 'Select'
    local action
    case $REPLY in
        1) action=start ;; 2) action=stop ;; 3) action=restart ;;
        4) status_screen; return ;; 5) logs_screen; return ;; 6) access_screen; return ;; *) return ;;
    esac
    managed_service && [[ -f $UNIT ]] || return 1
    if [[ $action != stop ]]; then verify_component server || return 1; fi
    systemctl "$action" "$SERVICE" >/dev/null 2>&1 || return 1
    if [[ $action != stop ]]; then access_screen; fi
}
tunnel_menu() {
    heading 'Tunnel 管理' 'Tunnel management'
    say '1. 启动 / 解锁  2. 停止  3. 状态  4. 日志  0. 返回' '1. Run / unlock  2. Stop  3. Status  4. Logs  0. Back'
    ask '选择' 'Select'
    case $REPLY in 1) tunnel_run ;; 2) tunnel_stop ;; 3) tunnel_status ;; 4) logs_screen ;; esac
}
install_both() {
    install_server || return $?
    if ! install_tunnel; then warn 'PARTIAL INSTALL：Server 保留；Tunnel 未完成。' 'PARTIAL INSTALL: Server retained; Tunnel incomplete.'; return 1; fi
}
repair() {
    say '重新安装同一 v1.0.0；不会删除运行数据、凭据或配置。' 'Reinstall the same v1.0.0; runtime data, credentials and config are preserved.'
    if [[ -f $BIN/strynium-server ]]; then install_server || return $?; fi
    if [[ -f $BIN/strynium-tunnel ]]; then install_tunnel || return $?; fi
}
install_menu() {
    say '1. Server  2. Tunnel  3. Server + Tunnel  4. 更新 / 修复  0. 返回' '1. Server  2. Tunnel  3. Server + Tunnel  4. Update / repair  0. Back'
    ask '选择' 'Select'
    case $REPLY in 1) install_server ;; 2) install_tunnel ;; 3) install_both ;; 4) repair ;; esac
}
uninstall() {
    heading '卸载' 'Uninstall'
    say '1. 仅删除程序/服务（保留所有数据）  2. 删除 Server 持久数据  0. 返回' \
        '1. Remove programs/services only (preserve all data)  2. Delete Server persistent data  0. Back'
    ask '选择' 'Select'
    case $REPLY in
        1)
            warn '将删除 Server 和 Tunnel 程序；用户账户、Tunnel 加密状态、Server 数据及操作用户记录均保留。' \
                'Remove Server/Tunnel programs; retain accounts, Tunnel encrypted state, Server data and operator metadata.'
            confirm || return 2
            safe_path "$BIN" && safe_path "$UNIT" && managed_service || return 1
            if [[ -f $BIN/strynium-tunnel ]]; then
                load_operator || return 1
                [[ -z $(facts pids "$BIN/strynium-tunnel" '*') ]] || { fail '先停止 Tunnel。' 'Stop Tunnel first.'; return 1; }
            fi
            if [[ -f $UNIT ]]; then
                systemctl disable --now "$SERVICE" >/dev/null 2>&1 || return 1
                systemctl is-active --quiet "$SERVICE" && return 1
                rm -f -- "$UNIT" || return 1
                systemctl daemon-reload >/dev/null 2>&1 || return 1
            fi
            [[ -z $(facts pids "$BIN/strynium-server" '*') ]] || return 1
            safe_path "$BIN/strynium-server" && safe_path "$BIN/strynium-tunnel" || return 1
            rm -f -- "$BIN/strynium-server" "$BIN/strynium-tunnel" || return 1
            pass '程序已删除；数据保留。' 'Programs removed; data retained.' ;;
        2)
            warn "永久删除 $DATA。Tunnel 状态不在此目录，安装器不会自动删除用户目录。" \
                "Permanently delete $DATA. Tunnel state is separate; installer never recursively removes user directories."
            [[ ! -e $UNIT && ! -e $BIN/strynium-server && $DATA == /var/lib/strynium ]] || return 1
            id "$SERVER_USER" >/dev/null 2>&1 || return 1
            [[ -z $(facts pids "$BIN/strynium-server" "$SERVER_USER") ]] || return 1
            safe_path "$DATA" "$(id -u "$SERVER_USER")" private || return 1
            [[ -d $DATA && $(realpath -e "$DATA") == /var/lib/strynium && ! -L $DATA ]] || return 1
            ask '输入 DELETE /var/lib/strynium 才会永久删除' 'Type DELETE /var/lib/strynium to permanently delete'
            [[ $REPLY == 'DELETE /var/lib/strynium' ]] || return 2
            # Coordinate with the product's exclusive Console ownership lock.
            if [[ -e $DATA/console-owner.lock ]]; then
                safe_path "$DATA/console-owner.lock" "$(id -u "$SERVER_USER")" private || return 1
                exec 8<"$DATA/console-owner.lock"
                flock -n -x 8 || { exec 8<&-; return 1; }
            fi
            # Fixed authority, no symlink traversal; refuse mounted descendants.
            if findmnt -rn -o TARGET | grep -Eq '^/var/lib/strynium(/|$)'; then exec 8<&-; return 1; fi
            if ! find /var/lib/strynium -xdev -depth -delete; then exec 8<&-; return 1; fi
            exec 8<&-
            pass 'Server 数据已按明确确认删除。' 'Server data deleted after explicit confirmation.' ;;
    esac
}
advanced() {
    heading '高级设置' 'Advanced'
    say '1. 路径/版本/哈希  2. 重装当前版本  3. 服务状态  0. 返回' '1. Paths/version/hashes  2. Reinstall current version  3. Service status  0. Back'
    ask '选择' 'Select'
    case $REPLY in
        1) printf '%s\n%s\n%s\n%s\nServer SHA256=%s\nTunnel SHA256=%s\n' "$VERSION" "$BIN" "$DATA" "$META" "$SERVER_SHA" "$TUNNEL_SHA"
           if load_operator; then printf 'User=%s\nConfig=%s\nState=%s\n' "$OPERATOR" "$CONFIG_BASE" "$STATE_BASE"; fi ;;
        2) repair ;; 3) status_screen ;;
    esac
}
menu_text() {
    if [[ $1 == fresh ]]; then
        heading '安装与更新' 'Install and update'
        say '1. 安装 STRYNIUM Server\n2. 安装 STRYNIUM Tunnel\n3. 安装 Server + Tunnel\n4. 更新 / 修复已安装组件' \
            '1. Install STRYNIUM Server\n2. Install STRYNIUM Tunnel\n3. Install Server + Tunnel\n4. Update / repair installed components' | sed 's/\\n/\n/g'
        heading '运行与管理' 'Run and manage'
        say '5. 查看运行状态\n6. 查看访问与登录信息\n7. 查看日志\n8. 系统诊断\n9. 高级设置\n10. 卸载\n0. 退出' \
            '5. Runtime status\n6. Web access / login\n7. Logs\n8. Diagnostics\n9. Advanced\n10. Uninstall\n0. Exit' | sed 's/\\n/\n/g'
    else
        say '1. 安装 / 更新\n2. Server 管理\n3. Tunnel 管理\n4. 查看访问与登录信息\n5. 查看日志\n6. 系统诊断\n7. 高级设置\n8. 卸载\n0. 退出' \
            '1. Install / update\n2. Server management\n3. Tunnel management\n4. Web access / login\n5. Logs\n6. Diagnostics\n7. Advanced\n8. Uninstall\n0. Exit' | sed 's/\\n/\n/g'
    fi
}
dispatch() {
    local mode=$1 choice=$2
    if [[ $mode == fresh ]]; then
        case $choice in 1) install_server ;; 2) install_tunnel ;; 3) install_both ;; 4) repair ;; 5) status_screen ;; 6) access_screen ;; 7) logs_screen ;; 8) diagnostic ;; 9) advanced ;; 10) uninstall ;; esac
    else
        case $choice in 1) install_menu ;; 2) server_menu ;; 3) tunnel_menu ;; 4) access_screen ;; 5) logs_screen ;; 6) diagnostic ;; 7) advanced ;; 8) uninstall ;; esac
    fi
}
main() {
    export PATH=/usr/sbin:/usr/bin:/sbin:/bin
    umask 077
    ulimit -c 0
    [[ $EUID == 0 ]] || { printf '请使用 root 权限运行 STRYNIUM 安装器。\n' >&2; return 1; }
    colors; language_screen || return 0
    local command
    for command in python3 sha256sum stat realpath flock systemctl journalctl ip ss install find findmnt \
        getent useradd setpriv systemd-ask-password cmp cut awk grep sed mktemp readlink getconf hostname; do
        command -v "$command" >/dev/null || { fail "缺少依赖：$command（请由管理员安装）" "Missing dependency: $command (administrator must provision it)"; return 1; }
    done
    command -v curl >/dev/null || command -v wget >/dev/null || { fail '需要 curl 或 wget。' 'curl or wget required.'; return 1; }
    platform_check && arch_check || return 1
    # /run is root-controlled; /run/lock may be world-writable on Ubuntu.
    safe_path /run/strynium-installer.lock || return 1
    exec 9>/run/strynium-installer.lock
    flock -n 9 || { fail '另一个安装器正在运行。' 'Another installer is running.'; return 1; }
    TMP=$(mktemp -d /tmp/strynium-installer.XXXXXXXX) || return 1
    trap cleanup EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    safe_path "$ROOT" && safe_path "$BIN" && safe_path "$META" || return 1
    local mode code
    while true; do
        heading 'STRYNIUM Miner v1.0.0' 'STRYNIUM Miner v1.0.0'
        status_screen
        mode=fresh
        [[ ! -f $BIN/strynium-server && ! -f $BIN/strynium-tunnel ]] || mode=installed
        menu_text "$mode"; ask '选择' 'Select'
        [[ $REPLY != 0 ]] || break
        if dispatch "$mode" "$REPLY"; then :; else
            code=$?
            if [[ $code != 2 ]]; then warn '操作未完成；未宣称成功。请使用诊断，勿删除状态绕过错误。' 'Operation incomplete; success not claimed. Use diagnostics; do not erase state to bypass errors.'; fi
        fi
    done
}

# Sourcing is solely for isolated offline tests; normal execution has no bypass flags.
if [[ ${BASH_SOURCE[0]} == "$0" ]]; then main "$@"; fi
