# Testing and continuous integration

The `Source checks` workflow runs four independent required suites. Its `offline`
job succeeds only when every required job and matrix entry succeeds. Failed,
cancelled, missing or unexpectedly skipped checks block the aggregate gate.

## Run locally

Use Python 3.14, Node 22 or 24, and the .NET SDK pinned by `global.json`.
Install the SDK as described in [setup](setup.md), then run from a Git checkout:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r ci/requirements.txt
python -m pip install --no-deps --no-build-isolation -e .
npm ci --ignore-scripts --no-audit --no-fund
python ci/install_tools.py .local/ci-tools actionlint shellcheck gitleaks osv-scanner
export PATH="$PWD/.local/ci-tools:$PATH"

python ci/run.py python
python ci/run.py patchers
python ci/run.py startup
python ci/run.py security
```

These checks need no TV, Samsung account or personal signing certificate.
Dependency downloads and vulnerability queries require internet access. Tests use
disposable synthetic state. Signing tests generate disposable certificates that
cannot authorize installation on a Samsung TV.

| Suite | Checks |
| --- | --- |
| `python` | Ruff lint/format, compilation, examples and documentation links, unit tests, line/branch coverage, clean source-distribution installation |
| `patchers` | Locked NuGet restore, all six patchers built with warnings as errors, synthetic IL transformation, invalid-input refusal, compilation of pinned TV payload source |
| `startup` | Node syntax, ECMAScript 2019 compatibility for TV scripts, lifecycle and status access control, root-agent authentication, synthetic widget signatures, wrong-device and symlink rejection |
| `security` | actionlint/ShellCheck, redacted source/history secret scans, Python static analysis and dependency scanning of Python, Node and NuGet locks |

The runner is `ci/run.py`; definitions live under `ci/suites/`. A quick subset is
available with `python -m unittest discover -s tests -p test_guards.py -v`.

## Workflow events and platforms

| Event | Checks |
| --- | --- |
| Pull request and push to `main` | Python 3.14, .NET patchers and Node 24 on Ubuntu 24.04/macOS 14; security on Linux |
| Monday at 07:23 UTC | The same checks plus Node 22 on Linux and advisory CI-health reporting |
| Manual dispatch | Required suites; the boolean `compatibility` input adds Node 22 on Linux |

Schedules run on the default branch and can be delayed. `merge_group` is not
configured; add that trigger before using a merge queue. There is no release or
deployment workflow. CI does not install anything on a TV or use owner credentials.

All actions are commit-pinned. Python requirements, NuGet dependencies and Node
packages are locked; scanner binaries are checksum-verified. npm lifecycle scripts
are disabled during installation. Checkouts do not persist credentials, tokens
are read-only, and no persistent self-hosted runner or shared cache is used.
Only superseded pull-request runs are cancelled automatically.

## Reports and failure policy

Reports are written to `.ci-results/<suite>/` and summarized in GitHub job
summaries. Use `--output-root PATH` to choose another report directory. Repeating
a suite replaces that suite's output directory.

Reports include command exits/timings, test counts, coverage, dependency findings,
runtime versions, package sizes and source revision information. Required missing
or malformed reports fail the suite; report generation cannot hide a failed
command. Unexpected skipped tests also fail. Baseline/delta fields remain empty
unless comparable measurements are available; coverage and size have no arbitrary
percentage or timing budget.

Actions uploads suite reports even after failure, using unique run/matrix names
and 14-day retention. Advisory CI-health reports have 30-day retention. No generated
widget, certificate, Samsung binary, private configuration or device backup is
uploaded. CI-health sampling is read-only and bounded to 30 completed runs from
30 days, with a 120-second enrichment budget. Cancelled runs and reruns are
reported separately; rerun success alone is not evidence of a flaky test.

Dependency findings and HIGH Python static findings block. Lower static severities
remain visible for review. Deliberate subprocess use, fixed download URLs and
validated app-ID SQL are not silently suppressed. See [security](../SECURITY.md)
for the known signing-tool dependency issue.

## Recorded local verification

Retained local reports from 2026-10-18 record 88 passing Python tests with no
skips, six passing startup test groups, and successful patcher builds and
synthetic input checks. The security report records passing source/history
secret scans and no HIGH Python static findings, but fails the dependency gate
for `GHSA-86w9-cpqp-85rv`; see [security](../SECURITY.md).

Those reports were produced before the current documentation revision and
include different public-source digests for some suites. They are individual
local results, not a passing aggregate for the current checkout or a hosted
GitHub run. Device startup and cold-boot behavior require separate verification
under [restart and persistence](restart-and-persistence.md).

## Maintenance and limits

Dependabot covers Actions, pip, npm and NuGet. Update requirements and regenerate
their hash lock with `uv pip compile ci/requirements.in --python-version 3.14 --generate-hashes --output-file ci/requirements.txt`.
Use `npm install --package-lock-only --ignore-scripts` for reviewed Node updates,
then rerun startup and security checks. Keep action SHAs, scanner checksums and
`global.json` aligned with reviewed tool versions.

Reporting uses native GitHub summaries/artifacts and local open-source tools; no
separate dashboard account is required. OSV receives package metadata for lookup,
not private source or reports. Tool/network outages mean unavailable checks, not
zero findings. Repository protection is configured separately; `offline` is the
aggregate check to require after verifying the workflow in GitHub.

Automated checks do not establish TV playback, remote accessibility, firmware
compatibility or cold-start persistence. These need device testing. Python's
dynamic upstream adapter is tested behaviorally rather than through a largely
untyped static checker. Windows operation and wheel-only installation are not
supported; the editable source workspace is the documented distribution.
