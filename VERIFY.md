# 下载文件校验

从 [本版 Releases](https://github.com/strynium/strynium-miner/releases/tag/v1.0.0-r21-d15) 下载软件包、`SHA256SUMS.txt` 与 `STRYNIUM-R21-D15-MANIFEST.json`，确保文件来自同一发布。

## Linux / Ubuntu

只下载部分包时，在下载目录执行：

```bash
sha256sum --ignore-missing -c SHA256SUMS.txt
```

确认实际要安装的文件明确显示 `OK`；缺少或被改名的文件不会因其他条目成功而得到验证。全套下载可用 `sha256sum -c SHA256SUMS.txt`。软件包解压后的文件也附带独立 `SHA256SUMS.txt`。

## Windows PowerShell

```powershell
Get-FileHash -LiteralPath .\STRYNIUM-Local-Windows-x64-D15.zip -Algorithm SHA256
```

把输出的完整 SHA-256 与校验文件对应文件名的值比较，大小写不影响结果；不要只比较首尾几位。

## 来源与签名

SHA-256 证明文件字节是否一致，不等于独立发布者数字签名。本发布未提供独立签名，Windows 程序未使用 Authenticode 签名。不要关闭系统防护来绕过拦截；应核对官方仓库和文件校验，并遵循管理员策略。

发布清单列出文件大小、构建版本、校验值与验证范围。GitHub 自动生成的 Source code 仅包含公开文档仓库，不是产品源码或安装包。

## 管理脚本

`install.sh` 从固定 Git 提交下载管理程序，并用入口内置 SHA-256 验证后执行。Release 同时附带 `install.sh`、`strynium-manager.py` 与独立的 `MANAGER-SHA256SUMS.txt`，可使用 `sha256sum -c MANAGER-SHA256SUMS.txt` 检查这两个脚本。软件包仍使用原 `SHA256SUMS.txt`。


## 本版验证范围

日期：2026-11-02。构建源码提交：`bf7f7831b99b3929340f53462f368f9acbf41a8e`。

### 已完成

- 原生完整 Rust 工作区测试：2701 通过，0 失败，16 忽略（不计为通过）。包括 BTC 原有回归与七个非 BTC 币种的协议、工作量、抽水和任务恢复检查。
- 服务端界面 72 项、本地界面 19 项通过；5 项权威合同校验通过。
- Clippy 严格检查通过；独立本地端工作区全部目标检查通过。
- Windows x64 与 Linux x64 musl 完整正式构建通过。
- Windows/Linux 服务端及本地端四组隔离启动、会话保护、初始状态检查通过；仅停止各自测试进程。
- 服务端与独立本地端源码逐项核对，第三方许可重新收集。

### 验证边界

首次完整测试因开发机磁盘已满中断，完整失败输出保留；旧构建缓存移至其他磁盘后重新完成上述原生测试。另一次重跑发现 DASH 测试仍沿用旧币种的 TH/s 期望，已按 DASH 单位合同修正为 GH/s 后重新执行。完整工作区还检出两处旧隧道握手样本及一处将纯地址值误判为网络I/O的边界断言，已修正后全量重新执行；保留失败输出。BTC握手样本未变，旧编号8仍拒绝，DASH使用编号9；网络连接与DNS API仍禁止。未删除测试证据。

本记录证明当前软件级验证完成，不证明所有矿机固件与商业矿池变体兼容，不代表矿机硬件故障已经排除，也不代表 24 小时现场抽水比例或曲线平滑通过验收。部署后需要按币种核对真实份额、上下游任务及主池恢复。

本版两端均重新构建，清单不再沿用旧 D14 的包身份。
