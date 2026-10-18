"""Startup suite definitions for the shared offline runner."""

import hashlib
import json

from check_source import ROOT
from reports import required_tests_executed, tests_report


def startup_checks(checks):
    checks.command("node-version", ["node", "--version"])
    checks.command("npm-version", ["npm", "--version"])
    checks.metrics["node-runtime"] = {
        "node": (checks.output / "node-version.log").read_text().strip(),
        "npm": (checks.output / "npm-version.log").read_text().strip(),
    }
    for path in sorted(
        [
            *ROOT.glob("startup/service/*.js"),
            *ROOT.glob("startup/*.js"),
            *ROOT.glob("scripts/*.cjs"),
            *ROOT.glob("tests/*.cjs"),
        ]
    ):
        checks.command("syntax-" + path.stem, ["node", "--check", str(path)])
    checks.command(
        "startup-tests",
        [
            "node",
            "--test",
            "--test-reporter=junit",
            "--test-reporter-destination=" + str(checks.output / "junit.xml"),
            "tests/startup-ci.test.cjs",
        ],
        timeout=180,
    )
    checks.report("tests", lambda: tests_report(checks.output / "junit.xml"))
    checks.rows.append(
        {
            "name": "required-tests-executed",
            "result": "PASS"
            if required_tests_executed(checks.metrics.get("tests"))
            else "FAIL",
        }
    )

    def inventory():
        lock = json.loads((ROOT / "package-lock.json").read_text())
        rows = [
            {
                "name": name.removeprefix("node_modules/"),
                "version": value.get("version"),
                "license": value.get("license"),
                "integrity": value.get("integrity"),
            }
            for name, value in lock["packages"].items()
            if name
        ]
        if not rows or any(not row["version"] or not row["integrity"] for row in rows):
            raise ValueError("Incomplete Node dependency inventory")
        (checks.output / "inventory.json").write_text(json.dumps(rows, indent=2))
        return {
            "packages": len(rows),
            "lockfile_sha256": hashlib.sha256(
                (ROOT / "package-lock.json").read_bytes()
            ).hexdigest(),
            "startup_source_bytes": sum(
                p.stat().st_size for p in ROOT.glob("startup/service/*.js")
            ),
            "baseline": None,
        }

    checks.report("node-inventory", inventory)
