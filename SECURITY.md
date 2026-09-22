# Security

## Reporting status

A private security reporting channel has not yet been confirmed for this
repository. A private contact channel will be added when available. No public
email address is designated at this time.

Do not post passwords, bootstrap credentials, passphrases, private keys, runtime
stores, private network details, unredacted logs or sensitive exploit details in
public Issues. Do not assume an Issue or ordinary repository discussion is
private. Wait for a confirmed private reporting channel before sending sensitive
material. No response time or support SLA is promised.

## Safe operation

- Download from the canonical STRYNIUM GitHub Releases page and compare SHA-256
  against its manifest and checksum file. Hashes detect byte differences; an
  unsigned checksum file is not an independent publisher signature.
- Windows V1 executables are not Authenticode-signed. Respect OS and security
  product warnings; do not disable Defender, SmartScreen or antivirus.
- Restrict Console access to authorized operators and trusted management
  networks. Do not expose the management Console directly to the public Internet.
- Change the initial administrator username and password when prompted. Protect
  the runtime data directory; do not reset it as a workaround for failed login.
- Obtain bootstrap material and the bound client UUID from the authorized
  Server operator through an appropriate protected channel.
- Do not put bootstrap secrets or passphrases in command arguments, environment
  variables, shell history, plaintext files, screenshots or support logs.
- Keep TLS identity and certificate pins under controlled administration. Do not
  disable certificate validation or silently replace a mismatched pin.
- On Ubuntu, use the encrypted credential store and interactive hidden unlock.
  A new Tunnel process, including after reboot, requires unlock again. V1 does
  not provide unattended secure unlock on ordinary Linux hosts without TPM/KMS.
- Keep OS prerequisites updated and use appropriate network isolation, backups
  and monitoring. Encrypted storage does not eliminate every operational risk.

This document does not create a telemetry consent, hosted service, guaranteed
security outcome or continuing support obligation.
