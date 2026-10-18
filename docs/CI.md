# CI contract and maintenance handoff

Updated 2026-10-18. This is the active repository-side CI contract. There was no existing CI tracker or linked Desktop tracker for Tizen Dock. Baseline: clean `e4aa6df92148d08227f54094952db4c30f393d1e`. Changes in this pass remain an uncommitted working candidate; no push, settings change, service activation, release, signing, or TV operation is authorized by the CI result.

## Workflow responsibilities

`Source checks` (`.github/workflows/checks.yml`) runs independent Python, patcher, and security jobs. `offline` depends on all three and requires **success**, including every matrix child. Failure, cancellation, missing dependency or unexpected skip cannot satisfy that gate. Its existing check name is retained. Python `--strict-config`/`--strict-markers`, exit status, nonempty JUnit and coverage readers prevent empty/missing reports from becoming success. Reports never replace a failed command's exit status. The current offline suite has no approved skipped tests; an unexpected test skip also blocks.

| Event | Responsibility / platform | Policy |
| --- | --- | --- |
| `pull_request` | Python 3.12 on Ubuntu 24.04 and macOS 14; .NET 10 patchers on both; Linux security | Merge gates; no path filters, secrets, publishing or persistent runners |
| Push to `main` | Same contract, validates the merged source and emits baseline reports | No feature-branch duplicate push run; native reports available for future comparable baselines |
| Monday schedule, 07:23 UTC | Same checks plus Python 3.13/3.14 on Linux and bounded history report | Default branch only; weekly assurance. GitHub schedules can be delayed/dropped; a result older than eight days needs a manual refresh and never qualifies a different PR |
| `workflow_dispatch` | Same gates; optional typed boolean `compatibility` adds Python 3.13/3.14 | Safe default false; no device/production operations or arbitrary command inputs |
| `merge_group` | N/A | No merge queue observed in the active ruleset. Add trigger and verify stable `offline` on queued SHA before enabling a queue |
| Tags/releases/environments | N/A | No release workflow exists; ordinary CI never signs, uploads packages or deploys |

Health reporting is independent/advisory and is excluded from `offline`. No `workflow_run`, `pull_request_target`, reusable workflow, composite action or privilege transition is needed: there is one workflow and no repeated shared multi-job policy. Native `needs` expresses the dependencies.

## Check map

“Required” below is the workflow's policy and recommended repository protection, not an applied repository setting.

| Area / product risk | Exact workflow / job / command | Event / platform | Required, advisory, scheduled, or N/A | Reason / evidence |
| --- | --- | --- | --- | --- |
| Python source quality | `Source checks` / `Python (...)` / `python ci/run.py python`: Ruff check, Ruff format check, compileall | PR, main, weekly, manual; Linux/macOS | Required | Entire Python source, scripts, tests and CI helpers; existing Python normalized to establish formatting |
| Workflow and shell syntax | `Workflow and security` / actionlint 1.7.12 with ShellCheck 0.11.0 | All events; Linux | Required | Actions expressions/inputs plus embedded shell; generated cache apply script gets `sh -n` in its synthetic test |
| JSON/examples/profile/docs / direct lock drift | Python job / `python ci/check_source.py` | All Python entries | Required | JSON parsing, exact assembly hash shapes, local Markdown file references, direct input-to-lock consistency and public-file boundary; external URLs/anchor semantics are not network-checked in CI |
| Persistence/recovery/command-result boundaries | Python job / pytest `tests/` | All Python entries | Required | Snapshot checksum and chunking, corrupt snapshot retention, durable app state, app-ID guards, SDK exit markers, Home-launch rollback, cache framing and private archive allowlist |
| Unsafe overlay application | Python job / `test_incomplete_build_never_contacts_tv`, symlink/hash tests | All Python entries | Required | Build must list apply.sh and all four assemblies; listed inputs must be regular non-symlink files matching hashes before any adapter access |
| User's installation journey | Python job / `ci/package_smoke.py` | All Python entries | Required | Export only public files; build sdist; extract it to a new directory; locked tools + fresh editable install; outside-workspace CLI help and synthetic `doctor` |
| Distribution contents/reproducibility | Python job / `MANIFEST.in`, `package_smoke.py` | All Python entries | Required | Includes profiles, patchers, scripts, docs, SDK/lock configuration; no dependency on existing .local, .venv, obj/bin or local package metadata. Source workspace is supported; wheel-only operation is not supported or published |
| C# compilation and transformation | `.NET patchers (...)` / `python ci/run.py patchers` | PR, main, weekly, manual; Linux/macOS | Required | All six projects plus original synthetic fixture: locked restore, Release build with warnings as errors, positive layout transform and IL verification, six malformed-input refusals with expected error and no output |
| TV payload source compatibility | Patcher job / `legacy-payload-compile` | Same | Required | Runs bootstrap against pinned public upstream in disposable source, under SDK 10; only compiles the two netcoreapp3.1 payloads, never executes them or contacts a TV |
| Artwork/assets | Python job / PNG tests | All Python entries | Required | v3 backdrop and optional v4 ring: dimensions, PNG chunk CRC, decompression and transparent corners; generated assets are originals, not Samsung/provider artwork |
| Secrets | Security job / Gitleaks 8.30.1 `dir` and `git`, `--redact=100` | All events; full Git checkout for security | Required | Public candidate export and fetched history; .local/config.json never included; no allowlist or baseline hiding findings |
| Dependencies | Security job / OSV-Scanner 2.7.0 explicit lockfile list | All events | Required | 18 CI Python packages and seven NuGet lockfiles (Mono.Cecil repeated per project); all vulnerability findings block. Tool/API outage is failed/unavailable evidence, not zero findings. Framework/runtime vulnerabilities and the externally downloaded upstream Python environment are outside these locks; no device-runtime security claim |
| Python static security | Security job / Bandit 1.9.4, full JSON, high-severity gate | All events | Required HIGH; lower severities advisory | Full findings retained; no suppressions. Three medium findings reviewed below; no existing stricter policy was weakened |
| Inventory/licenses | Python job / `ci/inventory.py`; NOTICE and NuGet locks | All events | Required inventory; manual license review | Installed versions must match lock; license metadata retained or null; Mono.Cecil MIT, pinned upstream Unlicense. No blanket license allowlist or legal signoff |
| Coverage | Python job / pytest-cov branch coverage, XML + JSON | All events | Required valid report; percentage advisory | Measures CLI package only; scripts/C# measured by dedicated behavior/build checks, not a combined percentage. No arbitrary global threshold or changed-code delta without a comparable baseline |
| Performance/size | Python job / package bytes, installation elapsed; suite/check durations | All events | Advisory first measurements | Units, environment and input digest retained. Compression/time vary by platform and environment; no device FPS/memory/performance claim or noisy blocking budget |
| CI health | `CI health (advisory)` / `python ci/health.py` | Weekly/manual | Advisory | At most 30 completed source-workflow runs in 30 days; events separate, job failures/reruns visible, unavailable metrics null |
| Python static types | N/A | N/A | Omitted | Legacy CLI dynamically imports an upstream adapter with no typed interface. C# compilation checks C# types; adding a largely-any Python check would give little assurance. Behavioral boundaries are tested |
| UI/remote/accessibility/device behavior | N/A in hosted CI | Physical target | Omitted from automated acceptance | TV navigation, playback, v4 visual acceptance, overlays and restart persistence need the actual device and private exact binaries. Desktop/browser automation or Lighthouse would not exercise this product |
| Databases/services/migrations | Synthetic snapshots/cache tests; no service container | Python matrices | N/A for hosted service/migrations | Project has no hosted database, migration engine, API server, IaC or container. It prepares device commands; TV SQLite/mount semantics require separate device evidence |
| Windows / alternate hardware / ARM TV execution | N/A | N/A | Omitted | POSIX tools and macOS host documented; Linux provides offline source assurance. No claim of Windows, other firmware or TV execution qualification |

## Local commands

Use Python 3.12–3.14. Host patchers target `net10.0`; `global.json` pins SDK **10.0.402**, roll-forward disabled. Install it from [Microsoft's .NET 10 downloads](https://dotnet.microsoft.com/en-us/download/dotnet/10.0). For the SDK installed in the owner's user directory during this pass:

```sh
export DOTNET_ROOT="$HOME/.dotnet"
export PATH="$DOTNET_ROOT:$PATH"
dotnet --version
python3 -m venv /tmp/tizen-offline-ci
. /tmp/tizen-offline-ci/bin/activate
python -m pip install --require-hashes -r ci/requirements.txt
python -m pip install --no-deps --no-build-isolation -e .
python ci/install_tools.py /tmp/tizen-offline-tools actionlint shellcheck gitleaks osv-scanner
export PATH="/tmp/tizen-offline-tools:$PATH"
python ci/run.py python
python ci/run.py patchers
python ci/run.py security
python ci/health.py
```

The binary installer supports Linux x86_64 and macOS arm64, the platforms used for validation. It checks committed SHA256 values before installing individual regular executables; no archive extraction paths or remote install scripts are executed. An unsupported local architecture fails explicitly. Hosted matrices use their own setup actions.

`ci/run.py` replaces only its fixed `.ci-results/<suite>` directory. For retained local evidence, copy that public/synthetic report directory before rerunning the same suite. Scanners use the network for public releases/vulnerability metadata; “offline” here means no TV/provider/account operation, not no package network access. Pytest denies network connections and real TV adapters and redirects CLI state into synthetic temporary roots.

## Reports, failures and baselines

Every suite writes `.ci-results/<suite>/summary.md` and versioned `metrics.json`. Actions appends concise escaped HTML tables/measurements to `GITHUB_STEP_SUMMARY`. Identity includes tested SHA, public input digest, PR head SHA (separate from the tested merge SHA), ref/event, run URL/attempt, runtime, platform and UTC record time. A local SHA identifies the base; the input digest distinguishes the dirty worktree. The standalone aggregate also shows the actual `needs` results.

Python retains JUnit XML, coverage XML/JSON, bounded failing-test names, individual logs, package bytes and license metadata inventory. Patcher reports retain SDK information, build/refusal/transform/payload compile logs and command timings. Security retains redacted Gitleaks JSON, full Bandit JSON, OSV package/findings JSON and scanner versions. A missing/malformed required report fails its job; a failed command remains failed after reports run. Refusal tests additionally require the intended exception, so a missing runtime/executable cannot masquerade as valid rejection.

Uploads run with `always()`, have unique suite/platform/Python/run/attempt names, `if-no-files-found: error`, and 14-day retention. Health artifacts last 30 days. No source archive, Samsung binary, owner state, account token, `.local` or build output is uploaded. Pre-check setup/checkout failures can prevent report creation: their failed step plus a missing-artifact error is blocking, never a successful report. A cancelled job can prevent artifact finalization; `offline` still fails.

Baseline metrics remain null until a report with matching tools, suite scope, platform, runtime and input methodology is explicitly identified. Primary-branch reports are candidates for that comparison, not automatic interchangeable baselines. Changed-code coverage and performance deltas are unavailable in this first pass. Coverage counts describe actual tested lines/branches; they do not qualify hardware.

The history helper is read-only, uses the existing GitHub CLI/token, requests one page of at most 30 completed runs and at most 100 jobs per run. Its enrichment budget is 120 seconds, individual calls 15 seconds; it may make at most 61 requests (one list, up to 30 job pages and 30 first-attempt lookups). Partial API failures stay unavailable and cannot block correctness jobs. First-attempt rate excludes cancelled/neutral/skipped runs; reruns use the original attempt conclusion when accessible. A rerun recovery alone is not a flake diagnosis. It retains raw run elapsed (run start to final job completion), creation-to-first-job queue delay and summed job execution seconds. These are different measures; no billing-minute/cost claim. Medians/p95 are withheld because the Actions API does not provide comparable tool/input/suite fingerprints. Artifact/cache sizes, account quota, critical-path dependency tracing and causal failure/flake classification remain unavailable. No unbounded history crawler or cross-workflow stale-green rollup exists.

## Trust and maintenance policy

Permissions are read-only contents, with `actions: read` only for health. Checkouts disable credential persistence; PRs get no project secrets or write token. There are no caches: this small repository has fast restores, so cold correctness and avoiding fork cache trust are preferable to speculative caching. All actions are full-SHA pinned with version comments; binaries and Python tooling are checksum pinned; NuGet locked mode fixes resolved versions/content hashes. Workflow inputs only enter typed matrix selection; PR/report strings never interpolate into shell code or executable report templates. Summary values are HTML escaped.

Concurrency separates event and PR/ref; only superseded PR runs cancel automatically. Push/schedule/manual work is not cancelled by unrelated runs. Every job has a timeout and commands have bounded subprocess/network timeouts. Matrices use fail-fast false so independent diagnostic evidence survives another platform's failure.

Dependabot configuration proposes weekly Actions, pip and NuGet updates, with bounded open PR counts. It is repository configuration only; account/repository activation and bot behavior have not been changed or verified. Refresh Python hashes with a reviewed `uv pip compile ci/requirements.in --generate-hashes --output-file ci/requirements.txt` and rerun the gates. Review checksum-pinned binaries monthly against their official release assets. Update SDK/global.json through a reviewed maintenance change; .NET 10 is LTS through **2028-11-14**, verified against [Microsoft's policy](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core) and [release metadata](https://builds.dotnet.microsoft.com/dotnet/release-metadata/10.0/releases.json) on 2026-10-18. The .NET 10 migration notes were [reviewed](https://learn.microsoft.com/en-us/dotnet/core/compatibility/10). Legacy TV payloads still compile to **netcoreapp3.1**; do not install a 3.1 host runtime or retarget Samsung's installed runtime. This does not make that old TV runtime supported by Microsoft.

Bandit review (2026-10-18; revisit by 2027-01-18): B310 flags bootstrap's fixed HTTPS GitHub download URL; users cannot supply a scheme. B608 flags two app-ID SQL strings; `app_change` first enforces `[A-Za-z0-9_.-]+`, with synthetic quote/newline/shell-injection rejection tests. Nine low findings concern deliberate subprocess use. All remain visible, unsuppressed. New HIGH findings block; lower severities need human review, not automatic acceptance. SDK legacy-target warnings remain visible in the payload compilation log, while all host patcher builds treat warnings as errors.

## Integrations and eligibility

Verification date: **2026-10-18**. No new external service, account integration, token or code/report upload destination was activated. Native reporting fills the present need.

| Tool / status | Verified official source / eligibility | Permissions, data and limits / fallback |
| --- | --- | --- |
| GitHub native summaries/artifacts/Actions API: configured, hosted rendering unverified | [Summary docs](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#adding-a-job-summary), [billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) | Repository verified public. Standard hosted runner time is free for public repositories; larger runners are excluded. Free-plan included private allowance is 2,000 minutes/month, 500 MB artifact storage, 10 GB cache/repo; actual account plan/remaining quota not queried. Artifacts share storage with Packages; exhausted quota without payment blocks use. Reports stay in existing GitHub repository, 14/30 days; no LOC/upload-count service cap assumed. Local reports remain usable if upload fails, but required missing artifact fails the job |
| actionlint + ShellCheck: configured and locally verified | [actionlint](https://github.com/rhysd/actionlint), [ShellCheck](https://github.com/koalaman/shellcheck) | MIT/GPL-3.0 CLI tools inside runner; workflows/shell analyzed locally, no account or source/report upload, no service user/LOC/upload caps; runner resources apply |
| Gitleaks CLI: configured and locally verified | [Official project](https://github.com/gitleaks/gitleaks) | MIT CLI, no wrapper Action license/account dependency; public source and Git history analyzed locally, findings redacted. No service retention/LOC/upload caps; only GitHub artifact retention applies |
| OSV-Scanner: configured and locally verified | [Official docs](https://google.github.io/osv-scanner/), [lockfile support](https://google.github.io/osv-scanner/supported-languages-and-lockfiles/) | Apache-2.0 CLI; NuGet locks + pip requirements supported. Public package ecosystem/name/version metadata queried against OSV; no private source/report upload or new token/account. API availability/rate limits have no assumed entitlement; outage fails required evidence. No account-specific user/LOC/upload cap verified; local native findings are fallback |
| Bandit/pytest-cov/inventory: configured and locally verified | [Bandit](https://bandit.readthedocs.io/en/latest/), [pytest-cov](https://pytest-cov.readthedocs.io/en/latest/) | Local Python static checks and CLI coverage; no outside upload/account. Full findings and XML/JSON retained natively |
| Codecov: evaluated only, not recommended for activation now | [Plans](https://about.codecov.io/pricing/) | Official page lists free public unlimited uploads and private single-user 250 uploads/month. No account eligibility, retention or token configuration verified. Would send coverage and source paths/commit metadata externally; no such configuration added. Native coverage suffices; recheck all activation limits if an owner later requests changed-code service comparisons |
| SonarQube Cloud: evaluated only, not recommended | [Plan documentation](https://docs.sonarsource.com/sonarqube-cloud/administering-sonarcloud/managing-subscription/subscription-plans) | No unmet dashboard need justifies a second service. No plan/account/LOC/retention entitlement claimed or prepared; any future use needs a fresh exact free-tier/permission/data review and authorization |
| Lighthouse / hosted code scanning / dependency-review SaaS: not added | [Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci/blob/main/docs/getting-started.md) | No web UI to audit. No repository code-scanning settings assumed or changed; CLI security scans avoid unnecessary service activation |

## Observed hosted baseline and next handoff

Read-only inspection found public `dock108dev/tizen-dock`, default `main`, read-only default workflow token and no Actions SHA-pinning requirement. Its active `main` ruleset requires one PR approval and protects deletion/non-fast-forward pushes; it has no required status checks or merge queue. Legacy branch protection endpoint returned 404; the ruleset was inspected separately. No settings were changed. Recommended owner setting, after the new workflow is observed: add **`offline`** as required to the existing main ruleset, with GitHub Actions as the expected source. Keep review requirements intact.

Bounded window 2026-09-18 through 2026-10-18: one completed **Source checks** push run, [39142760793](https://github.com/dock108dev/tizen-dock/actions/runs/39142760793), on the baseline SHA passed first attempt. Measured elapsed 35 s, creation-to-first-job delay 2 s, summed job execution 33 s; zero reruns. First-attempt success 1/1 is a tiny historical sample, not a trend or evidence for these changes. No PR sample; no median, p95 or flake inference. A separate Dependency Graph run is outside this source-workflow sample.

Next action: review the working diff and retained local reports, then obtain authorization for committing/pushing a PR candidate. Observe the new Linux/macOS matrices and summary/artifact rendering on that exact commit before applying recommended protection. Hardware validation remains separately owner-controlled. No release readiness or device acceptance follows from local CI success.
