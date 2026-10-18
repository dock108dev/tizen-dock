"""Small strict report readers and native Actions summaries. No report execution."""

import html
from collections import Counter
import json
import math
import os
from pathlib import Path
import xml.etree.ElementTree as ET


def tests_report(path):
    root = ET.parse(path).getroot()
    if root.tag not in ("testsuite", "testsuites"):
        raise ValueError("Unsupported JUnit root")
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    cases = list(root.iter("testcase"))
    if root.tag == "testsuites" and not suites:
        # Node's built-in JUnit reporter emits direct testcase children.
        counts = {
            "tests": len(cases),
            "failures": sum(c.find("failure") is not None for c in cases),
            "errors": sum(c.find("error") is not None for c in cases),
            "skipped": sum(c.find("skipped") is not None for c in cases),
        }
        duration = sum(float(c.attrib["time"]) for c in cases)
    else:
        counts = {
            key: sum(int(s.attrib[key]) for s in suites)
            for key in ("tests", "failures", "errors", "skipped")
        }
        duration = sum(float(s.attrib["time"]) for s in suites)
    if (
        any(value < 0 for value in counts.values())
        or not math.isfinite(duration)
        or duration < 0
    ):
        raise ValueError("Invalid JUnit counts or duration")
    if counts["tests"] <= 0 or len(cases) != counts["tests"]:
        raise ValueError("Missing tests or inconsistent JUnit counts")
    if sum(counts[k] for k in ("failures", "errors", "skipped")) > counts["tests"]:
        raise ValueError("Invalid JUnit result counts")
    counts["passed"] = (
        counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
    )
    counts["duration_seconds"] = duration
    counts["failing_tests"] = [
        f"{c.get('classname')}.{c.get('name')}"
        for c in cases
        if c.find("failure") is not None or c.find("error") is not None
    ][:10]
    return counts


def required_tests_executed(report):
    # This repository has no approved skips in its offline merge suite.
    return (
        bool(report)
        and report["tests"] > 0
        and report["skipped"] == 0
        and report.get("failures") == 0
        and report.get("errors") == 0
    )


def coverage_report(path):
    totals = json.loads(Path(path).read_text())["totals"]
    required = ("covered_lines", "num_statements", "covered_branches", "num_branches")
    if (
        any(not isinstance(totals[k], int) or totals[k] < 0 for k in required)
        or totals["num_statements"] == 0
    ):
        raise ValueError("Invalid coverage totals")
    if (
        totals["covered_lines"] > totals["num_statements"]
        or totals["covered_branches"] > totals["num_branches"]
    ):
        raise ValueError("Inconsistent coverage totals")
    return {key: totals[key] for key in required} | {
        "percent_covered": totals["percent_covered"]
    }


def dependency_report(path):
    report = json.loads(Path(path).read_text())
    packages = [p for row in report["results"] for p in row["packages"]]
    if not packages:
        raise ValueError("Dependency scanner produced no package evidence")
    findings = {v["id"]: v for p in packages for v in p.get("vulnerabilities", [])}
    return {
        "unique_vulnerabilities": len(findings),
        "package_observations": len(packages),
        "ids": sorted(findings),
        "severity": dict(
            Counter(
                v.get("database_specific", {}).get("severity") or "UNKNOWN"
                for v in findings.values()
            )
        ),
        "database": "OSV query at recorded_utc; database snapshot age unavailable",
    }


def gate(needs, expected=("python", "patchers", "startup", "security")):
    if set(needs) != set(expected):
        raise ValueError("Missing or unexpected required jobs")
    return all(needs[name]["result"] == "success" for name in expected)


def summary(record, path):
    def escaped(value):
        return html.escape(str(value if value is not None else "unavailable"))

    text = f"### Offline CI: {escaped(record['result'])}\n\n"
    text += "<table><tr><th>Identity / environment</th><th>Value</th></tr>"
    for key in (
        "suite",
        "tested_sha",
        "public_input_sha256",
        "pr_head_sha",
        "event",
        "ref",
        "run_link",
        "platform",
        "python",
        "elapsed_seconds",
    ):
        if key in record:
            text += f"<tr><td>{key}</td><td>{escaped(record[key])}</td></tr>"
    text += "</table>\n\n"
    if "checks" in record:
        text += "<table><tr><th>Check</th><th>Outcome</th><th>Seconds</th><th>Diagnostics</th></tr>"
        for row in record["checks"]:
            text += (
                "<tr>"
                + "".join(
                    f"<td>{escaped(row.get(key))}</td>"
                    for key in (
                        "name",
                        "result",
                        "seconds",
                        "reason" if "reason" in row else "log",
                    )
                )
                + "</tr>"
            )
        text += "</table>\n\n"
    if "required_jobs" in record:
        text += (
            "<pre>"
            + escaped(json.dumps(record["required_jobs"], indent=2))
            + "</pre>\n"
        )
    metrics = record.get("metrics", record.get("health"))
    if metrics is not None:
        # Health raw samples live in the artifact; show only grouped counts here.
        if "health" in record:
            metrics = {k: v for k, v in metrics.items() if k != "runs"}
        text += (
            "Measurements (no baseline unless identified):\n<pre>"
            + escaped(json.dumps(metrics, indent=2))
            + "</pre>\n"
        )
    text += "\nNext action: " + escaped(record.get("next_action")) + "\n"
    if record.get("reason"):
        text += "\nUnavailable: " + escaped(record["reason"]) + "\n"
    text += "\nFull logs and machine-readable reports: download this job’s reports artifact from the run.\n"
    Path(path).write_text(text)
    if target := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(target, "a") as stream:
            stream.write(text)


if __name__ == "__main__":
    needs = None
    reason = None
    try:
        needs = json.loads(os.environ["NEEDS_JSON"])
        result = gate(needs)
    except (ValueError, KeyError, TypeError) as error:
        result = False
        reason = str(error)
    record = {
        "result": "PASS" if result else "FAIL",
        "required_jobs": needs,
        "reason": reason,
        "tested_sha": os.environ.get("GITHUB_SHA"),
        "next_action": "Review job summaries and reports; missing, skipped or cancelled required jobs block merging.",
    }
    summary(record, ".ci-results/gate-summary.md")
    raise SystemExit(0 if result else 1)
