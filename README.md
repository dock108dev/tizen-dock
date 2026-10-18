# Tizen Dock

Experimental, reversible **Tizen OS customizations for Samsung TVs**: a compact, centered dock over the current picture, fewer Samsung recommendation panels, and control over unwanted apps.

**Keep expectations low:** this was heavily vibe coded and spun up in about an hour. It looks good and stays simple, but testing is limited and behavior is unfinished. It adapts Samsung's Home renderer; it does not replace Tizen with iOS or tvOS.

Development has used one **Samsung UN65TU7000FXZA**, reported firmware **2301**, with Tizen 6.0 and ARMv7 observed. The latest device customization has rounded focus, gentler zoom, and higher-resolution icons whose full logos were confirmed to fit. The public build still produces v3; the optional v4 artwork patcher has a separate exact-input gate and is not integrated into that build.

## Capabilities and limits

- Hides upper Home cards, recommendation containers, and the sponsored launcher tile.
- Builds a bottom-centered dock and reduces selected menu animations and preview loading.
- Disables selected apps with saved original state; prepares shortcut removal separately.
- Provides temporary root, private backups and logs, and overlay restore commands.

The default tools use temporary bind mounts and preserve the original system files. A restart can clear those mounts. An experimental TV-side helper restored them on a later boot, about **10 seconds after its service started**. That is not a power-on timing guarantee: an unplug test failed, a controlled repeat is pending, and Developer Mode host-IP testing is incomplete. The helper is not included in the public installer. See [restart and persistence](docs/restart-and-persistence.md).

Movie Hub/channel audio prevention, continuous playback across every app, full remote navigation, and performance improvements remain unverified. A firmware label alone does not establish compatibility; builds check exact source hashes.

## Requirements and quickstart

Use the [compatible device inputs](docs/compatibility.md), a trusted local network, Python 3.12+, .NET SDK 10.0.402, OpenSSL, and Samsung SDB from [Tizen Studio](https://developer.tizen.org/development/tizen-studio/download). macOS is the development host; other hosts are unqualified.

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

See the [CI contract](docs/CI.md) for locked tool installation, the full check map, reporting and local commands. The required offline suites are:

```sh
python ci/run.py python
python ci/run.py patchers
python ci/run.py security
```

See [development](docs/development.md) for patcher builds, [architecture](docs/architecture.md) for implementation details, and [troubleshooting](docs/troubleshooting.md) for recovery. Source checks do not qualify device behavior.

## Privacy and license

Keep `config.json` and `.local/` private. They can contain credentials, account data, backups, device identifiers, logs, and Samsung-derived binaries. The public tree contains source, profiles, examples, and tests; it ships no Samsung firmware, app artwork, or signing material.

Original project code is [MIT licensed](LICENSE). Temporary root builds on pinned [samsung-tv-root](https://github.com/chris-ritsen/samsung-tv-root) research; see [NOTICE](NOTICE), [security](SECURITY.md), and [contributing](CONTRIBUTING.md). This project is independent of Samsung, Apple, and the named app providers.
