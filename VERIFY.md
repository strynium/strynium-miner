# 下载文件校验

从 [本版 Releases](https://github.com/strynium/strynium-miner/releases/tag/v1.0.0-r33-d27) 下载软件包、`SHA256SUMS.txt` 与 `STRYNIUM-R33-D27-MANIFEST.json`，确保文件来自同一发布。

## Linux / Ubuntu

只下载部分包时，在下载目录执行：

```bash
sha256sum --ignore-missing -c SHA256SUMS.txt
```

确认实际要安装的文件明确显示 `OK`；缺少或被改名的文件不会因其他条目成功而得到验证。全套下载可用 `sha256sum -c SHA256SUMS.txt`。软件包解压后的文件也附带独立 `SHA256SUMS.txt`。

## Windows PowerShell

```powershell
Get-FileHash -LiteralPath .\STRYNIUM-Local-Windows-x64-D27.zip -Algorithm SHA256
```

把输出的完整 SHA-256 与校验文件对应文件名的值比较，大小写不影响结果；不要只比较首尾几位。

## 来源与签名

SHA-256 证明文件字节是否一致，不等于独立发布者数字签名。本发布未提供独立签名，Windows 程序未使用 Authenticode 签名。不要关闭系统防护来绕过拦截；应核对官方仓库和文件校验，并遵循管理员策略。

发布清单列出文件大小、构建版本、校验值与验证范围。GitHub 自动生成的 Source code 仅包含公开文档仓库，不是产品源码或安装包。

## 管理脚本

`install.sh` 从固定 Git 提交下载管理程序，并用入口内置 SHA-256 验证后执行。Release 同时附带 `install.sh`、`strynium-manager.py` 与独立的 `MANAGER-SHA256SUMS.txt`，可使用 `sha256sum -c MANAGER-SHA256SUMS.txt` 检查这两个脚本。软件包仍使用原 `SHA256SUMS.txt`。


## 本版验证范围

- 原生 Rust 完整工作区：**2782 通过、0 失败、16 忽略**。忽略项不计入通过数。
- 前端：服务端 **85** 项、本地端 **19** 项通过；严格 Clippy、独立本地端全部目标检查和五项合同检查通过。
- 本轮验证了 LTC 切换前处理已到达提交、非 BTC 队列满载时下发普通任务，并增加 BTC 本地拒绝诊断。现场拒绝率待验证。
- Windows / Linux 服务端及本地端完成重构建和四项隔离启动、接口检查；测试进程均已结束。
- 六个软件包逐文件核验程序、许可与 SHA-256；未包含现场原始证据和私密凭据。
- **实机限制**：软件回归与回放不等同于全部实机/矿池验收；实际拒绝率、抽水比例和 24 小时平滑仍需实测。
