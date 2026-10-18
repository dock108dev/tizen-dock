# Security and privacy

Tizen Dock performs powerful operations on a TV you control. Use a trusted local
network. Do not expose SDB or the startup status port to the internet.

## Access and trusted inputs

Developer Mode and Samsung SDB provide initial access. Temporary administrator
sessions authenticate commands with fresh HMAC secrets and nonces. The upstream
root tooling is pinned; runtime or capability mismatches remain errors.

Installation checks exact original assembly hashes, backup checksums and generated
file hashes. Hashes detect changed bytes; they do not make an untrusted installer
safe. Apply only builds you produced or reviewed. The CLI intentionally supports
explicit root commands and is not a sandbox against another process running as
the same computer user.

Artwork imports accept plain PNG filenames, reject symlinks and reserved names,
and require 512 × 512 images. Backup and build validation reject redirected
artifact files. Generated startup packages must stay under ignored `.local/`
storage with private permissions. Signing verifies that the distributor
certificate covers the selected TV; the TV validates widget signatures.

## Startup status

The TV helper exposes read-only status on LAN port 8098, protected by a random
256-bit token with constant-time comparison. Host and browser-origin checks limit
access; the installed widget's opaque origin still needs the token. There is no
HTTP command, reboot or installation endpoint. Responses are not cached, and the
CLI observer rejects redirects and bypasses configured proxies.

Status uses HTTP. Someone able to inspect LAN traffic may capture the read-only
token and learn helper/boot activity. It does not authorize administrator commands.
Keep it private and use an isolated trusted network. Rebuild and reinstall the
helper after changing service code; editing local source does not update a TV.

## Private files and recovery

Keep configurations, tokens, signing certificates/passwords, backups, databases,
logs and Samsung-derived binaries out of Git. `.local/` is ignored for this purpose.
Inspect logs before sharing them; they may contain sensitive command output.

Uninstall **Tizen Dock Startup** before rebooting if you want automatic restoration
to stop. Clearing mounts alone leaves the helper able to restore them on a later
boot. See [recovery](docs/backups-and-recovery.md) and
[startup](docs/restart-and-persistence.md). Recovery after a post-mount Home launch
failure and cold-power-loss restoration are not guaranteed on every device.

## Known dependency issue

The locked signing tools use `node-forge 1.4.0`, affected by the HIGH-severity
[GHSA-86w9-cpqp-85rv](https://github.com/advisories/GHSA-86w9-cpqp-85rv) RSA
signature-verification advisory. This tool uses certificate parsing and signing;
that does not establish an application exploit. The dependency check still blocks
the finding. Resolve it through a reviewed upstream fix and lockfile update before
considering the security gate passing. There is no suppression or ignore baseline.

Report vulnerabilities through the repository's private security-reporting
facility when available. Do not publish access details, credentials or raw device
logs in an issue. Ordinary bugs can use redacted diagnostics.
