# Troubleshooting

| Symptom | Check / recovery |
| --- | --- |
| SDB cannot connect | TV and computer network, Developer Mode host address, host firewall, guest-network isolation, VPN routing, then full TV power cycle |
| Callback timeout | The TV must reach the computer; set `callback_host` only to the correct LAN interface and allow the callback through the firewall |
| Shell permission denied | Ordinary SDB shell access is not unrestricted on this TV; use the pinned adapter route after setup |
| `Unknown option --list-runtimes` | Run the pinned bootstrap adaptation; do not generalize it to an unrecognized runtime path |
| Original assembly mismatch | Stop. Confirm the firmware and whether old overlays are still mounted. A different input needs a new reviewed profile |
| Existing project stage | Restore/unmount first, verify original hashes, then archive the unused project staging directory before retrying |
| Home fails to launch from root | Relaunch with `tizen-dock restart-home`, which uses the SDK context |
| Home does not recover | Use `restore-menu`, inspect local records, then fully power-cycle if necessary; persistent app/cache changes still need their own restoration |
| Blank On Now area | Verify the component, container and renderer overlays together; hiding the feed alone leaves focus/loading paths active |
| Icons remain square | Verify the loaded renderer hash, restart Home, and check the ContentItemView mask resource. An older ImageTitle-only patch does not affect WebAppLauncher shortcuts |
| Square white corners behind rounded apps | The v4 patcher isolates the native app backplate and adds its own rounded outline; verify both renderer and assets |
| Logos show only middle letters | Replacement artwork and mask must both be 512 × 512 for the optional artwork map; a smaller mask crops the source |
| Dock disappears after restart | Default mounts are temporary. The experimental helper is separate and cold-power-loss recovery remains incompletely tested; see [restart and persistence](restart-and-persistence.md) |
| Startup takes longer than 10 seconds | Startup scheduling and network readiness add time before the service starts; see the helper's status for its service timing |
| Huge panel / bad centering | The v4 build changes the background container's anchor and dimensions through its ordered patcher chain. Confirm the renderer revision before adjusting values; layout units are not pixels |
| TV Plus gone but channel audio remains | A separate native channel player can continue running. Disabling the app is not proof of stopped playback; this remains unresolved |
| App is disabled but tile remains | Package state and Home cache are separate. Prepare a backed-up cache edit using the exact component ID |
| Cache helper reports stale input | The TV changed those files after the snapshot. Take a new backup and rebuild the edit; do not bypass the hash check |
| Build fails resolving TV types | Collect all five reference assemblies from the same device and pass the private originals directory |
| Build fails restoring .NET references | Confirm SDK 10.0.402 from `global.json`, select its directory on PATH, and confirm network access for package restore. Do not bundle Samsung DLLs to work around missing device inputs |
| Backup integrity fails | Preserve the remote snapshot and private logs; do not apply changes using that incomplete backup |

If reporting a problem, include the exact model, on-screen firmware, project revision, failing command name, and a redacted error excerpt. Do not attach databases, private configuration, account screens, raw logs, Samsung DLLs, keys, or a full snapshot.
