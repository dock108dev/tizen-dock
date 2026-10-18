# Tizen Dock

Experimental, reversible **Tizen OS customizations for Samsung TVs**: a compact, centered dock over the current picture, fewer Samsung recommendation panels, and control over unwanted apps.

The current build is **v4**, with rounded focus, gentler zoom, optional private
512-pixel artwork, and a device-authorized startup helper. It adapts Samsung's
Home renderer and remains experimental. See [compatibility](docs/compatibility.md)
for observed devices, exact-input requirements and validation limits.

## Capabilities and limits

- Hides upper Home cards, recommendation containers, and the sponsored launcher tile.
- Builds a bottom-centered dock and reduces selected menu animations and preview loading.
- Disables selected apps with saved original state; prepares shortcut removal separately.
- Provides temporary root, private backups and logs, and overlay restore commands.

Reversible bind mounts preserve original system files. The TV-side startup helper
uses the same build manifest; cold-power-loss recovery still needs a controlled
test on each installation. See [startup and persistence](docs/restart-and-persistence.md).

Movie Hub/channel audio prevention, continuous playback across every app, full remote navigation, and performance improvements remain unverified. A firmware label alone does not establish compatibility; builds check exact source hashes.

## Requirements and quickstart

Use the [compatible device inputs](docs/compatibility.md), a trusted local network, Python 3.12+, .NET SDK 10.0.402, OpenSSL, and Samsung SDB from [Tizen Studio](https://developer.tizen.org/development/tizen-studio/download). Node 22 or 24 is required for startup packaging. macOS is the development host; other hosts are unqualified.

From the extracted project directory:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
cp config.example.json config.json
```

Set the TV address and SDB path in `config.json`. Enable TV Developer Mode with the computer's LAN address, following [setup](docs/setup.md), then:

```sh
python scripts/bootstrap.py
tizen-dock doctor
tizen-dock connect
tizen-dock status
```

Before changing the TV, create a [private backup](docs/backups-and-recovery.md), then follow [customization](docs/customization.md). There is no automatic bulk-debloat preset, password-based root login, or firmware flashing command.

## Local checks

Install the locked test tools as described in [testing](docs/CI.md). Quick local
checks are:

```sh
python -m pytest
node tests/test_startup.cjs
```

The testing guide lists the full Python, .NET, startup and security suites.

See [development](docs/development.md) for patcher builds, [architecture](docs/architecture.md) for implementation details, and [troubleshooting](docs/troubleshooting.md) for recovery. Source checks do not qualify device behavior.

## Privacy and license

Keep `config.json` and `.local/` private. They can contain credentials, account data, backups, device identifiers, logs, and Samsung-derived binaries. The public tree contains source, profiles, examples, and tests; it ships no Samsung firmware, app artwork, or signing material.

Original project code is [MIT licensed](LICENSE). Temporary root builds on pinned [samsung-tv-root](https://github.com/chris-ritsen/samsung-tv-root) research; see [NOTICE](NOTICE), [security](SECURITY.md), and [contributing](CONTRIBUTING.md). This project is independent of Samsung, Apple, and the named app providers.
