# Development

## Local checks

```sh
python -m compileall -q src scripts
python -m unittest discover -s tests -v
```

Build each `patchers/*/Patcher.csproj` with SDK 9. These projects use Mono.Cecil 0.11.6. Builds need package restore, but no TV. Tests use synthetic data and fake adapters; they must never connect to a real TV in automation.

An offline overlay build requires authentic private inputs matching the allowlisted profile. Use `scripts/build-overlays.py` with a new output directory. Generated assets and assemblies remain under `.local/`. Do not commit decompiled Samsung implementation files or device-derived build outputs.

## Adding a profile

Keep the existing profile unchanged. Record the new exact model, on-screen version, observed platform/runtime, file paths, and original SHA-256 values. Inspect the actual method signatures, bodies, references, native-image behavior, and Home cache format. Do not treat a passing hash edit as compatibility research.

Qualify, separately: temporary access and cleanup; consistent backup and integrity verification; reversible app-state round trip; overlay mounting and restore; Home launch; visible fit/focus/Back/Settings/Inputs; app launching; video/audio behavior; and a power-cycle recovery. Retain private evidence and publish only a sanitized status table. Stop before applying if a source structure or runtime prerequisite is unexpected.

## Contribution scope

Useful next work includes v3 device confirmation, source cleanup after that confirmation, Movie Hub/channel-player lifecycle analysis, performance measurements, and a secure optional reapplication strategy. Persistent boot modification and a universal model installer are outside the current implementation.

See [CONTRIBUTING](../CONTRIBUTING.md), [security notes](../SECURITY.md), and [validation](validation.md).
