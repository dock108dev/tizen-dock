# Compatibility and limitations

## Supported input set

Development has used a Samsung **UN65TU7000FXZA**, 65-inch TU7000 family, with on-screen software version reported as **2301**. Tizen 6.0, ARMv7, TV user 5001, and Microsoft.NETCore.App 3.1.3 through Samsung's launcher were observed. The host was macOS.

This is not a compatibility claim for every TV labeled TU7000 or firmware 2301. Other regions, sizes, builds, updates, and hosts need separate qualification. Upstream root compatibility does not imply renderer compatibility.

`profiles/tu7000-2301.json` defines the original paths and SHA-256 values for CompHome, CompTerra, CompAdvertise, and ImplNUI. The build checks all four before patching. Framework references must come privately from the same TV. A mismatch stops the build; do not edit the hashes merely to bypass it.

## Current behavior

Temporary root, overlay loading, selected app disable/enable, and shortcut removal have worked on the development TV. Standard SDB uninstall of protected apps was rejected; package operations here disable rather than uninstall. The latest optional artwork customization has owner-confirmed rounded focus and full logos fitting inside the tiles. The default public build remains v3; the v4 source patcher is separate.

Video has been visible behind the dock, but continuous video/audio across every app and complete remote navigation have not been checked. Disabling TV Plus did not prove the separate native channel player had stopped. Movie Hub playback prevention remains unresolved. No reliable performance benchmark exists.

The public wrapper's complete backup/apply/restore workflow has not been qualified end to end on additional hardware. Local tests and source builds do not establish that outcome.

## Restart limits

Default overlays are volatile. A separately installed experimental helper has restored them on a later boot, approximately 10 seconds after its service started. An unplug test was unsuccessful, repeat cold-boot testing was deferred, and Developer Mode host-IP behavior remains incompletely tested. See [restart and persistence](restart-and-persistence.md) before relying on automatic restoration.
