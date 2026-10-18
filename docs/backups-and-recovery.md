# Backups, logs, and recovery

## Before making changes

Run `tizen-dock backup`. A unique directory under `.local/backups/` receives:

- `snapshot.tar.gz`: the current four renderer assemblies and native-image counterparts, needed framework references, Home application data, and consistent SQLite snapshots of both package registries.
- `manifest.json`: archive size, SHA-256, model, profile digest, and scope.

The Home process is briefly paused while its cache files are archived, then resumed by an exit trap. Each database is copied through SQLite's backup interface; the two database snapshots are sequential, not one cross-database transaction. Transfers are chunked below the root agent's output limit. The local archive's size and digest must match before the temporary TV copy is removed.

This is an application-level snapshot, **not a full firmware image or guaranteed unbrick image**. It captures the currently mounted view. Take it before overlays: a snapshot taken while a customized assembly is mounted contains that customized view and cannot satisfy the pristine-source build checks. Keep an additional offline copy of the verified archive and manifest.

`extract-originals.py` selectively extracts the private build inputs. For Home-cache work, extract only `opt/usr/home/owner/apps_rw/com.samsung.tv.csfs/data` into a private directory, preserving a separate untouched copy. For example, from the project root:

```sh
mkdir -p .local/extracted
tar -xzf .local/backups/YOUR_BACKUP/snapshot.tar.gz -C .local/extracted opt/usr/home/owner/apps_rw/com.samsung.tv.csfs/data
```

Pass that extracted data directory as `--input` to the cache helper. Do not place extracted files in a public directory.

## What remains private

Backups and Home caches can include account identifiers, login state, app tokens, viewing data, and device configuration. Root records can include host addresses and command output. Original/patched assemblies are Samsung-derived material. These belong in `.local/`, which is excluded from publication. Local directories and records created by the CLI use restrictive permissions; separately copied files need the same care.

`config.json` contains your actual device and connection settings. `.local/upstream` contains downloaded dependency source. `.local/payloads`, `.local/patcher-tools`, `.local/build`, and `.local/originals` contain generated or proprietary material. None belongs in a public issue attachment.

## Logs and change records

Root operations create timestamped JSON records in `.local/logs`. App mutations additionally write `.local/changes` before the mutation and mark a record complete only after verification. Backup and build manifests are separate. The tool prints paths to these local records.

An incomplete record is evidence of an interrupted operation, not proof that no change happened. Query the current app flag or mounted assembly hash, then reconcile it with the saved before state. SDK commands are not all automatically archived; retain useful outputs privately. Never post complete raw logs, archives, configuration, or databases without inspecting them for private data.

## Restore menu overlays

`restore-menu` attempts lazy unmount of each managed and native-image path and relaunches Home through the SDK context. It reports launch output, but does not independently establish that all unmounts succeeded. Check the four SDK-visible source hashes against `profiles/tu7000-2301.json`. A full unplug/reconnect clears volatile mounts if control is lost.

The TV staging directory `/home/owner/share/tizen-dock/menu-overlay` remains after restore. Once the original hashes are visible and no mounts use that staging directory, archive or remove this project's directory before a fresh application attempt. The installer intentionally refuses an existing staging directory. Never overwrite a file still mapped by Home; stage a new revision and restart it instead.

## Restore persistent changes

- **App flags:** use the authentic `.local/changes` record's `before` field. Run `enable-app` only when the previous state was enabled; otherwise leave/reapply the disabled state. Dedicated companion services need their own recorded restoration.
- **Home shortcuts:** restore the original `.appLayerCache` and `.listofremovedbyuser` copies you changed. If earlier manual changes touched `.homeCache` or `.ContentsBrowserCache`, restore those exact backed-up files too. Pause Home, preserve current copies, copy original bytes while preserving the TV files' ownership/security metadata, resume Home, then use `restart-home`.
- **Registry databases:** retain the consistent snapshots as evidence/recovery inputs. Do not replace live registry databases wholesale while package services are running. Native package controls are the supported per-app restore path here; complete database recovery has not been qualified.

A power cycle clears temporary overlays but does not necessarily undo disabled apps, removed shortcuts, account changes, or anything else a custom root command changed. Firmware updates may replace renderer inputs or reset app state; remove trials first and requalify exact hashes afterward. Do not restore old Samsung binaries over a newer firmware installation.
