# 安装与维护 · 服务端 R15 / 本地加密端 D12

从 [当前发布](https://github.com/strynium/strynium-miner/releases/tag/v1.0.0-r15-d12) 下载所需组件、`SHA256SUMS.txt` 和发布清单，先按 [VERIFY.md](VERIFY.md) 校验。保留包内 LICENSE、USE_TERMS 和 licenses 目录。无需 Rust、Node、Docker 或自行编译。

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
2. 服务端自动识别公网 IPv4，无需手动填写；只有识别失败或地址不明确才提示输入。此时输入 `local` 可选择仅本机访问，空白不会再静默选择本机模式。脚本创建专用服务用户，并从 **20000–60000** 随机选一个未占用的 Web 端口，内部 API 另选端口且仅监听本机。
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
strynium-manage server public-ip     # 自动修复公网访问地址，保留端口和数据
strynium-manage local console       # 本地端完整登录链接
strynium-manage local restart       # 重启本地端
strynium-manage server stop         # 停止服务端
strynium-manage server start        # 启动服务端
strynium-manage local uninstall     # 卸载本地端，保留数据
strynium-manage server uninstall    # 卸载服务端，保留数据
```

安装、更新、启停、重启、状态、日志、诊断、控制台链接与卸载支持两端。`port`、`reset-account` 和 `public-ip` 仅针对服务端。密码在交互终端输入，不回显，不经命令参数、环境变量或明文文件保存。首次重置若缺少账号维护组件，将从系统软件源自动准备。

修改 Web 端口、重置账号会短暂停止对应服务并备份，随后原来运行的服务会重启并检查。失败时恢复原配置；原来已停止的服务保持停止。**两步验证及恢复码、矿机自报账号、抽水配置、证书和客户端身份均保留。** 重置控制台密码不能解除本地端的加密存储密码，也不会移除两步验证。

### 自动识别与现有地址修复

新安装优先使用 SSH 连接中的服务端公网地址、阿里云实例元数据或唯一的本机公网网卡地址；仅有内网网卡时使用两次直接 HTTPS 地址查询，结果一致才采用。查询超时、返回内网地址或多个候选不明确时提示手动输入，不静默退回 `127.0.0.1`。查询出口 IP 不能验证云安全组或 NAT 入站映射是否放行，按实际网络配置开放显示的端口。

旧安装只显示 `127.0.0.1` 时，重新运行首页一行命令更新管理器，选择 **1 服务端 → 12 自动修复公网访问地址**，或运行 `strynium-manage server public-ip`。自动识别成功后保留现有 Web 端口、账号和业务数据，备份后应用公网访问配置；运行中的服务会短暂重启并检查，失败时回退。原来停止的服务仍保持停止。已有自定义访问域名或 HTTPS 证书时不会擅自覆盖，需先核对实际地址和证书。

普通“安装 / 更新”继续保留已配置的访问模式，不会将主动选择本机模式的既有服务自动改成公网服务。

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

已有 R14 或更早标准 `strynium.service`（启动器 `/usr/bin/strynium` 或 `/opt/strynium/scripts/start-console.sh`）可确认后接管。保留原服务单元及环境配置，仅增加程序启动覆盖文件。外部 EnvironmentFile、未知启动器、数据所有者不符等情况会拒绝自动接管，避免误覆盖。

接管部署的卸载会停用服务、移除管理器版本和覆盖文件，保留原服务文件及原 DEB 包；如需卸载原 DEB，可再执行 `sudo apt remove strynium`。普通管理器新装直接删除自己的程序目录。所有卸载均保留运行数据、操作备份和管理命令，不提供自动清空数据选项。

下列手动安装方式继续可用，不要让手动进程与 systemd 服务同时使用同一数据目录。

## Windows x64

服务端：完整解压 `STRYNIUM-Server-Windows-x64-R15.zip`，运行 `Start-STRYNIUM.cmd`。浏览器控制台地址以启动输出为准。

本地端：完整解压 `STRYNIUM-Local-Windows-x64-D12.zip`，运行 `STRYNIUM-Local.exe`。保留 `strynium-browse.exe`、运行库及 licenses。系统需单独安装 Microsoft Edge WebView2 Runtime；本包不附带完整浏览器。

本地窗口 X 隐藏到系统托盘，右键托盘退出才会停止转发。初始窗口按当前屏幕宽 59%、高 73% 设置。更新前从托盘退出，再解压到新目录，用原用户启动，保留原数据。

<a id="linux-local"></a>
## Linux / Ubuntu x64 本地加密端

### Ubuntu DEB

```bash
sudo apt install ./strynium-local_1.0.0+20261031.d12_amd64.deb
strynium-local
```

安装命令用 sudo；随后启动命令使用普通用户。DEB 安装在 `/opt/strynium-local`，提供 `/usr/bin/strynium-local`，不自动开启矿机转发。

### Linux tar.gz

```bash
tar -xzf STRYNIUM-Local-Linux-x64-D12.tar.gz
cd STRYNIUM-Local-Linux-x64-D12
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
sudo apt install ./strynium_1.0.0+20261031.r15_amd64.deb
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

### 已有部署更新至 R15

继续使用首页一键命令，选择 **1 服务端 → 1 安装 / 更新**。本地端选择 **2 本地加密端 → 1 安装 / 更新**。

管理器校验最新发布清单和软件包，备份后切换版本；保留既有账号、端口、证书、授权和数据，运行中的服务会短暂重启，失败回退。原已停止的服务保持停止。管理器部署不要另用 apt 替换 current 指向的程序；Linux 本地端更新后仍按原流程解锁并应用转发。

已有 systemd 部署通过 `systemctl status strynium`、`journalctl -u strynium -n 100 --no-pager` 检查状态；正常停止后再卸载 `strynium` 软件包。自行配置的 systemd 单元需由管理员相应停用，默认保留数据。

## 验证范围

本次 Windows / Linux 两组件构建及隔离控制台启动通过；956 项相关回归通过、12 项默认忽略，最终连接专项 10 项通过（有重叠，不能相加）。更新成功、失败回退、保持停止状态的隔离事务场景通过。

DEB 已验证解包、二进制及内部校验；未重新验证所有发行版的 apt 依赖解析、全部 ASIC/商业矿池与长时间浸泡运行。先单台矿机连续测试至少 30 分钟。详见 [R15 / D12 验证说明](docs/RELEASE_R15_D12.md)。

管理器 1.0.3 代码与固定提交校验未改动，其此前验证记录见 [管理器验证](docs/MANAGER_VERIFICATION.md)。
