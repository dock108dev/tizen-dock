# Customization workflow

Complete [setup](setup.md), verify the exact device, and take a [backup](backups-and-recovery.md) first. The commands below are deliberate operations on the configured TV; the tools do not select a TV automatically from a broad scan.

## Build the menu privately

```sh
tizen-dock backup
python scripts/extract-originals.py --backup .local/backups/YOUR_BACKUP --output .local/originals
python scripts/build-overlays.py --originals .local/originals --output .local/build/dock
```

Replace `YOUR_BACKUP` with the printed backup directory. Extraction selects only the documented build inputs and verifies the archive checksum. Do not publish `.local/originals` or the outputs: they contain Samsung-derived assemblies.

Review `.local/build/dock/apply.sh` and `manifest.json`. The build is incremental: Home/feed/ad patches, the initial dock transformation, and two successive renderer revisions. Only the final renderer is deployed. The current design uses a 25-unit-high panel, a row width clamped to `min(210, window width - 24)`, a background 12 units wider, BottomCenter anchoring, and 17-unit normal app shortcuts. Focus enlargement is 1.18 for the app shortcut renderer. These are Tizen layout units, not screen pixels.

```sh
tizen-dock apply --build .local/build/dock --backup .local/backups/YOUR_BACKUP
```

Application verifies the backup, profile, and generated file hashes, uploads private build files, checks the TV's original assembly hashes again, and applies temporary overlays in the main mount namespace. It refuses an existing project staging directory or already-modified source inputs. A partial mount failure removes mounts created by that application attempt. Home is relaunched through the SDK context; a failed launch triggers an attempt to remove the overlays and relaunch the original renderer.

After Home loads, check left/right focus, the last app, Back, Settings, Inputs, app launch, video continuity, audio continuity, and whether any blank recommendation space remains. A process staying alive is not a visual check. Keep the current version experimental until these work on the device.

## Disable or restore a specific app

First inspect your own inventory privately:

```sh
tizen-dock root --command "sqlite3 -readonly /opt/dbspace/.pkgmgr_parser.db 'SELECT app_id, app_disable FROM package_app_info;'"
```

Choose an exact app ID, then:

```sh
tizen-dock disable-app YOUR_EXACT_APP_ID --backup .local/backups/YOUR_BACKUP
tizen-dock enable-app YOUR_EXACT_APP_ID --backup .local/backups/YOUR_BACKUP
```

Each command reads the authentic original state, records intent before changing it under `.local/changes`, applies the native package operation, and verifies the resulting flag. On interruption, read both that record and current TV state before deciding what to restore. `enable-app` is not always the correct restore if the app was already disabled before this project touched it.

The native operations are `pkgcmd -D -t app -n APP_ID --uid 5001` and `pkgcmd -A -t app -n APP_ID --uid 5001`. They disable/enable rather than uninstall. App IDs and associated services vary by installation. Do not disable every service sharing a vendor name: AirPlay and ad infrastructure can be shared with necessary system features. There is no automatic bulk debloat preset.

## Remove app shortcuts from Home

Disabling a package and removing a cached Home shortcut are separate changes. On the development TV, the Home row lived in `.appLayerCache.1/.2`; the removal map lived in `.listofremovedbyuser.1/.2` under:

`/opt/usr/home/owner/apps_rw/com.samsung.tv.csfs/data`

Extract that directory from your verified private snapshot into a private working directory. Prepare a removal by exact component ID:

```sh
python scripts/edit-home-cache.py --input .local/home-data --output .local/home-edit --remove 'd/webapp@YOUR_STORE_ID'
```

Repeat `--remove` for multiple entries. Review the generated files and `.local/home-edit/apply.sh`, then:

```sh
tizen-dock root --script .local/home-edit/apply.sh
tizen-dock restart-home
```

The helper validates cache framing, increments generations, updates both existing copies, and checks original file hashes before writing. A stale snapshot is rejected rather than overwriting newer Home changes. It briefly pauses Home while writing and resumes it on script exit. Keep the verified original files for restoration. An interrupted write can still require manual restoration from that backup.

An empty `.homeCache` alone was insufficient: Samsung's code fell back to default cards. The renderer overlays handle that behavior. No generic cache format is promised for other builds.

## Stop or undo

```sh
tizen-dock restore-menu
```

This attempts to unmount the four component overlays, then restarts Home. It does not restore app disable flags or Home cache files. Verify the SDK-visible hashes against the profile afterward. A full power cycle clears the temporary mounts, but an installed startup helper may reapply them. Uninstall that helper first if you want automatic restoration to stop; see [restart and persistence](restart-and-persistence.md). See [recovery](backups-and-recovery.md) for persistent changes and retry staging cleanup.

## Optional artwork and focus styling

The separate `patchers/dock-v4` source isolates app backplates, replaces the native square focus background with a rounded outline, and reduces focus zoom to 1.08. With matching 512-pixel artwork and mask, the owner confirmed rounded focus and full logos fitting inside the tiles. App launch, playback, and every remote path remain incompletely tested.

This patcher accepts only the exact device-derived v3 renderer hash checked in its source. The default build embeds different resource paths and is not automatically accepted by this additional gate. Do not bypass it. There is no integrated v4 apply command or public startup-helper installer.

For development with an already-qualified v3 input:

```sh
python patchers/dock-v4/make-assets.py .local/artwork
dotnet run --project patchers/dock-v4/Patcher.csproj -- \
  .local/qualified/ImplNUI.v3.dll .local/artwork/ImplNUI.dll \
  .local/originals /home/owner/share/tizen-dock/menu-overlay \
  examples/artwork-map.json
```

The arguments are input renderer, output renderer, private reference directory, absolute TV asset directory, and optional artwork map. The generated directory is not a normal `tizen-dock apply` build: it has no deployment manifest. Loading it requires separately reviewed staging, hash checks, bind mounts, and rollback instructions.

The asset generator creates only the original rounded outline and mask. Supply your own square 512 × 512 PNG app cards named by [the example map](../examples/artwork-map.json). Map keys must exactly match displayed app titles; unmapped titles keep their existing artwork. The patcher resolves values as filenames under the TV asset directory. Stage all referenced files alongside the renderer before loading it.

Use the 512-pixel mask with 512-pixel replacement artwork. A smaller mask cropped the source before display scaling, causing only the middle letters of logos to show. Keep masks, artwork, and the patched renderer together as one compatible set. The rounded focus outline is a separate image from the icon mask.

The artwork map is optional. Without it, existing app artwork and its existing mask are retained; only focus styling changes. App logos and Samsung-derived binaries are not shipped in this repository. Some private device artwork used vector marks from [Simple Icons](https://github.com/simple-icons/simple-icons) and locally rendered text.
