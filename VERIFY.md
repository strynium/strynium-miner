# Verify your download

Download SHA256SUMS.txt and STRYNIUM-V1.0.0-MANIFEST.json with the chosen binary
from [GitHub Releases](https://github.com/strynium/strynium-miner/releases).

Compare the entire SHA-256 value, not a shortened prefix. Stop if a filename,
size or checksum differs. The manifest's sizes are bytes. These checks detect
changed bytes; they do not independently authenticate an attacker-controlled
download site. Use the canonical repository over HTTPS and respect OS policies.

## Windows PowerShell

~~~powershell
Get-FileHash -LiteralPath ".\strynium-server-v1.0.0-windows-x86_64.exe" -Algorithm SHA256
Get-FileHash -LiteralPath ".\strynium-tunnel-v1.0.0-windows-x86_64.exe" -Algorithm SHA256
~~~

Compare each result with the same filename in SHA256SUMS.txt and the manifest.
Case of hexadecimal letters does not change the hash value. Windows V1
executables are not Authenticode-signed; the checksum is not a code signature.

## Ubuntu

~~~bash
sha256sum strynium-server-v1.0.0-ubuntu24.04-x86_64
sha256sum strynium-tunnel-v1.0.0-ubuntu24.04-x86_64
~~~

If all four listed binaries are in the same directory, this verifies every
checksum entry:

~~~bash
sha256sum --check SHA256SUMS.txt
~~~

When only one platform's files have been downloaded, use the individual commands
and compare their complete values; missing-file errors for the other platform
are not successful verification.

## Installed filenames

The release filenames include version/platform information. Installation copies
them to the standard names described in [INSTALL.md](INSTALL.md). Recompute
SHA-256 after copying; changing a filename or adding executable permission does
not change file contents. Never strip, patch or re-sign a download and then
expect the original checksum to match.

GitHub source archives contain this documentation repository, not proprietary
product source or substitute executable downloads.
