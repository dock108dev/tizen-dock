# Architecture and Tizen OS customization

## Access layers

1. Samsung Developer Mode permits the configured host to reach SDB.
2. The pinned public research adapter obtains an SDK command foothold and uses the SDK archive-launcher route for temporary root.
3. Root commands run through an authenticated, short-lived session. Its private launcher namespace and restoration checks belong to that adapter.
4. UI overlays must be bound through `nsenter -t 1 -m`, because a mount visible only inside the temporary root namespace does not change the running system menu.
5. Home restarts through SDK `app_launcher`, not through the temporary root context. The latter failed on the development TV because its namespace and security context differed.

This project does not expose a password-based SSH login and does not add a background root controller.

## Menu components

| Assembly | Customization |
| --- | --- |
| CompHome | Returns a successful empty Home component list, preventing the default-card fallback |
| CompTerra | Returns an empty recommendation list, keeps the container invisible, and skips feed initialization and relevant event fetch callbacks |
| CompAdvertise | Hides the sponsored launcher element; keeps its provider installed |
| ImplNUI | Reduces the menu region, removes empty content/preview focus paths and preview loading, adjusts selected transition constants, and reshapes the launcher |

Both `.dll` and `.ni.dll` paths are mounted to the modified managed assembly so the runtime does not keep selecting the old native image. The development TV accepted managed fallback/JIT loading. Source files on the system partition are preserved.

## Patch lineage

`patchers/layout` and `patchers/terra` make isolated PE method-body edits with metadata tokens taken from the actual input. `dock-v1` establishes the initial feed-free renderer and shorter transitions. `dock-v2` uses Cecil with the TV's private reference assemblies to rewrite geometry and image styling. `dock-v3` corrects the actual app-shortcut path and centers the backdrop itself.

The early mask targeted `ImageTitleLauncherView`, but WebAppLauncher shortcuts fall back to `ContentItemView` through FluxLauncherAppsBridge. That explains why the earlier live trial still had square app icons. The current mask is applied to `ContentItemView.mainImage`, backed by ImageBox's AlphaMaskUrl property. The mask is generated from source; original app art is not redistributed.

The panel uses bottom-center parent and pivot anchors, a fixed background width, and a clamped inner row. It retains the original app-launching and remote infrastructure. It is an Apple TV-inspired visual direction, not Apple's interface or software.

The source projects keep the historical transformations explicit so the current build can be reproduced from original inputs. Intermediate UI revisions are not offered as validated user-facing themes. A future cleanup can consolidate them after the current live behavior is confirmed.

## Independent state

Native `app_disable` flags, Home cached shortcut IDs, and renderer visibility are separate mechanisms. Changing one does not establish that the others changed. Likewise, an invisible preview surface is not proof that a separate channel player has stopped decoding or producing sound.

The observed app-ID lists and full databases remain private. The public project has no default list of apps to delete and never assumes that all vendor services are disposable.

## Root research adaptation

The upstream source revision is pinned in `scripts/bootstrap.py`. Its runtime enumeration normally calls `dotnet --list-runtimes`. Samsung's TU7000 launcher rejects that option. The local adaptation catches only that specific error, verifies the exact observed runtime symlink and `libcoreclr.so`, then identifies the 3.1 runtime for payload selection. Other errors remain failures.

This adaptation and the payload target framework were exercised during the original device session. The new public wrapper is separately marked as locally checked until its complete backup/apply/restore loop is exercised on hardware.
