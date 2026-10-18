# Development

## Offline checks

The [CI contract](CI.md) is the source for dependency installation, the four
required suite commands, reporting and the current dependency blocker. Checks use
synthetic state; no TV, Samsung account or owner certificate is needed. Downloads
and vulnerability queries require network access.

For a quick standard-library-only guard check, `python -m unittest discover -s tests -p test_guards.py -v` still runs the original `unittest` suite; it is a subset, not the full CI contract. New pytest suites require the locked tools.

An overlay build requires private originals matching the profile. The
[customization workflow](customization.md) produces v4, optionally using an artwork
map. Keep original and patched Samsung-derived files under `.local/`.

## Implementation boundaries

The numbered dock patchers are dependencies of the assembly transformation chain, not independent themes. Retain them until the build itself changes. The current build produces v4; prepare and install its device-authorized startup helper using [restart and persistence](restart-and-persistence.md).

The CLI expects an editable source workspace with configuration at its root. `--config` can select another configuration file, but relative dependency paths are resolved against the project root. Tests and offline builds do not read private credentials or require Samsung account sign-in.

## Adding device support

Add a separate profile instead of changing the existing one. Determine the exact model, firmware, platform/runtime, paths, original hashes, method structures, native-image behavior, and cache format. Validate access, backup integrity, reversible app state, overlay loading/removal, Home launch, visible layout/navigation, streaming behavior, and restart recovery on that device. A passing hash edit is not compatibility work.

Include the model, firmware, and scope of testing with a change. Keep private device data out of reports. See [CONTRIBUTING](../CONTRIBUTING.md) and [security](../SECURITY.md).

## Source organization and maintenance

- `ci/run.py` owns command execution, exits and report output.
  `ci/suites/` owns the Python, patcher, startup and security check definitions.
  `ci/reports.py` validates reports and the aggregate gate. Keep check policy out
  of the runner's orchestration class.
- `startup/index.html`, `app.css` and `app.js` are the startup widget's markup,
  styles and UI behavior. Preparation fills the private key placeholder in the
  copied `app.js`; the source must never contain an actual observer credential.
- `startup/service/main.js` owns startup lifecycle/status. The transport modules
  remain together by protocol responsibility with their upstream licenses; they
  are not alternative installers. The C# projects retain one transformation
  stage each because their ordered intermediate hashes are compatibility gates.

Python follows the existing Ruff configuration. Authored startup UI/service and
Node scripts use `.prettierrc.json`; the optional formatting command is
`npm exec --yes --package=prettier@3.6.2 -- prettier --write PATHS`.
Protocol adapters retain their upstream formatting rather than receiving a
mechanical rewrite.

Generated reports and device state belong in ignored `.ci-results/` and `.local/`.
Required source fixtures, runtime artwork and dependency locks are build inputs.
