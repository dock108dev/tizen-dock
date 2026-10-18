# Validation record

Publication preparation: 2026-10-18.

## Local checks completed

- Python sources compiled successfully.
- Seven guard tests passed: backup corruption, backup path escape, build tampering before contact, invalid app IDs, interrupted app-state recording, preservation of retained shortcuts and cache generations, and refusal of unknown firmware inputs before build.
- All five source patcher projects compiled with SDK 9.
- The complete overlay pipeline built successfully against private original assemblies from the development device. Each component patch and final app-renderer mask passed its static readback checks. Generated application scripts remain private.
- The pinned source download and TU7000 runtime adaptation completed; both netcoreapp3.1 payloads compiled. The build reports the expected out-of-support target-framework warnings for the TV runtime.
- CLI help and local dependency-path validation were checked.

No connection to the TV, new device mutation, end-to-end public-wrapper backup/apply/restore run, performance benchmark, new visual acceptance, or persistence qualification was performed during publication preparation. These local results do not establish those outcomes.

The original device-session evidence and unmodified/private build inputs are retained locally and excluded from the public project. See [compatibility](compatibility.md) for the separate live-device findings and unresolved v3 visual confirmation. Hosted automated checks have their own status; local success does not imply a hosted run passed.
