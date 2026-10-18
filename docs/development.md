# Development

## Offline checks

From the project root with the Python environment active:

```sh
python -m compileall -q src scripts patchers/dock-v4
python -m unittest discover -s tests -v
for project in patchers/*/Patcher.csproj; do
  dotnet build "$project" --nologo -v q
done
```

Tests use synthetic files and fake adapters. They cover backup integrity, path and app-ID guards, interrupted app-state recording, cache editing, and refusal of unrecognized inputs. They must not connect to a TV in automation. Patcher builds require SDK 9 and package restore; building source alone requires no Samsung binaries or device connection. These are also the checks used by the source workflow in `.github/workflows/checks.yml`.

An overlay build additionally requires private original assemblies matching the profile. Run `scripts/build-overlays.py` with a new output directory. It produces the default v3 renderer. The optional [v4 artwork patcher](customization.md#optional-artwork-and-focus-styling) has its own input gate and manual asset workflow. Keep generated files under `.local/`; do not publish Samsung-derived inputs or outputs.

## Implementation boundaries

The numbered dock patchers are dependencies of the assembly transformation chain, not independent themes. Retain them until the build itself changes. The public build does not install the experimental TV-side startup helper; see [restart and persistence](restart-and-persistence.md).

The CLI expects an editable source workspace with configuration at its root. `--config` can select another configuration file, but relative dependency paths are resolved against the project root. Tests and offline builds do not read private credentials or require Samsung account sign-in.

## Adding device support

Add a separate profile instead of changing the existing one. Determine the exact model, firmware, platform/runtime, paths, original hashes, method structures, native-image behavior, and cache format. Validate access, backup integrity, reversible app state, overlay loading/removal, Home launch, visible layout/navigation, streaming behavior, and restart recovery on that device. A passing hash edit is not compatibility work.

Include the model, firmware, and scope of testing with a change. Keep private device data out of reports. See [CONTRIBUTING](../CONTRIBUTING.md) and [security](../SECURITY.md).
