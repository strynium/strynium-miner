# 安装与维护 · 服务端 R14 / 本地加密端 D11

从 [当前发布](https://github.com/strynium/strynium-miner/releases/tag/v1.0.0-r14-d11) 下载所需组件、`SHA256SUMS.txt` 和发布清单，先按 [VERIFY.md](VERIFY.md) 校验。保留包内 LICENSE、USE_TERMS 和 licenses 目录。无需 Rust、Node、Docker 或自行编译。

<a id="manager"></a>
## Linux / Ubuntu 一键安装与管理

云服务器通常只安装服务端，矿场电脑安装本地加密端。在云厂商控制台打开「远程连接 / 登录终端」，复制下面这一行命令并回车，然后选择「1 服务端 → 1 安装 / 更新」。缺少的基础组件会自动准备，不需要逐项手动安装。

```bash
bash <(curl -fsSL https://github.com/strynium/strynium-miner/raw/main/install.sh)
```

入口固定校验管理程序的 SHA-256，再进入中文交互菜单。已安装组件直接复用，缺少的从系统软件源自动安装；root 直接运行，普通账号自动申请 sudo 权限。后续重新运行上述命令可更新管理程序，日常维护用 `strynium-manage`。

技术范围：Linux x64、Python 3.8+、运行中的 systemd。容器、过旧系统或未知软件源可能不支持自动安装，脚本会说明原因；不会自动升级操作系统。无 systemd 的环境可使用下方 tar 包方式。

<a id="entry-troubleshooting"></a>
### 入口问题

上述一行命令需要在 Bash 终端运行，并已具备 curl 和可用的 HTTPS 证书。若极简 Ubuntu / Debian 镜像提示 `curl: command not found`，可先在 root 终端运行 `apt-get update && apt-get install -y curl ca-certificates`；普通账号在两条 apt-get 命令前加 sudo。其他发行版使用对应系统软件源安装这两个组件，再运行上方一行命令。运行环境的后续准备由脚本自动完成。

### 首次安装

1. 选择服务端或本地加密端，再选「安装 / 更新」。两端可安装在不同电脑，按组件独立管理。
2. 服务端填写实际公网 IPv4；留空仅本机访问。脚本创建专用服务用户，并从 **20000–60000** 随机选一个未占用的 Web 端口，内部 API 另选端口且仅监听本机。
3. 成功后显示完整地址和初始登录信息：**账号 `strynium`，密码 `Strynium2026.`**。首次登录必须修改账号密码；新密码至少 8 位，包含大小写字母、数字及特殊字符。公开初始凭据仅用于首次初始化。
4. 在云安全组和防火墙放行实际 Web、授权和代理端口；脚本不修改防火墙。证书信任应按实际访问地址配置。
5. 本地端选择现有普通 Linux 用户和数据目录。脚本设置该服务的内存锁定额度，以普通用户运行；控制台只监听本机，默认 `17892`。从「打开控制台」取得完整链接，按下方配对步骤使用。

首次随机端口仅指**管理脚本全新部署的服务端 Web 端口**。更新或接管已有服务保留原端口和账号；手动 tar / DEB 启动默认仍为 8443。进程开机启动不等于本地转发自动解锁；本地端每次重启仍需在页面解锁并「应用并启动」。

### 常用维护命令

```bash
strynium-manage                     # 中文菜单
strynium-manage server update       # 更新服务端
strynium-manage local update        # 更新本地端
strynium-manage server status       # 地址、端口、版本和进程
strynium-manage server logs         # 最近 100 条日志
strynium-manage server diagnose     # 本机健康检查
strynium-manage server port         # 修改 Web 端口（支持 random）
strynium-manage server reset-account # 交互重置账号密码
strynium-manage local console       # 本地端完整登录链接
strynium-manage local restart       # 重启本地端
strynium-manage server stop         # 停止服务端
strynium-manage server start        # 启动服务端
strynium-manage local uninstall     # 卸载本地端，保留数据
strynium-manage server uninstall    # 卸载服务端，保留数据
```

安装、更新、启停、重启、状态、日志、诊断、控制台链接与卸载支持两端。`port` 和 `reset-account` 仅针对服务端。密码在交互终端输入，不回显，不经命令参数、环境变量或明文文件保存。首次重置若缺少账号维护组件，将从系统软件源自动准备。

修改 Web 端口、重置账号会短暂停止对应服务并备份，随后原来运行的服务会重启并检查。失败时恢复原配置；原来已停止的服务保持停止。**两步验证及恢复码、矿机自报账号、抽水配置、证书和客户端身份均保留。** 重置控制台密码不能解除本地端的加密存储密码，也不会移除两步验证。

### 更新、备份和现有部署

下载仅使用官方 GitHub 正式 Release，校验清单、文件大小、SHA-256 和包内校验后才安装。程序按版本独立存放，启动检查失败时回退；更新保留已有 Web 端口、账号密码与数据。已是最新版本时不重复安装。

| 内容 | 默认位置 |
| :--- | :--- |
| 管理命令 | `/usr/local/sbin/strynium-manage` |
| 管理器状态 | `/etc/strynium-manager`（仅 root 可读） |
| 软件版本 | `/opt/strynium-managed/server`、`/opt/strynium-managed/local` |
| 服务端数据 | `/var/lib/strynium` |
| 本地端数据 | 所选用户的 `~/.local/state/STRYNIUM/LocalEncryption`，可选择原目录 |
| 操作前备份 | `/var/backups/strynium-manager`（仅 root 可读，包含敏感配置） |
| systemd 单元 | `strynium.service`、`strynium-local.service` |

已有 R14 标准 `strynium.service`（启动器 `/usr/bin/strynium` 或 `/opt/strynium/scripts/start-console.sh`）可确认后接管。保留原服务单元及环境配置，仅增加程序启动覆盖文件。外部 EnvironmentFile、未知启动器、数据所有者不符等情况会拒绝自动接管，避免误覆盖。

接管部署的卸载会停用服务、移除管理器版本和覆盖文件，保留原服务文件及原 DEB 包；如需卸载原 DEB，可再执行 `sudo apt remove strynium`。普通管理器新装直接删除自己的程序目录。所有卸载均保留运行数据、操作备份和管理命令，不提供自动清空数据选项。

下列手动安装方式继续可用，不要让手动进程与 systemd 服务同时使用同一数据目录。

## Windows x64

服务端：完整解压 `STRYNIUM-Server-Windows-x64-R14.zip`，运行 `Start-STRYNIUM.cmd`。浏览器控制台地址以启动输出为准。

本地端：完整解压 `STRYNIUM-Local-Windows-x64-D11.zip`，运行 `STRYNIUM-Local.exe`。保留 `strynium-browse.exe`、运行库及 licenses。系统需单独安装 Microsoft Edge WebView2 Runtime；本包不附带完整浏览器。

本地窗口 X 隐藏到系统托盘，右键托盘退出才会停止转发。初始窗口按当前屏幕宽 59%、高 73% 设置。更新前从托盘退出，再解压到新目录，用原用户启动，保留原数据。

<a id="linux-local"></a>
## Linux / Ubuntu x64 本地加密端

### Ubuntu DEB

```bash
sudo apt install ./strynium-local_1.0.0+20261028.d11_amd64.deb
strynium-local
```

安装命令用 sudo；随后启动命令使用普通用户。DEB 安装在 `/opt/strynium-local`，提供 `/usr/bin/strynium-local`，不自动开启矿机转发。

### Linux tar.gz

```bash
tar -xzf STRYNIUM-Local-Linux-x64-D11.tar.gz
cd STRYNIUM-Local-Linux-x64-D11
./scripts/start-local-client.sh
```

需要 `util-linux`（提供 prlimit）与 `sudo`。桌面自动打开浏览器使用 `xdg-utils`。程序为 x86_64 静态链接版本；这减少系统库差异，但不保证所有发行版兼容。

安全存储需要锁定内存。启动器在额度不足时请求 sudo，为**当前进程**设置额度，之后仍以原普通用户运行，不修改系统全局限额。

控制台只监听 `127.0.0.1`，默认端口 `17892`。打开启动终端打印的完整链接；链接含当前会话访问密钥，不要公开。可用 `strynium-local --port 17893` 选择其他本机控制台端口。

### 无桌面环境

在矿场 Linux 主机运行 `strynium-local --no-browser`（tar 包使用 `./scripts/start-local-client.sh --no-browser`），保持进程运行。在自己的管理电脑另开终端：

```bash
ssh -L 17892:127.0.0.1:17892 your-user@your-linux-host
```

用管理电脑的浏览器打开 Linux 启动终端打印的完整本机链接。SSH 中的用户和主机需替换为自己的信息；不要把本地控制台绑定到公网。

### 配对、更新与卸载

复制本地设备标识，到服务端「前置加密」生成授权。返回本地「云端配对」导入，按提示设置安全存储密码；在「连接端口」同步并应用。矿机填写显示的局域网接入地址，账号仍由矿机上报。

每次进程重启后重新解锁安全存储，并显式启动转发。关闭浏览器不退出进程；运行终端按 Ctrl+C 退出。不要在脚本、命令行或日志中存储解锁密码。

数据目录：`${XDG_STATE_HOME:-$HOME/.local/state}/STRYNIUM/LocalEncryption`；Windows 对应 `%LOCALAPPDATA%\STRYNIUM\LocalEncryption`。沿用原用户和数据目录，更新前先退出旧进程并备份数据。DEB 更新再次执行 apt install，tar 更新解压到新目录。

卸载 DEB：`sudo apt remove strynium-local`。默认保留用户配置和凭据。tar 包在退出后删除软件目录即可，不删除数据目录。

### 可选上网行为模拟

默认关闭。Linux 使用系统 Chromium 或 Google Chrome，需从官方渠道单独安装；没有浏览器不影响矿机转发。首次缺少浏览器时页面部分提示仍沿用 Windows 的 WebView2 文案，请按此处 Linux 依赖说明处理。

本轮未验证真实外部视频站点、完整 Linux 浏览器自动化或所有发行版。Windows 浏览模块使用系统 WebView2。浏览功能会额外消耗资源，不作为加密安全或链路稳定保证。

<a id="server"></a>
## Linux / Ubuntu x64 服务端

新装 Ubuntu：

```bash
sudo apt install ./strynium_1.0.0+20261028.r14_amd64.deb
strynium
```

Linux：完整解压服务端 tar 包，在目录运行 `sh scripts/start-console.sh`。

默认控制台为 `https://127.0.0.1:8443`，数据目录 `${XDG_DATA_HOME:-$HOME/.local/share}/STRYNIUM/integrated`。以实际输出为准。DEB 提供程序，不会自动创建生产服务账号、systemd 服务或放行防火墙。

初始账号 `strynium`、初始密码 `Strynium2026.`，首次登录按提示修改管理员账号密码；不要删除数据目录来绕过登录。

### 新建云服务器部署

先完成本机初始化，再由管理员选择受控的数据目录、专用服务账号和访问范围。启动器支持环境变量：

| 变量 | 作用 |
| :--- | :--- |
| `STRYNIUM_CONSOLE_MODE` | 默认 `local-only`；云访问为 `public-cloud` |
| `STRYNIUM_CONSOLE_PUBLIC_IP` | 实际公网 IPv4，用于云端访问配置 |
| `STRYNIUM_CONSOLE_HTTPS_PORT` | Web 管理端口，默认 8443 |
| `STRYNIUM_DATA_HOME` | 显式指定需持久保存的数据目录 |
| `STRYNIUM_API_PORT` | 仅本机的内部 API 端口，默认 18080 |

Web 管理端口、授权端口和代理端口按需放行；内部 API 只允许本机访问。证书信任需与实际地址匹配，不通过关闭证书校验来消除浏览器提示。

### 已有 R13 Ubuntu 部署升级 R14

本发布附带 [upgrade-r14.sh](https://github.com/strynium/strynium-miner/releases/download/v1.0.0-r14-d11/upgrade-r14.sh)，仅用于已有 `strynium` 服务账号、`/var/lib/strynium` 数据目录的部署。确认没有正在进行的配置更改，并预留短暂重启时间：

```bash
sudo sh ./upgrade-r14.sh ./strynium_1.0.0+20261028.r14_amd64.deb YOUR_PUBLIC_IPV4
```

将 `YOUR_PUBLIC_IPV4` 替换为自己的公网 IPv4。脚本固定校验 R14 DEB 的版本、架构与 SHA-256，备份到 `/root/strynium-before-r14-*` 后安装，保留原服务单元和数据。它不是通用一键安装脚本，不适用于空白服务器或不同目录布局。

已有 systemd 部署通过 `systemctl status strynium`、`journalctl -u strynium -n 100 --no-pager` 检查状态；正常停止后再卸载 `strynium` 软件包。自行配置的 systemd 单元需由管理员相应停用，默认保留数据。

## 验证范围

本轮 Linux 本地端在 **Ubuntu 26.04 x64 / WSL2** 完成正式构建；126 项 Rust 测试通过，5 项忽略。DEB 在隔离 dpkg 根目录安装/卸载，依赖由宿主环境提供，该隔离步骤不验证 apt 依赖解析。

安装后的程序通过 12 项本地端与真实服务端集成检查：控制台资源、会话/来源校验、配对、端口冲突、授权转发、矿机去重与离线状态、凭据加密、重启恢复和撤销。测试矿池为本机合成数据。服务端 R14 与 Windows D11 延用此前验证的原始包，哈希未变。

其他发行版、全部 Windows/浏览器版本和物理矿场环境没有在本轮逐一验证。详细校验与范围见发布清单。

统一管理器另在 Ubuntu 26.04 x64 / WSL2 的真实 systemd 环境验证：两端安装、启停、更新、卸载保留数据、随机端口、初始登录、账号重置、端口占用拒绝、更新与配置失败回退。单元测试覆盖启用中的两步验证保留、配置链接拒绝、写入故障与下载重定向限制。具体范围见 [管理器验证记录](docs/MANAGER_VERIFICATION.md)。
