# Compatibility and current status

## Observed hardware

| Field | Development device |
| --- | --- |
| Model | Samsung UN65TU7000FXZA, 65-inch TU7000 family |
| Reported software version | 2301, supplied from the owner's TV information |
| Observed platform | Tizen 6.0, ARMv7 |
| Observed managed runtime | Microsoft.NETCore.App 3.1.3 through Samsung's launcher |
| Host | macOS |
| TV user for app controls | 5001 |

The version is a reported value, not a universal firmware compatibility claim. Other TU7000 variants, screen sizes, regions, builds, and newer updates are unqualified. Root-route compatibility is broader upstream, but that does not qualify this project's UI patchers.

## Exact source gate

`profiles/tu7000-2301.json` lists paths and SHA-256 values for CompHome, CompTerra, CompAdvertise, and ImplNUI. The build checks all four before changing any assembly. Reference libraries are collected privately from the same TV; they are not distributed. A mismatch stops the build. Do not change the allowlisted hashes just to bypass a mismatch.

## Evidence and limits

| Capability | Result |
| --- | --- |
| SDB connection and initial SDK command route | Observed working |
| Temporary archive-launcher root | Observed UID/GID 0 and full effective capability mask |
| Standard SDB removal of selected preinstalled apps | Rejected by the TV; no successful uninstall claim |
| Native app disable/enable | Observed; one Hulu enable/disable round trip verified |
| Nine selected unwanted apps and related dedicated services | Disable flags verified; shared infrastructure preserved |
| Home shortcut removal | Owner confirmed selected shortcuts were gone |
| Upper cards / recommendation cleanup | Owner reported improvement; early revision left blank On Now space |
| Renderer v1 | Loaded; owner rejected small, square icons and overflow |
| Renderer v2 | Loaded; owner rejected square icons, excessive panel height, and poor fit |
| Renderer v3 | Loaded with matching device hash; shorter centered container and app-specific masking implemented; visual/navigation acceptance pending |
| Streaming behind Home | Owner photos show video behind the dock; continuous playback and audio across apps remain unqualified |
| Movie Hub / TV Plus playback prevention | Unresolved; channel-player process remained after TV Plus package disabling |
| Performance improvement | No benchmark or reliable latency claim established |
| Survives full power loss | Renderer overlays do not; native app/cache changes may persist |

These are separate evidence levels: a successful build, a live loaded assembly, an owner photo, and successful navigation are not interchangeable. No completed iOS or tvOS replacement is claimed.

The public tools were reorganized from the device session. Local source builds and guard tests are recorded in [validation](validation.md). The reorganized end-to-end device workflow has not been rerun against the TV as part of publication.
