"""Security suite definitions for the shared offline runner."""

from collections import Counter
import json
from pathlib import Path
import shutil
import sys
import tempfile

from check_source import ROOT, public_files
from reports import dependency_report


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
        ROOT / "package-lock.json",
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
        result = dependency_report(checks.output / "osv.json")
        checks.metrics["dependency_counts"] = result
        if result["unique_vulnerabilities"]:
            raise ValueError(
                f"{result['unique_vulnerabilities']} vulnerability findings"
            )
        return result

    checks.report("dependency-findings", dependency_results)
