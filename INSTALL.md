# 安装与维护 · 服务端 R14 / 本地加密端 D11

从 [当前发布](https://github.com/strynium/strynium-miner/releases/tag/v1.0.0-r14-d11) 下载所需组件、`SHA256SUMS.txt` 和发布清单，先按 [VERIFY.md](VERIFY.md) 校验。保留包内 LICENSE、USE_TERMS 和 licenses 目录。无需 Rust、Node、Docker 或自行编译。

统一安装维护菜单尚未交付；仓库旧 `install.sh` 已停用。以下为本版可用的安装方式。

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

首次使用授权部署渠道提供的初始凭据登录，按提示修改管理员账号密码；不要删除数据目录来绕过登录。

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
