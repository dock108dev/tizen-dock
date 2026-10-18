"""Run independent offline checks, retain exits/logs, emit native CI summaries."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from check_source import ROOT, public_files
from reports import summary
from suites.python import python_checks
from suites.patchers import patcher_checks
from suites.startup import startup_checks
from suites.security import security_checks


class Checks:
    def __init__(self, suite, output_root=None):
        self.suite = suite
        self.output = (output_root or ROOT / ".ci-results") / suite
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
        # Hash public source only; exclude private files and generated output.
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
            else "Review job summaries before testing changes on a TV",
        }
        (self.output / "metrics.json").write_text(json.dumps(record, indent=2) + "\n")
        summary(record, self.output / "summary.md")
        return 0 if passed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=("python", "patchers", "startup", "security"))
    parser.add_argument(
        "--output-root",
        type=Path,
        help="Write reports under this directory",
    )
    args = parser.parse_args()
    os.chdir(ROOT)
    checks = Checks(
        args.suite, args.output_root.resolve() if args.output_root else None
    )
    try:
        {
            "python": python_checks,
            "patchers": patcher_checks,
            "startup": startup_checks,
            "security": security_checks,
        }[args.suite](checks)
    except Exception as error:
        checks.rows.append({"name": "suite", "result": "FAIL", "reason": str(error)})
    raise SystemExit(checks.finish())
