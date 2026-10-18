# Restart and persistence

## What the public tools do

The dock is loaded with temporary bind mounts over Samsung assemblies. The files on the system partition remain intact. `restart-home` relaunches the Home application; it does not reboot the TV or remove those mounts. A system reboot or removal of power clears the mounts. App disable flags and edited Home shortcuts are separate persistent state.

A remote's ordinary Power press may only enter standby. Seeing the dock after standby is not a reboot test. Holding Power until the Samsung logo appears requests a fuller restart; unplugging power for 30 seconds tests recovery after power removal. Allow the TV and its network to finish starting before judging a startup helper.

## Experimental TV-side startup helper

A separately signed helper, Tizen Dock Startup, is installed on the development TV. It runs locally on the TV and is intended to work without a Mac restore process. Its source, signing setup, and installer remain private local experimental material, not part of the public CLI or a supported download. The public setup instructions do not install it.

The helper starts an on-boot web service, uses local loopback SDB for temporary authenticated root, verifies staged assets and original/overlay hashes, reapplies missing overlays, and relaunches Home through the SDK context. It closes the temporary command channel when finished. A token-protected, read-only status endpoint reports progress; there is no LAN command endpoint. Its current restore configuration targets the accepted higher-resolution artwork and rounded focus styling.

On a later system boot, the service reported `active` and `reapplied`; inspection found the modified assemblies in the live Home process, and the owner saw the custom dock. That restore completed roughly **10 seconds after the service started**. Time before service startup is additional and has not been characterized. Do not present this as “the dock is ready 10 seconds after power-on.”

An earlier unplug test was reported unsuccessful. A controlled repeat with a fresh boot checkpoint was deferred. Operation with the Mac physically off has not been directly tested. The helper is designed to run on the TV, but reliable recovery after power loss is **not established**.

## Developer Mode host IP

For normal setup, use the **computer's current LAN IPv4 address** as Host PC IP in Apps → 12345 → Developer Mode. This is separate from the TV's own address in `config.json`. Save and restart after changing the setting.

Loopback host IP `127.0.0.1` was tested while investigating the helper. Earlier attempts logged connection resets/timeouts; a later local restore succeeded with the computer's address configured. That does not establish which setting is required across cold boots, network changes, or other firmware. **Host-IP testing is incomplete.** Do not switch everyone to loopback as a proven persistence fix. It can interfere with external development access.

## Recovery

If the helper is installed and you want to stop automatic restoration, uninstall **Tizen Dock Startup** from TV Apps before fully restarting. Otherwise it may reapply overlays after a reboot even though that reboot cleared the previous mounts.

For Mac debugging, restore the computer's current LAN address in Developer Mode, restart, and use the normal connection commands. Inspect private status/logs before changing assemblies. A file hash or running process alone is insufficient: confirm the visible menu after Home reloads.

Samsung account sign-in was used to request the helper's author/distributor signing certificates. This is separate from ordinary CLI access, which requires no hosted Tizen Dock account. Certificates, passwords, device authorization files, status tokens, signed packages, and service logs must remain private. Do not reuse or publish another device's signing package.
