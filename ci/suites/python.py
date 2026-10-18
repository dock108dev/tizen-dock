"""Python suite definitions for the shared offline runner."""

import json
import sys

from reports import coverage_report, required_tests_executed, tests_report


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
