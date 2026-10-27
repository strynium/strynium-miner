#!/usr/bin/env bash
# Copyable entry for cloud terminals, including minimal images without curl.
set -e
as_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo -- "$@"
  else
    echo '请在云服务器控制台使用 root 登录，再执行此命令。' >&2; exit 1
  fi
}
if ! command -v curl >/dev/null 2>&1 || { [ ! -s /etc/ssl/certs/ca-certificates.crt ] && [ ! -s /etc/pki/tls/certs/ca-bundle.crt ]; }; then
  echo '正在自动准备下载工具，请稍候……'
  if command -v apt-get >/dev/null 2>&1; then
    as_root apt-get update
    as_root apt-get install -y curl ca-certificates
  elif command -v dnf >/dev/null 2>&1; then
    as_root dnf install -y curl ca-certificates
  elif command -v yum >/dev/null 2>&1; then
    as_root yum install -y curl ca-certificates
  elif command -v pacman >/dev/null 2>&1; then
    as_root pacman -S --needed --noconfirm curl ca-certificates
  elif command -v zypper >/dev/null 2>&1; then
    as_root zypper --non-interactive install curl ca-certificates
  else
    echo '暂不支持此系统的自动安装，请查看安装说明。' >&2; exit 1
  fi
fi
curl -fsSL --proto '=https' --proto-redir '=https' --connect-timeout 15 --max-time 120 --retry 2 \
  https://raw.githubusercontent.com/strynium/strynium-miner/main/install.sh -o strynium-install.sh
bash strynium-install.sh
