# Installation — STRYNIUM Miner V1.0.0

## Before starting

Download the component for your platform from
[GitHub Releases](https://github.com/strynium/strynium-miner/releases), together
with SHA256SUMS.txt and STRYNIUM-V1.0.0-MANIFEST.json. Follow [VERIFY.md](VERIFY.md)
before executing anything. Read [LICENSE.txt](LICENSE.txt), [USE_TERMS.md](USE_TERMS.md)
and [SECURITY.md](SECURITY.md).

Use a fresh installation directory for a first installation. Do not overwrite
an existing installation or reset its runtime data with these examples. Runtime
configuration, authentication and TLS identities are stored outside the binary
directory and must be preserved across restarts and upgrades.

Each component has one executable. Customers do not need Rust, Cargo, Node,
npm, Docker, source compilation, or an external frontend server.

## Windows 11 x86_64

Windows 11 x64 is the qualified Windows platform. Windows 10 is not separately
qualified here. Windows Tunnel requires the independently installed Microsoft
WebView2 Runtime; this release neither bundles it nor silently installs it.
Obtain it through Microsoft's official
[WebView2 distribution page](https://developer.microsoft.com/en-us/microsoft-edge/webview2/).

### Server

In a fresh directory containing the verified download:

~~~powershell
Copy-Item -LiteralPath ".\strynium-server-v1.0.0-windows-x86_64.exe" -Destination ".\strynium-server.exe"
Get-FileHash -LiteralPath ".\strynium-server.exe" -Algorithm SHA256
.\strynium-server.exe
~~~

The copied file must still match the Windows Server checksum. The standard
filename is required for the Server's no-argument customer startup path;
renaming/copying does not change its bytes. Do not launch the versioned download
under an arbitrary name and assume identical no-argument behavior.

The Server opens its Console in the system browser. Use the HTTPS endpoint
selected by the running Server; do not guess a LAN IP/port or send credentials
to an HTTP fallback. Check the endpoint/certificate through your authorized
operator before trusting it. The default data directory is
`%PROGRAMDATA%\STRYNIUM`. If access permissions prevent startup, have the
administrator provision the correct permissions; do not weaken them broadly.

At first login, use the initial bootstrap credential supplied through your
authorized setup channel, then complete the mandatory administrator username
and password changes. This public guide deliberately does not disclose the
initial password. If you have not received the credential, obtain it from the
authorized operator rather than guessing or deleting runtime state. The old
initial credential is not the normal login after account setup.

A fresh installation may show IDLE / NOT_CONFIGURED. Configure your authorized
pools/routes and deployment before expecting mining or remote Tunnel traffic.

### Tunnel

In a separate fresh directory:

~~~powershell
Copy-Item -LiteralPath ".\strynium-tunnel-v1.0.0-windows-x86_64.exe" -Destination ".\strynium-tunnel.exe"
Get-FileHash -LiteralPath ".\strynium-tunnel.exe" -Algorithm SHA256
.\strynium-tunnel.exe
~~~

Use the GUI setup workflow with bootstrap material issued by your authorized
Server operator. Review the configured mining ports and connection state before
pointing miners at the local Tunnel. Keep its existing per-user runtime state;
the default configuration location is
`%LOCALAPPDATA%\STRYNIUM\STRYNIUM Tunnel`.

### Unsigned Windows V1

The two Windows executables are not Authenticode-signed. Windows or your security
software may warn about an unrecognized publisher or download reputation.
Independently verify the release origin and hashes; if policy blocks execution,
consult your administrator. Do not disable Defender, SmartScreen or antivirus.

## Ubuntu 24.04 x86_64 — Server

Use Ubuntu 24.04 x86_64 with its system-library baseline, including glibc 2.39.
A controlled installation directory such as `/opt/strynium/server` is suitable;
have the administrator grant the intended runtime identity access to the Server
data directory `/var/lib/strynium`. Keep binary and data directories separate.

From a fresh installation directory containing the verified download:

~~~bash
cp -n strynium-server-v1.0.0-ubuntu24.04-x86_64 strynium-server
sha256sum strynium-server
chmod +x strynium-server
./strynium-server
~~~

Before continuing, verify the copied checksum equals the published Server value.
The standard filename is required for no-argument startup. Use the Console HTTPS
URL printed when ready. From another authorized management host, use only the
intended management-network endpoint and verify its identity. Complete the same
initial-account change flow described above; no initial password is published here.

The default launch provides Console management, not a ready-made remote
production deployment. Remote Tunnel provisioning requires an operator-configured
deployment authority, appropriate DNS/TLS identities, pins and network policy.
Do not expose management services or invent a bootstrap address as a shortcut.

## Ubuntu 24.04 x86_64 — Tunnel

Ubuntu Tunnel is a headless CLI, not the Windows GUI. Use a dedicated non-root
operator identity with a real home directory and a controlling terminal.
The administrator must grant that identity an **unlimited locked-memory
allowance**; do not relax the product's memory/core protections to work around
an error. For systemd-managed sessions the corresponding resource setting is
`LimitMEMLOCK=infinity`; that alone does not supply an interactive unlock terminal.

From a fresh directory containing the verified download:

~~~bash
cp -n strynium-tunnel-v1.0.0-ubuntu24.04-x86_64 strynium-tunnel
sha256sum strynium-tunnel
chmod +x strynium-tunnel
ulimit -l
~~~

Check the copied checksum and confirm the locked-memory limit reports
`unlimited`. If not, stop and have the administrator provision the intended
session's resource limits. Do not run as root merely to bypass setup.

### First bootstrap import

Obtain a valid bootstrap record and its **server-bound client UUID** from the
Server operator. The UUID is not a secret but must match exactly; do not generate
a replacement UUID. Existing installations retain their existing identity.

Linux import accepts bootstrap data through a pipe, not an echoing terminal or
plaintext file. In an ordinary interactive Ubuntu terminal, this example uses
the OS password prompt to pass the bootstrap directly through a pipe:

~~~bash
set +x
set -o pipefail
env -u CREDENTIALS_DIRECTORY systemd-ask-password --echo=no --timeout=0 'STRYNIUM bootstrap:' |
  ./strynium-tunnel import-bootstrap --stdin
~~~

Run the complete pipeline, not the password-prompt command alone: its stdout
contains the secret and is intended only for Tunnel stdin. Do not add `tee`,
output redirection, terminal recording or shell tracing. No secret value belongs
in the command itself. This uses the OS tool's hidden TTY input without enabling
its optional keyring cache; see the
[systemd password-prompt documentation](https://www.freedesktop.org/software/systemd/man/systemd-ask-password.html).

The Tunnel then asks for the server-bound UUID and hidden creation/confirmation
of the encrypted-store passphrase. Follow the prompts and protect that passphrase.
Trusted configuration initialization requires a successful authenticated pull;
if it fails, do not fabricate a configuration file or delete encrypted pending
state. Correct the deployment/network issue and retry through the supported flow.

Default Tunnel configuration is under
`$XDG_CONFIG_HOME/strynium/strynium-tunnel`, or
`$HOME/.config/strynium/strynium-tunnel` when XDG_CONFIG_HOME is unset.
Encrypted storage is passphrase-based, not merely a plaintext file protected
by mode 0600.

### Normal run and restart

~~~bash
./strynium-tunnel run
~~~

Enter the unlock passphrase at the hidden terminal prompt. Use Ctrl+C for
orderly shutdown. Every new Tunnel process, including after a reboot, requires
unlock again. A wrong passphrase fails closed; do not reset the store as a remedy.

**V1 does not provide unattended secure unlock on ordinary Linux hosts without
TPM/KMS.** No TPM/KMS integration or automatic boot-time unlock is claimed.
Do not persist a passphrase in a service environment, command line or plaintext
sidecar to imitate unattended unlock.
