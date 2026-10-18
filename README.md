# Tizen Dock

Experimental, reversible **Tizen OS customizations for Samsung TVs**: a compact menu over your current picture, fewer recommendation panels, and explicit control over unwanted apps.

Tizen Dock adapts Samsung's existing Home renderer rather than installing a replacement operating system. It includes source patchers, local tools, exact-input compatibility checks, backup and restore workflows, and the findings behind the current implementation.

**Current status:** tested during development on one **Samsung UN65TU7000FXZA**, with firmware reported as **2301**, Tizen 6.0 and ARMv7 observed. Temporary root access, app disabling, shortcut cleanup, and overlay loading worked on that device. The latest centered dock revision still needs visual and navigation confirmation. This is a research toolkit, not a finished theme installer.

## What it changes

- Hides the upper Home account, notification, privacy, and promotional cards.
- Removes the recommendation container and its empty navigation paths.
- Suppresses the sponsored launcher tile while keeping its shared provider installed.
- Builds a shorter dock anchored at the bottom center, with larger app shortcuts and rounded image masks applied to the app shortcut renderer.
- Reduces selected menu animation delays and disables preview loading in the customized renderer.
- Disables explicitly selected apps using native package controls, with a saved original state for each change.
- Prepares Home shortcut edits separately from package changes.

The renderer runs through temporary bind mounts. Its original system files remain intact. A full power cycle removes those mounts. App disable flags and Home cache edits can persist and have separate restore procedures.

## Start here

1. Read [compatibility and current status](docs/compatibility.md).
2. Follow [setup and device access](docs/setup.md).
3. Create a [verified private backup](docs/backups-and-recovery.md).
4. Follow the [customization workflow](docs/customization.md).

[Architecture](docs/architecture.md) explains the patch pipeline and Tizen-specific differences. [Troubleshooting](docs/troubleshooting.md) covers connection failures and recovery. [Development](docs/development.md) explains local checks and how to add a separately qualified profile.

## Important boundaries

Samsung Tizen is not Android: Android package commands and ADB user-0 removal do not apply. Standard SDB access also does not automatically provide an unrestricted shell. This project uses a separately attributed public root research route and a narrowly scoped TU7000 runtime adaptation.

The toolkit does not flash firmware, replace the bootloader, install a persistent root service, or distribute Samsung's binaries. It does not yet establish that Movie Hub playback always stops, that every streaming app keeps playing behind Home, or that the current dock behaves correctly across every remote-control path. Disabling TV Plus alone did not establish that the native channel player had stopped.

A reported firmware version alone is insufficient. The build refuses source assemblies whose hashes differ from the documented profile. Review the generated application script before running it on your own TV.

## Project layout

| Path | Contents |
| --- | --- |
| `src/tizen_dock/` | Connection, temporary root, backup, app-state, and overlay commands |
| `patchers/` | Source-only assembly transformations and intermediate dock revisions |
| `profiles/` | Exact original hashes and device paths for the qualified input set |
| `scripts/` | Dependency setup, private input extraction, asset generation, and offline Home-cache editing |
| `docs/` | Setup, operation, recovery, limitations, and development notes |
| `.local/` | Private dependencies, binaries, backups, builds, logs, and device session records; excluded from publication |

## Attribution and license

Project code is available under the [MIT license](LICENSE). Temporary root access builds on [samsung-tv-root](https://github.com/chris-ritsen/samsung-tv-root), pinned to a documented source revision; see [NOTICE](NOTICE) and [security notes](SECURITY.md). Samsung, Tizen, Apple TV, and app names belong to their respective owners. This project is independent of those companies.
