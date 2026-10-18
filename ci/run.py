"""Run independent offline checks, retain exits/logs, emit native CI summaries."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

from check_source import ROOT, public_files
from reports import coverage_report, required_tests_executed, summary, tests_report


class Checks:
    def __init__(self, suite):
        self.suite = suite
        self.output = ROOT / ".ci-results" / suite
        if self.output.exists():
            shutil.rmtree(self.output)  # Only this fixed, disposable report directory.
        self.output.mkdir(parents=True)
        self.rows = []
        self.metrics = {}
        self.started = time.monotonic()

    def command(self, name, args, timeout=180, expected=0, contains=None, **kwargs):
        started = time.monotonic()
        log = self.output / f"{name}.log"
        with log.open("w") as stream:
            try:
                result = subprocess.run(
                    args,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    timeout=timeout,
                    **kwargs,
                )
                code = result.returncode
                passed = (code != 0) if expected == "nonzero" else code == expected
            except (OSError, subprocess.TimeoutExpired) as error:
                stream.write(str(error))
                code, passed = None, False
        if contains is not None and contains not in log.read_text():
            passed = False
        self.rows.append(
            {
                "name": name,
                "result": "PASS" if passed else "FAIL",
                "exit_code": code,
                "seconds": round(time.monotonic() - started, 3),
                "log": log.name,
            }
        )
        print(f"{name}: {self.rows[-1]['result']} ({log})", flush=True)
        return passed

    def report(self, name, function):
        try:
            self.metrics[name] = function()
            self.rows.append({"name": name, "result": "PASS"})
        except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as error:
            self.metrics[name] = None
            self.rows.append({"name": name, "result": "FAIL", "reason": str(error)})

    def finish(self):
        passed = bool(self.rows) and all(r["result"] == "PASS" for r in self.rows)
        # Hash only public candidate inputs, not private files, logs or caches.
        digest = hashlib.sha256()
        for name in sorted(public_files()):
            digest.update(
                str(name).encode() + b"\0" + (ROOT / name).read_bytes() + b"\0"
            )
        identity = subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip()
        record = {
            "schema_version": 1,
            "result": "PASS" if passed else "FAIL",
            "suite": self.suite,
            "tested_sha": os.environ.get("GITHUB_SHA", identity),
            "public_input_sha256": digest.hexdigest(),
            "pr_head_sha": os.environ.get("PR_HEAD_SHA") or None,
            "ref": os.environ.get("GITHUB_REF"),
            "event": os.environ.get("GITHUB_EVENT_NAME", "local"),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "run_link": f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
            if os.environ.get("GITHUB_RUN_ID")
            else None,
            "recorded_utc": datetime.now(timezone.utc).isoformat(),
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "elapsed_seconds": round(time.monotonic() - self.started, 3),
            "checks": self.rows,
            "metrics": self.metrics,
            "baseline": None,
            "next_action": "Review failing logs/reports"
            if not passed
            else "Review exact-candidate hosted checks and device evidence separately",
        }
        (self.output / "metrics.json").write_text(json.dumps(record, indent=2) + "\n")
        summary(record, self.output / "summary.md")
        return 0 if passed else 1


def python_checks(checks):
    python = sys.executable
    checks.command("ruff-version", [python, "-m", "ruff", "--version"])
    checks.command(
        "lint",
        [python, "-m", "ruff", "check", "src", "scripts", "tests", "patchers", "ci"],
    )
    checks.command(
        "format",
        [
            python,
            "-m",
            "ruff",
            "format",
            "--check",
            "src",
            "scripts",
            "tests",
            "patchers",
            "ci",
        ],
    )
    checks.command(
        "compile",
        [python, "-m", "compileall", "-q", "src", "scripts", "patchers/dock-v4", "ci"],
    )
    checks.command("source-contract", [python, "ci/check_source.py"])
    checks.command(
        "tests",
        [
            python,
            "-m",
            "pytest",
            "--junitxml=" + str(checks.output / "junit.xml"),
            "--cov=tizen_dock",
            "--cov-report=xml:" + str(checks.output / "coverage.xml"),
            "--cov-report=json:" + str(checks.output / "coverage.json"),
            "--cov-report=term-missing",
        ],
        timeout=240,
    )
    checks.report("tests", lambda: tests_report(checks.output / "junit.xml"))
    executed = required_tests_executed(checks.metrics.get("tests"))
    checks.rows.append(
        {
            "name": "required-tests-executed",
            "result": "PASS" if executed else "FAIL",
            "reason": "All offline tests are required; zero collection, unavailable results or unexpected skips block"
            if not executed
            else "No unexpected skips",
        }
    )
    checks.report("coverage", lambda: coverage_report(checks.output / "coverage.json"))
    checks.command(
        "fresh-export",
        [python, "ci/package_smoke.py", str(checks.output / "package.json")],
        timeout=480,
    )
    checks.report(
        "package", lambda: json.loads((checks.output / "package.json").read_text())
    )


def patcher_checks(checks):
    checks.command("sdk", ["dotnet", "--info"])
    projects = sorted(ROOT.glob("patchers/*/Patcher.csproj"))
    if len(projects) != 6:
        raise ValueError("Expected all six patcher projects")
    fixture = ROOT / "tests/patcher-fixture/Fixture.csproj"
    for project in [*projects, fixture]:
        name = project.parent.name
        if checks.command(
            name + "-restore",
            ["dotnet", "restore", str(project), "--locked-mode", "--nologo"],
        ):
            checks.command(
                name + "-build",
                [
                    "dotnet",
                    "build",
                    str(project),
                    "--no-restore",
                    "--configuration",
                    "Release",
                    "--nologo",
                    "--warnaserror",
                    "-v",
                    "minimal",
                ],
            )
        else:
            checks.rows.append(
                {
                    "name": name + "-build",
                    "result": "NOT RUN",
                    "reason": "Restore failed",
                }
            )
    with tempfile.TemporaryDirectory(prefix="tizen-patchers-") as temporary:
        root = Path(temporary)
        original = root / "synthetic.dll"
        transformed = root / "transformed.dll"
        harness = fixture.parent / "bin/Release/net10.0/Fixture.dll"
        checks.command(
            "fixture-create", ["dotnet", str(harness), "create", str(original)]
        )
        checks.command(
            "layout-transform",
            [
                "dotnet",
                str(ROOT / "patchers/layout/bin/Release/net10.0/Patcher.dll"),
                str(original),
                str(transformed),
                "Synthetic.Cache",
            ],
        )
        checks.command(
            "layout-verify", ["dotnet", str(harness), "verify", str(transformed)]
        )
        bootstrap = root / "payload-source/scripts/bootstrap.py"
        bootstrap.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / "scripts/bootstrap.py", bootstrap)
        shutil.copyfile(ROOT / "global.json", bootstrap.parents[1] / "global.json")
        checks.command(
            "legacy-payload-compile",
            [sys.executable, str(bootstrap)],
            timeout=240,
            cwd=bootstrap.parents[1],
        )
        invalid = root / "invalid.dll"
        invalid.write_bytes(b"synthetic invalid PE")
        for project in projects:
            destination = root / (project.parent.name + ".dll")
            checks.command(
                project.parent.name + "-refusal",
                [
                    "dotnet",
                    str(project.parent / "bin/Release/net10.0/Patcher.dll"),
                    str(invalid),
                    str(destination),
                    *(
                        ["Synthetic.Cache"]
                        if project.parent.name == "layout"
                        else [str(root), str(root)]
                        if project.parent.name == "dock-v4"
                        else [str(root)]
                        if project.parent.name in ("dock-v2", "dock-v3")
                        else []
                    ),
                ],
                expected="nonzero",
                contains="Unqualified renderer input"
                if project.parent.name == "dock-v4"
                else "BadImageFormatException",
            )
            checks.report(
                project.parent.name + "-no-output",
                lambda destination=destination: no_output(destination),
            )


def no_output(path):
    if path.exists():
        raise ValueError("Rejected input produced output")
    return {"output_created": False}


def security_checks(checks):
    python = sys.executable
    checks.command("shellcheck-version", ["shellcheck", "--version"])
    checks.command("actionlint-version", ["actionlint", "--version"])
    checks.command("actionlint", ["actionlint", "-color"])
    checks.command("gitleaks-version", ["gitleaks", "version"])
    checks.command("osv-version", ["osv-scanner", "--version"])
    # Full source findings remain visible; the reviewed gate blocks HIGH findings.
    checks.command(
        "bandit",
        [
            python,
            "-m",
            "bandit",
            "-r",
            "src",
            "scripts",
            "patchers",
            "-f",
            "json",
            "-o",
            str(checks.output / "bandit.json"),
            "--exit-zero",
        ],
    )

    def static_results():
        report = json.loads((checks.output / "bandit.json").read_text())
        if report["errors"]:
            raise ValueError("Bandit source parsing failed")
        counts = dict(Counter(row["issue_severity"] for row in report["results"]))
        checks.metrics["static_counts_by_severity"] = counts
        if counts.get("HIGH", 0):
            raise ValueError("High severity static findings")
        return {
            "high": 0,
            "medium": counts.get("MEDIUM", 0),
            "low": counts.get("LOW", 0),
        }

    checks.report("static-analysis", static_results)
    with tempfile.TemporaryDirectory(prefix="tizen-public-scan-") as temporary:
        export = Path(temporary)
        for relative in public_files():
            source = ROOT / relative
            if source.is_symlink():
                raise ValueError("Public scan refuses symlinks")
            target = export / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        checks.command(
            "secrets-source",
            [
                "gitleaks",
                "dir",
                str(export),
                "--redact=100",
                "--no-banner",
                "--timeout=120",
                "--report-format=json",
                "--report-path=" + str(checks.output / "gitleaks-source.json"),
            ],
        )
    checks.command(
        "secrets-history",
        [
            "gitleaks",
            "git",
            ".",
            "--redact=100",
            "--no-banner",
            "--timeout=120",
            "--report-format=json",
            "--report-path=" + str(checks.output / "gitleaks-history.json"),
        ],
    )

    def secret_results():
        reports = [
            json.loads((checks.output / ("gitleaks-" + scope + ".json")).read_text())
            for scope in ("source", "history")
        ]
        if any(not isinstance(report, list) for report in reports):
            raise ValueError("Malformed secret report")
        count = sum(len(report) for report in reports)
        if count:
            raise ValueError(f"{count} secret findings; see redacted report")
        return {
            "findings": count,
            "scope": "public candidate files and fetched git history",
        }

    checks.report("secret-findings", secret_results)
    locks = [
        ROOT / "ci/requirements.txt",
        *sorted(ROOT.glob("patchers/*/packages.lock.json")),
        ROOT / "tests/patcher-fixture/packages.lock.json",
    ]
    if any(not p.is_file() for p in locks):
        raise ValueError("Missing dependency lockfile")
    command = [
        "osv-scanner",
        "scan",
        "source",
        "--format=json",
        "--all-packages",
        "--output-file=" + str(checks.output / "osv.json"),
    ]
    for lock in locks:
        command += ["--lockfile", str(lock)]
    checks.command("dependencies", command, timeout=240)

    def dependency_results():
        report = json.loads((checks.output / "osv.json").read_text())
        packages = [p for r in report["results"] for p in r["packages"]]
        if not packages:
            raise ValueError("Dependency scanner produced no package evidence")
        ids = {v["id"] for p in packages for v in p.get("vulnerabilities", [])}
        if ids:
            raise ValueError(f"{len(ids)} vulnerability findings")
        return {
            "unique_vulnerabilities": 0,
            "package_observations": len(packages),
            "severity": {},
            "database": "OSV online query at recorded_utc; database snapshot age unavailable",
        }

    checks.report("dependency-findings", dependency_results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=("python", "patchers", "security"))
    args = parser.parse_args()
    os.chdir(ROOT)
    checks = Checks(args.suite)
    try:
        {
            "python": python_checks,
            "patchers": patcher_checks,
            "security": security_checks,
        }[args.suite](checks)
    except Exception as error:
        checks.rows.append({"name": "suite", "result": "FAIL", "reason": str(error)})
    raise SystemExit(checks.finish())
