# Architecture and Tizen OS customization

## Access layers

1. Samsung Developer Mode permits the configured host to reach SDB.
2. The pinned public research adapter obtains an SDK command foothold and uses the SDK archive-launcher route for temporary root.
3. Root commands run through an authenticated, short-lived session. Its private launcher namespace and restoration checks belong to that adapter.
4. UI overlays must be bound through `nsenter -t 1 -m`, because a mount visible only inside the temporary root namespace does not change the running system menu.
5. Home restarts through SDK `app_launcher`, not through the temporary root context. The latter failed on the development TV because its namespace and security context differed.

The public CLI does not expose a password-based SSH login or install a background root controller.

## Menu components

| Assembly | Customization |
| --- | --- |
| CompHome | Returns a successful empty Home component list, preventing the default-card fallback |
| CompTerra | Returns an empty recommendation list, keeps the container invisible, and skips feed initialization and relevant event fetch callbacks |
| CompAdvertise | Hides the sponsored launcher element; keeps its provider installed |
| ImplNUI | Reduces the menu region, removes empty content/preview focus paths and preview loading, adjusts selected transition constants, and reshapes the launcher |

Both `.dll` and `.ni.dll` paths are mounted to the modified managed assembly so the runtime does not keep selecting the old native image. The development TV accepted managed fallback/JIT loading. Source files on the system partition are preserved.

## Renderer construction

`patchers/layout` and `patchers/terra` rewrite selected PE method bodies using metadata from the supplied input. The default build chains `dock-v1`, `dock-v2`, and `dock-v3` to remove feed paths, set geometry, and center the backdrop. These projects are build dependencies, not separate supported theme choices.

WebAppLauncher shortcuts use `ContentItemView` through FluxLauncherAppsBridge. Its `mainImage` needs the alpha mask; changing only `ImageTitleLauncherView` does not round these app shortcuts. The dock uses bottom-center parent and pivot anchors, a bounded background, and a clamped inner row while retaining Samsung's existing app-launch and remote infrastructure.

The optional v4 patcher gives app shortcuts private native backplates and hides their rectangular focus surface. A separate rounded outline supplies focus feedback, with gentler zoom. An optional exact-title artwork map replaces the image sources. Its mask dimensions match the 512-pixel replacement art to avoid cropping. Other Samsung controls retain shared backplate styling.

See [customization](customization.md) for default versus optional build behavior, and [restart and persistence](restart-and-persistence.md) for the separately installed experimental helper. The public CLI does not install a TV startup service.

## Independent state

Native `app_disable` flags, Home cached shortcut IDs, and renderer visibility are separate mechanisms. Changing one does not establish that the others changed. Likewise, an invisible preview surface is not proof that a separate channel player has stopped decoding or producing sound.

The observed app-ID lists and full databases remain private. The public project has no default list of apps to delete and never assumes that all vendor services are disposable.

## Root research adaptation

The upstream source revision is pinned in `scripts/bootstrap.py`. Its runtime enumeration normally calls `dotnet --list-runtimes`. Samsung's TU7000 launcher rejects that option. The local adaptation catches only that specific error, verifies the exact observed runtime symlink and `libcoreclr.so`, then identifies the 3.1 runtime for payload selection. Other errors remain failures.

The runtime adaptation and payloads have run on the development TV. The public wrapper's complete backup/apply/restore loop remains incompletely tested on hardware.
