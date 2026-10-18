# Compatibility and limitations

## Supported input set

The observed platform is Tizen 6.0 / ARMv7 on Samsung UN65TU7000FXZA and
UN65AU8000FXZA televisions, using a macOS host. The profile name reflects the
original TU7000 input set (reported firmware 2301), not a model allowlist.
Other regions, builds, updates and hosts need compatibility checks. Temporary
root compatibility alone does not establish renderer compatibility.

`profiles/tu7000-2301.json` defines the original paths and SHA-256 values for CompHome, CompTerra, CompAdvertise, and ImplNUI. The build checks all four before patching. Framework references must come privately from the same TV. A mismatch stops the build; do not edit the hashes merely to bypass it. Model names in connection settings are identity metadata, not a compatibility allowlist. Accepting a configuration does not qualify a TV.

## Current behavior

Temporary root, overlay loading, selected app disable/enable, and shortcut removal have worked on the development TV. Standard SDB uninstall of protected apps was rejected; package operations here disable rather than uninstall. The current build includes v4 focus styling and optional private artwork. Startup preparation uses that same build manifest.

Video has been visible behind the dock, but continuous video/audio across every app and complete remote navigation have not been checked. Disabling TV Plus did not prove the separate native channel player had stopped. Movie Hub playback prevention remains unresolved. No reliable performance benchmark exists.

Backup, original restoration and v4 application have been exercised on the observed
platform. Full remote navigation, continuous playback and recovery across device
updates still require testing on each installation.

## Restart limits

Default overlays are volatile. The device-authorized startup helper has restored them on a later boot, with variable startup timing. Cold-power-loss restoration has not been established reliably. See [restart and persistence](restart-and-persistence.md) before relying on automatic restoration.
