#!/usr/bin/env bash
# STRYNIUM Linux/Ubuntu installer and management entry point.
set -Eeuo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
umask 077

fail() { printf 'STRYNIUM: %s\n' "$*" >&2; exit 1; }
[[ $(uname -s) == Linux ]] || fail '仅支持 Linux / Ubuntu。'
[[ $(uname -m) == x86_64 ]] || fail '当前软件包仅支持 x64。'
[[ $EUID -eq 0 ]] || fail '请运行 sudo bash strynium-install.sh；本地端程序仍以普通用户运行。'

need_dependencies=0
command -v python3 >/dev/null 2>&1 || need_dependencies=1
command -v curl >/dev/null 2>&1 || need_dependencies=1
command -v sha256sum >/dev/null 2>&1 || need_dependencies=1
[[ -s /etc/ssl/certs/ca-certificates.crt || -s /etc/pki/tls/certs/ca-bundle.crt ]] || need_dependencies=1
if [[ $need_dependencies -eq 1 ]]; then
    printf '需要从系统软件源安装 Python 3、curl、CA 证书及校验工具，输入 yes 继续：' >/dev/tty
    read -r answer </dev/tty
    [[ $answer == yes ]] || fail '已取消。'
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update
        apt-get install -y python3 curl ca-certificates coreutils
    elif command -v dnf >/dev/null 2>&1; then
        dnf install -y python3 curl ca-certificates coreutils
    elif command -v yum >/dev/null 2>&1; then
        yum install -y python3 curl ca-certificates coreutils
    elif command -v pacman >/dev/null 2>&1; then
        pacman -S --needed --noconfirm python curl ca-certificates coreutils
    elif command -v zypper >/dev/null 2>&1; then
        zypper --non-interactive install python3 curl ca-certificates coreutils
    else
        fail '请先安装 Python 3.8+、curl、CA 证书与 sha256sum。'
    fi
fi
python3 -c 'import sys; sys.exit(sys.version_info < (3, 8))' || fail '需要 Python 3.8 或更新版本。'

# This immutable commit and digest are updated together after manager acceptance.
manager_ref='3329e15671034310bd36a8c426401ade298f0424'
manager_sha256='be8d25780f5bd9a5b446e8d54601b29bbe6309c94c610fdad54b198970705784'
manager_url="https://raw.githubusercontent.com/strynium/strynium-miner/${manager_ref}/scripts/strynium_manager.py"
temporary=$(mktemp -d /tmp/strynium-install.XXXXXXXX)
trap 'rm -rf -- "$temporary"' EXIT
curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
    --connect-timeout 15 --max-time 120 --retry 2 "$manager_url" -o "$temporary/manager.py"
printf '%s  %s\n' "$manager_sha256" "$temporary/manager.py" | sha256sum --check --status \
    || fail '管理程序校验失败，未执行。请重新下载安装入口。'
python3 "$temporary/manager.py" "$@"
