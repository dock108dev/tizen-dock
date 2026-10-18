# Development

## Offline checks

Follow the [CI contract](CI.md) to install hash-locked Python tools, pinned scanners and the SDK selected by `global.json`. Run all three suites from a Git checkout:

```sh
python ci/run.py python
python ci/run.py patchers
python ci/run.py security
```

Tests use synthetic files, temporary state and fake adapters. The Python suite includes formatting/lint, behavioral tests, coverage and a clean source-distribution install. The patcher suite builds all six host projects with SDK 10.0.402, checks a synthetic transformation and input refusals, and compiles the pinned legacy payload source in a disposable directory. Security checks validate Actions/shell, secrets, dependencies and Python static findings. Reports stay under ignored `.ci-results/`; see the contract for artifact policy and evidence limits. No Samsung binaries, TV connection or account is needed. Package downloads and vulnerability queries require network access.

For a quick standard-library-only guard check, `python -m unittest discover -s tests -p test_guards.py -v` still runs the original `unittest` suite; it is a subset, not the full CI contract. New pytest suites require the locked tools.

An overlay build additionally requires private original assemblies matching the profile. Run `scripts/build-overlays.py` with a new output directory. It produces the default v3 renderer. The optional [v4 artwork patcher](customization.md#optional-artwork-and-focus-styling) has its own input gate and manual asset workflow. Keep generated files under `.local/`; do not publish Samsung-derived inputs or outputs.

## Implementation boundaries

The numbered dock patchers are dependencies of the assembly transformation chain, not independent themes. Retain them until the build itself changes. The public build does not install the experimental TV-side startup helper; see [restart and persistence](restart-and-persistence.md).

The CLI expects an editable source workspace with configuration at its root. `--config` can select another configuration file, but relative dependency paths are resolved against the project root. Tests and offline builds do not read private credentials or require Samsung account sign-in.

## Adding device support

Add a separate profile instead of changing the existing one. Determine the exact model, firmware, platform/runtime, paths, original hashes, method structures, native-image behavior, and cache format. Validate access, backup integrity, reversible app state, overlay loading/removal, Home launch, visible layout/navigation, streaming behavior, and restart recovery on that device. A passing hash edit is not compatibility work.

Include the model, firmware, and scope of testing with a change. Keep private device data out of reports. See [CONTRIBUTING](../CONTRIBUTING.md) and [security](../SECURITY.md).
