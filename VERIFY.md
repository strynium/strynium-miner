# 下载文件校验

从 [本版 Releases](https://github.com/strynium/strynium-miner/releases/tag/v1.0.0-r20-d14) 下载软件包、`SHA256SUMS.txt` 与 `STRYNIUM-R20-D14-MANIFEST.json`，确保文件来自同一发布。

## Linux / Ubuntu

只下载部分包时，在下载目录执行：

```bash
sha256sum --ignore-missing -c SHA256SUMS.txt
```

确认实际要安装的文件明确显示 `OK`；缺少或被改名的文件不会因其他条目成功而得到验证。全套下载可用 `sha256sum -c SHA256SUMS.txt`。软件包解压后的文件也附带独立 `SHA256SUMS.txt`。

## Windows PowerShell

```powershell
Get-FileHash -LiteralPath .\STRYNIUM-Local-Windows-x64-D14.zip -Algorithm SHA256
```

把输出的完整 SHA-256 与校验文件对应文件名的值比较，大小写不影响结果；不要只比较首尾几位。

## 来源与签名

SHA-256 证明文件字节是否一致，不等于独立发布者数字签名。本发布未提供独立签名，Windows 程序未使用 Authenticode 签名。不要关闭系统防护来绕过拦截；应核对官方仓库和文件校验，并遵循管理员策略。

发布清单列出文件大小、构建版本、校验值与验证范围。GitHub 自动生成的 Source code 仅包含公开文档仓库，不是产品源码或安装包。

## 管理脚本

`install.sh` 从固定 Git 提交下载管理程序，并用入口内置 SHA-256 验证后执行。Release 同时附带 `install.sh`、`strynium-manager.py` 与独立的 `MANAGER-SHA256SUMS.txt`，可使用 `sha256sum -c MANAGER-SHA256SUMS.txt` 检查这两个脚本。软件包仍使用原 `SHA256SUMS.txt`。

## 本版验证范围

本版四个相关 crate 的完整原生回归：**1416 通过、0 失败、11 忽略**；测试配置为 `test opt-level=1; debug assertions and overflow checks enabled`。控制台测试：**72 通过、0 失败、0 跳过**；相关 crate 的全部目标通过 Clippy `-D warnings` 检查。忽略与跳过不计为通过，局部测试不重复累计。

Windows / Linux 服务端由正式入口重新进行 release 构建；两端均通过独立临时目录、仅本机回环地址的 HTTPS 启动与管理员设备 API 检查，读取至少两次真实设备样本，间隔不少于 1 秒，并核对产品版本与构建标识。测试进程均已退出。

6 个软件包已完成逐文件、许可清单、内外校验和与隐私检查：三个 R20 服务端包采用本轮新构建，三个 D14 本地端包与原发布逐字节相同。管理脚本已通过服务端与本地端选包、解压、校验和二进制版本检查。这些是本地包与管理脚本验证，不替代发布后的在线下载复核或真实矿场长期验收。

本轮重点验证真实难度下降后的准备结束、准备期间客户主池继续、旧任务不重播、当前身份与上下文检查、限额下的调度公平性，以及准备失败恰好一次进入既有熔断处理。测试辅助推进准备截止时间只用于确定性测试，不能当作实际等待 600 秒或矿场持续运行的证明。

忽略项、隔离测试、真实平台运行和软件包完整性检查分别记录。局部测试不重复累计进完整回归，历史通过结果不移作本版证据。软件测试不代表已完成实际两小时、六小时或 24 小时矿场稳定性验收，也不代表万连接容量已通过。

## 本次组件来源

三个 R20 服务端包由本版服务端源码重新构建；三个 D14 本地加密端包逐字节复用 R18 / D14 发布的原包，SHA-256 保持不变。本地端 Ubuntu 文件名仍为 `strynium-local_1.0.0+20261101.d14_amd64.deb`。

发布清单分别记录服务端的新源码、构建与验证来源，以及 D14 原包来源。新的 Release 标签不表示本地端重新编译。仪表盘显示正式产品版本 **v1.0.0**；安装包与发布清单中的 R20 / D14 编号用于区分实际构建。
