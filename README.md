# STRYNIUM Miner

STRYNIUM Miner V1.0.0 is proprietary mining proxy and tunnel software for Windows
and Ubuntu. This public repository contains release documentation and metadata,
not the proprietary product source.

## Components

- **STRYNIUM Server** hosts the mining proxy and embedded management Console.
- **STRYNIUM Tunnel** connects an authorized mining network to its configured
  Server using TLS and exact certificate pinning.

Each component is delivered as one executable for its platform. Runtime data
and operating-system prerequisites are separate from the executable.

## Supported platforms

| Platform | Server | Tunnel |
|---|---|---|
| Windows 11 x86_64 | Embedded web Console | Desktop GUI |
| Ubuntu 24.04 x86_64 | Embedded web Console | Headless CLI |

Windows qualification was performed on Windows 11 x64. This release does not
claim separate Windows 10 qualification. Ubuntu binaries require the Ubuntu
24.04 system-library baseline (glibc 2.39); other distributions and architectures
are not qualified by this release.

Windows Tunnel requires an independently installed Microsoft WebView2 Runtime.
Ubuntu Tunnel requires an unlimited locked-memory allowance and an interactive
terminal for secure credential-store unlock. See [INSTALL.md](INSTALL.md).

## Main features

- Single-binary delivery; no customer Rust, Cargo, Node, npm or Docker requirement.
- Embedded Server management Console and LAN HTTPS.
- Remote Tunnel TLS with exact certificate pinning.
- Coin/pool catalog and configurable mining routes.
- Windows Tunnel GUI and Ubuntu headless Tunnel CLI.
- Passphrase-unlocked encrypted credential storage for Ubuntu Tunnel.

A fresh Server is not automatically configured for production mining or remote
Tunnel service. An authorized operator must configure the deployment and issue
the required client bootstrap material. No mining profitability, hashrate,
uptime or universal pool-compatibility guarantee is made.

## Downloads

Use the assets from [GitHub Releases](https://github.com/strynium/strynium-miner/releases).
V1.0.0 publication is pending; do not treat repository documentation alone as an
available binary release.

GitHub's automatically generated **Source code (zip)** and **Source code
(tar.gz)** archives contain only this public documentation repository, not
STRYNIUM proprietary product source code. They are not executable installers.

## Installation, verification and security

- [Installation and first-run guidance](INSTALL.md)
- [SHA-256 verification](VERIFY.md)
- [Security guidance and reporting status](SECURITY.md)
- [Release changes](CHANGELOG.md)

V1 Windows binaries are not Authenticode-signed. Verify hashes before use.
Do not disable Defender, SmartScreen or other security protections.

## License

STRYNIUM Miner V1 is **proprietary freeware, binary-only**. Commercial and
internal business use are allowed under [LICENSE.txt](LICENSE.txt) and
[USE_TERMS.md](USE_TERMS.md). Free availability does not grant redistribution,
resale, bundling or first-party source-code rights. Mandatory-law exceptions
and independent third-party rights remain intact.

## Third-party notices and marks

See [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt), including its Rust
standard-library notice appendix.

Third-party cryptocurrency names and marks are used for identification and
cryptocurrency-related UI context. No partnership, sponsorship or endorsement
by those projects is claimed. This statement does not assert that every logo
has been licensed by its owner.

STRYNIUM is the product owner's original naming. The S mark was generated using
ChatGPT image generation at the product owner's direction and selected/adopted
by the product owner. No registered trademark, OpenAI endorsement, OpenAI
trademark ownership or assignment of trademark rights is claimed.
