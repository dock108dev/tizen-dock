# Restart and startup persistence

## Current installation

The current build is v4. Its startup helper restores the same manifest-verified
renderer and assets after boot, using a short-lived authenticated root session
on the TV. It then relaunches Home and closes that session. It exposes only a
token-protected read-only status endpoint, never a LAN command endpoint.

System binaries remain intact. Standby may preserve the mounts; a full reboot
clears them until the installed helper restores them. App flags and shortcut
cache changes remain independent.

## Recorded installation and verification

The 2026-10-18 basement installation used the v4 renderer with private 512-pixel
artwork and startup revision `dock-v4-startup-1`. The recorded status was
`active / already-present`, and the owner reported the v4 dock visible. These
observations establish operation in that boot only. The last observed boot ID
was unchanged; the owner deferred the restart and cold-power-loss test.

The repository now contains hardened startup revision `dock-v4-startup-2`.
The installation record says it has not been signed or deployed. Source checks
therefore do not establish that the installed helper has the newer access
controls. Prepare a fresh device-authorized package when maintenance resumes,
then use the verification procedure below. No device was contacted to refresh
this record during the documentation pass.

## Prepare one private package per TV

Use that TV's selected configuration, verified pristine backup, v4 build, pinned
bootstrap payloads and Samsung-authorized signing certificates. The distributor
certificate must include the selected TV's DUID. Retain signing material privately;
never reuse a signed package just because another TV has the same model.

Supply `author.p12`, `distributor.p12`, `author.pw` and `device-profile.xml` in
`.local/tv/certs/`. Both PKCS#12 files must use the password in `author.pw`.
The certificate files must be issued for the intended TV.

Read its DUID using your configured SDB executable and serial, redirecting the
result to `.local/tv/device-id` rather than printing it in shared logs. The SDB
command is `sdb -s TV_IP:26101 shell 0 getduid`; replace the executable and TV IP
with your actual settings. Create the private directory first and restrict the
file to its owner.

Install the repository's locked signing tools with
`npm ci --ignore-scripts --no-audit --no-fund`. Preparation does not download
certificates. The known dependency issue is described in [security](../SECURITY.md).
The commands below use `config.json`; add `--config PATH` consistently when using
another TV configuration.

```sh
python scripts/prepare-startup.py \
  --build .local/build/dock \
  --backup .local/backups/YOUR_BACKUP \
  --payloads .local/payloads \
  --certificates .local/tv/certs \
  --device-id .local/tv/device-id \
  --output .local/tv/startup

tizen-dock install-startup \
  --package .local/tv/startup

tizen-dock startup-status \
  --package .local/tv/startup
```

Prepare refuses an existing output directory. It generates one restoration script
from the current build's file hashes and the backup's managed/native originals,
then signs a widget only if its certificate authorizes the selected device.
Installation rechecks package hashes, signatures' presence and the connected TV's
identity before uploading. The TV validates the signatures. Preparation restricts generated packages to ignored `.local/` storage and uses private file permissions. Keep the status token,
package, certificates and installer output private.

Apply the v4 build before installing its helper. For an existing v3 installation,
restore its mounts, verify original hashes, and archive the unused old staging
directory before applying the new build. Never overwrite files still mapped by Home.

## Verify persistence

A successful helper launch in the current boot proves only current-boot operation.
Record `bootId`, fully restart, and observe status without sending apply commands.
Require a changed `bootId`, `state: active`, `overlays: reapplied`, matching live
hashes, and a visible functioning dock. Repeat after unplugging for 30 seconds to
qualify cold-power-loss recovery. Installation alone is not that qualification.

Startup timing depends on TV and network readiness. The helper has a bounded
startup deadline; installation alone does not guarantee cold-power-loss recovery.

## Developer Mode and recovery

The installed autonomous helper uses Host PC IP `127.0.0.1`. The installer saves
the previous setting, sets this loopback host and disconnects the Mac bridge so
the TV-local client can connect. The TV-local client requires this setting;
it does not by itself prove persistence through a new boot. Normal Mac SDB access
is unavailable while the TV trusts loopback.

For maintenance, restore the computer's current LAN address in Developer Mode,
save and restart. After maintenance, reinstall the helper through the current
installer to restore its local host setting and release the Mac connection.

To stop automatic restoration, uninstall **Tizen Dock Startup** from TV Apps, then
fully reboot. `restore-menu` alone clears mounts but leaves the installed helper
able to restore them on a subsequent boot. Preserve the original backup and prior
build artifacts for recovery.
