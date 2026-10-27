#!/usr/bin/env bash
# STRYNIUM Linux/Ubuntu installer and management entry point.
set -Eeuo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
umask 077

fail() { printf 'STRYNIUM: %s\n' "$*" >&2; exit 1; }
[[ $(uname -s) == Linux ]] || fail '仅支持 Linux / Ubuntu。'
[[ $(uname -m) == x86_64 ]] || fail '当前软件包仅支持 x64。'
if [[ $EUID -ne 0 ]]; then
    command -v sudo >/dev/null 2>&1 || fail '当前账号没有管理员权限。请在云服务器控制台使用 root 登录，再运行安装命令。'
    printf '正在申请安装权限；如有提示，请输入当前 Linux 账号的密码。\n'
    exec sudo -- bash "$0" "$@"
fi
[[ -d /run/systemd/system ]] || fail '当前环境不支持后台服务管理。请在完整的 Linux 云主机中运行；容器或精简环境请使用软件包手动启动。'

printf '正在检查安装环境，已有组件会直接复用……\n'
python_ready() { command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(sys.version_info < (3, 8))'; }
ca_ready() { [[ -s /etc/ssl/certs/ca-certificates.crt || -s /etc/pki/tls/certs/ca-bundle.crt ]]; }

need_dependencies=0
python_ready || need_dependencies=1
command -v curl >/dev/null 2>&1 || need_dependencies=1
command -v sha256sum >/dev/null 2>&1 || need_dependencies=1
ca_ready || need_dependencies=1
if [[ $need_dependencies -eq 1 ]]; then
    printf '正在从系统软件源自动准备缺少的运行组件，请稍候……\n'
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 curl ca-certificates coreutils
    elif command -v dnf >/dev/null 2>&1; then
        dnf install -y python3 curl ca-certificates coreutils
    elif command -v yum >/dev/null 2>&1; then
        yum install -y python3 curl ca-certificates coreutils
    elif command -v pacman >/dev/null 2>&1; then
        pacman -S --needed --noconfirm python curl ca-certificates coreutils
    elif command -v zypper >/dev/null 2>&1; then
        zypper --non-interactive install python3 curl ca-certificates coreutils
    else
        fail '暂不支持此系统的自动安装。请查看 INSTALL.md 中的手动安装方式。'
    fi
fi
python_ready || fail '当前系统软件源提供的运行环境过旧。请使用较新的 Ubuntu/Debian 等系统，或按 INSTALL.md 手动运行软件包；脚本不会自动升级操作系统。'
command -v curl >/dev/null 2>&1 && command -v sha256sum >/dev/null 2>&1 && ca_ready \
    || fail '基础组件准备失败，请检查系统软件源或网络后重新运行。'
printf '环境检查完成，正在准备 STRYNIUM 管理菜单……\n'

# This immutable commit and digest are updated together after manager acceptance.
manager_ref='65ced3caf28f34d7a001e2e32d3926a2a4af558a'
manager_sha256='3654984050478d5e0825bb7d76a2b7a2e79c36969e69ca1ed913eee73c7e9396'
manager_url="https://raw.githubusercontent.com/strynium/strynium-miner/${manager_ref}/scripts/strynium_manager.py"
temporary=$(mktemp -d /tmp/strynium-install.XXXXXXXX)
trap 'rm -rf -- "$temporary"' EXIT
curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
    --connect-timeout 15 --max-time 120 --retry 2 "$manager_url" -o "$temporary/manager.py"
printf '%s  %s\n' "$manager_sha256" "$temporary/manager.py" | sha256sum --check --status \
    || fail '管理程序校验失败，未执行。请重新下载安装入口。'
python3 "$temporary/manager.py" "$@"
