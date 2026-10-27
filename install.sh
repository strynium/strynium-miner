#!/usr/bin/env bash
set -eu
cat >&2 <<'NOTICE'
STRYNIUM: the previous v1.0.0 installer is retired.
The new unified installation/maintenance menu is not yet available.
Use the current R14 / D11 packages and verified manual installation steps:
https://github.com/strynium/strynium-miner/blob/main/INSTALL.md
https://github.com/strynium/strynium-miner/releases/latest
No system configuration or package has been changed.
NOTICE
exit 2
