# 下载文件校验

从 [本版 Releases](https://github.com/strynium/strynium-miner/releases/tag/v1.0.0-r22-d16) 下载软件包、`SHA256SUMS.txt` 与 `STRYNIUM-R22-D16-MANIFEST.json`，确保文件来自同一发布。

## Linux / Ubuntu

只下载部分包时，在下载目录执行：

```bash
sha256sum --ignore-missing -c SHA256SUMS.txt
```

确认实际要安装的文件明确显示 `OK`；缺少或被改名的文件不会因其他条目成功而得到验证。全套下载可用 `sha256sum -c SHA256SUMS.txt`。软件包解压后的文件也附带独立 `SHA256SUMS.txt`。

## Windows PowerShell

```powershell
Get-FileHash -LiteralPath .\STRYNIUM-Local-Windows-x64-D16.zip -Algorithm SHA256
```

把输出的完整 SHA-256 与校验文件对应文件名的值比较，大小写不影响结果；不要只比较首尾几位。

## 来源与签名

SHA-256 证明文件字节是否一致，不等于独立发布者数字签名。本发布未提供独立签名，Windows 程序未使用 Authenticode 签名。不要关闭系统防护来绕过拦截；应核对官方仓库和文件校验，并遵循管理员策略。

发布清单列出文件大小、构建版本、校验值与验证范围。GitHub 自动生成的 Source code 仅包含公开文档仓库，不是产品源码或安装包。

## 管理脚本

`install.sh` 从固定 Git 提交下载管理程序，并用入口内置 SHA-256 验证后执行。Release 同时附带 `install.sh`、`strynium-manager.py` 与独立的 `MANAGER-SHA256SUMS.txt`，可使用 `sha256sum -c MANAGER-SHA256SUMS.txt` 检查这两个脚本。软件包仍使用原 `SHA256SUMS.txt`。


## 本版验证范围

冻结源码：9482127a3e8b6fccee5b0b7134d0c735d88f174c。
- 原生完整 Rust 工作区：2709 通过、0 失败、16 忽略（不计为通过）。
- 严格 Clippy、服务端/本地端界面与五项权威合同检查通过。
- Windows/Linux 服务端与本地端四组隔离启动检查通过；独立本地端源码全部目标检查通过。
- BCH 8191.875 难度及 nonce2 8→4→8 回放；抽水接受、拒绝、结果未知、恢复客户任务与持久账本检查。
- KAS 小数难度回放；七个非 BTC 币种十种已支持协议变体的拒绝/断连回放。

本报告是软件回归结果，不代替所有矿机与商业矿池的实测，不代表24小时比例或曲线平滑验收。未降低费率、身份、历史信用和未知提交不重放要求；BTC费率计量未改。
早期未优化 ETC 回放失败及修复前/测试夹具失败均保留原始日志；正式结果以本轮冻结源码的完整测试为准。
