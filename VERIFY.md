# 下载文件校验

从 [本版 Releases](https://github.com/strynium/strynium-miner/releases/tag/v1.0.0-r19-d14) 下载软件包、`SHA256SUMS.txt` 与 `STRYNIUM-R19-D14-MANIFEST.json`，确保文件来自同一发布。

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

本轮对 `fee-module`、`proxy-core`、`minerproxy-runtime`、`minerproxy-server` 四个组件执行原生完整库与集成测试，共 125 个测试目标：**1400 通过、0 失败、11 忽略**。使用 test profile、优化级别 1，并保持 debug assertions 和 overflow checks 开启；这是测试构建，不是 release-profile 回归。最终测试输入已经重新核对，没有测试后源码变更。

上述四个组件的全目标 Clippy（`-D warnings`）通过；服务端界面测试 **72 通过、0 失败**。前期重叠专项、历史版本和 D14 原有测试不重复累加。

11 个忽略项包括显式长期运行、万连接容量门禁、专用诊断及子进程夹具，未执行项不计为通过。模拟时钟和模型中的长周期结果不能当作真实运行时长；**本轮没有据此宣称通过真实两小时、六小时或 24 小时矿场稳定性验收，也不代表万连接容量已通过**。

Windows 与 Linux 正式服务端程序已分别在隔离环境实际启动，HTTPS 管理界面及管理员设备 API 检查通过。两平台均读取间隔至少 1 秒的两次真实主机样本，核对产品版本为 **1.0.0**、内存可读，后续 CPU 与网速样本可用；首次尚无差值时保持未测量。测试不连接生产矿池，结束后已停止各自测试进程。

六个软件包已完成外层 SHA-256、包内载荷、程序来源和许可文件检查：三个 R19 包对应本次正式构建，三个 D14 包与上次发布逐字节一致。管理器在离线发布夹具中正确选中 R19 服务端与 D14 本地端 Linux 包，校验、解包及程序版本检查通过；此结果不冒充 GitHub 在线下载实测。源码回归、正式构建、平台启动及软件包检查分别记录，不能相互代替。

## 本次组件来源

三个 R19 服务端包由本版服务端源码重新构建；三个 D14 本地加密端包逐字节复用 R18 / D14 发布的原包，SHA-256 保持不变。本地端 Ubuntu 文件名仍为 `strynium-local_1.0.0+20261101.d14_amd64.deb`。

发布清单分别记录服务端的新源码、构建与验证来源，以及 D14 原包来源。新的 Release 标签不表示本地端重新编译。仪表盘显示正式产品版本 **v1.0.0**；安装包与发布清单中的 R19 / D14 编号用于区分实际构建。
