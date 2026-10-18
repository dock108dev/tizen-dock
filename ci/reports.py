"""Small strict report readers and native Actions summaries. No report execution."""

import html
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET


def tests_report(path):
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    counts = {
        key: sum(int(s.attrib[key]) for s in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }
    cases = list(root.iter("testcase"))
    if counts["tests"] <= 0 or len(cases) != counts["tests"]:
        raise ValueError("Missing tests or inconsistent JUnit counts")
    if sum(counts[k] for k in ("failures", "errors", "skipped")) > counts["tests"]:
        raise ValueError("Invalid JUnit result counts")
    counts["passed"] = (
        counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
    )
    counts["duration_seconds"] = sum(float(s.attrib["time"]) for s in suites)
    counts["failing_tests"] = [
        f"{c.get('classname')}.{c.get('name')}"
        for c in cases
        if c.find("failure") is not None or c.find("error") is not None
    ][:10]
    return counts


def required_tests_executed(report):
    # This repository has no approved skips in its offline merge suite.
    return bool(report) and report["tests"] > 0 and report["skipped"] == 0


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


def gate(needs, expected=("python", "patchers", "security")):
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
    needs = json.loads(os.environ["NEEDS_JSON"])
    result = gate(needs)
    record = {
        "result": "PASS" if result else "FAIL",
        "required_jobs": needs,
        "tested_sha": os.environ.get("GITHUB_SHA"),
        "next_action": "Review job summaries and reports; missing, skipped or cancelled required jobs block merging.",
    }
    summary(record, ".ci-results/gate-summary.md")
    raise SystemExit(0 if result else 1)
