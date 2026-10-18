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

## Signing dependency security fix

There is no published npm fix for
[GHSA-86w9-cpqp-85rv](https://github.com/advisories/GHSA-86w9-cpqp-85rv).
The signing tools temporarily pin node-forge to commit
`ceba34402e329f0365134f23fe19898756527d65` from
[upstream PR 1152](https://github.com/digitalbazaar/forge/pull/1152).
This is an unmerged proposed fix, not an official release. The source change
rejects unconsumed children in the nested DigestAlgorithm sequence. Relative to
1.4.0, only rsa.js, its upstream tests, package version and changelog change.

The lockfile records the source archive integrity; the npm override forces tizen
onto the same patched dependency. Startup CI checks both dependency paths resolve
to that copy and exercises valid and malformed RSA encodings, including extra
nested elements with and without NULL parameters. Package signatures are also
verified independently with Node crypto. Replace the commit pin and override with
a reviewed official release when available. No vulnerability suppression is used.

Report vulnerabilities through the repository's private security-reporting
facility when available. Do not publish access details, credentials or raw device
logs in an issue. Ordinary bugs can use redacted diagnostics.
