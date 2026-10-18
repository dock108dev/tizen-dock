import json

import pytest

from health import aggregate
from reports import coverage_report, gate, summary, tests_report as read_tests


def test_gate_requires_all_required_successes():
    assert gate(
        {
            name: {"result": "success"}
            for name in ("python", "patchers", "startup", "security")
        }
    )


@pytest.mark.parametrize(
    "status", ["failure", "cancelled", "skipped", "timed_out", None]
)
def test_gate_fails_closed_for_required_result(status):
    needs = {
        name: {"result": "success"}
        for name in ("python", "patchers", "startup", "security")
    }
    needs["python"]["result"] = status
    assert not gate(needs)


def test_gate_refuses_missing_required_job():
    with pytest.raises(ValueError):
        gate({"python": {"result": "success"}})


@pytest.mark.parametrize(
    "document",
    [
        "",
        "<testsuites/>",
        '<testsuite tests="0" failures="0" errors="0" skipped="0" time="0"/>',
        '<testsuite tests="2" failures="0" errors="0" skipped="0" time="1"><testcase/></testsuite>',
    ],
)
def test_required_junit_cannot_be_empty_or_malformed(tmp_path, document):
    path = tmp_path / "junit.xml"
    path.write_text(document)
    with pytest.raises(Exception):
        read_tests(path)


def test_junit_keeps_failed_and_skipped_counts(tmp_path):
    path = tmp_path / "junit.xml"
    path.write_text(
        '<testsuite tests="3" failures="1" errors="0" skipped="1" time="1.25"><testcase name="pass"/><testcase name="fail"><failure>bad</failure></testcase><testcase name="skip"><skipped/></testcase></testsuite>'
    )
    report = read_tests(path)
    assert (report["passed"], report["failures"], report["skipped"]) == (1, 1, 1)
    assert report["duration_seconds"] == 1.25


def test_missing_required_coverage_fails(tmp_path):
    with pytest.raises(FileNotFoundError):
        coverage_report(tmp_path / "missing.json")
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps(
            {
                "totals": {
                    "covered_lines": 0,
                    "num_statements": 0,
                    "covered_branches": 0,
                    "num_branches": 0,
                }
            }
        )
    )
    with pytest.raises(ValueError):
        coverage_report(path)


def test_summary_escapes_untrusted_report_content(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    path = tmp_path / "summary.md"
    summary(
        {
            "result": "FAIL",
            "next_action": "<script>bad</script>\n[link](javascript:bad)",
        },
        path,
    )
    assert "<script>" not in path.read_text()
    assert "&lt;script&gt;" in path.read_text()


def test_history_separates_events_and_has_no_fake_trend_or_flakes():
    def row(event, conclusion, attempt=1):
        return {
            "event": event,
            "first_conclusion": conclusion,
            "conclusion": conclusion,
            "attempt": attempt,
            "elapsed_seconds": 35,
        }

    data = aggregate(
        [
            row("push", "success"),
            row("pull_request", "failure"),
            row("pull_request", "cancelled"),
        ]
    )
    assert data["push"]["first_attempt_pass_rate"] == 1
    assert data["pull_request"]["first_attempt_pass_rate"] == 0
    assert data["pull_request"]["first_attempt_sample"] == 1
    assert data["push"]["median_seconds"] is None
    assert data["push"]["p95_seconds"] is None
    assert data["push"]["suspected_flakes"] is None


def test_command_failure_is_retained_while_reporting_continues(tmp_path, monkeypatch):
    import run
    import sys

    monkeypatch.setattr(run, "ROOT", tmp_path)
    checks = run.Checks("python")
    assert not checks.command("failure", [sys.executable, "-c", "raise SystemExit(7)"])
    checks.report("missing", lambda: read_tests(tmp_path / "absent.xml"))
    checks.report("later-report", lambda: {"count": 1})
    assert [row["result"] for row in checks.rows] == ["FAIL", "FAIL", "PASS"]
    assert checks.rows[0]["exit_code"] == 7
    assert checks.metrics["missing"] is None


def test_refusal_requires_the_expected_reason(tmp_path, monkeypatch):
    import run
    import sys

    monkeypatch.setattr(run, "ROOT", tmp_path)
    checks = run.Checks("python")
    assert not checks.command(
        "unrelated-crash",
        [sys.executable, "-c", "raise SystemExit(1)"],
        expected="nonzero",
        contains="BadImageFormatException",
    )


@pytest.mark.parametrize(
    "counts",
    [
        None,
        {"tests": 0, "skipped": 0},
        {"tests": 10, "skipped": 10},
        {"tests": 10, "skipped": 1},
    ],
)
def test_required_suite_cannot_pass_with_missing_or_skipped_tests(counts):
    from reports import required_tests_executed

    assert not required_tests_executed(counts)


def test_node_junit_reports_real_pass_failure_and_skip_counts(tmp_path):
    path = tmp_path / "node.xml"
    path.write_text(
        '<testsuites><testcase name="pass" time="1"/><testcase name="fail" time="2"><failure/></testcase><testcase name="skip" time="0"><skipped/></testcase></testsuites>'
    )
    report = read_tests(path)
    assert (
        report["tests"],
        report["passed"],
        report["failures"],
        report["skipped"],
    ) == (3, 1, 1, 1)
    assert report["duration_seconds"] == 3


def test_gate_cannot_ignore_missing_or_failed_startup():
    needs = {name: {"result": "success"} for name in ("python", "patchers", "security")}
    with pytest.raises(ValueError):
        gate(needs)
    needs["startup"] = {"result": "failure"}
    assert not gate(needs)


def test_dependency_counts_remain_visible_for_findings_and_missing_evidence(tmp_path):
    from reports import dependency_report

    path = tmp_path / "osv.json"
    vulnerability = {"id": "SYNTHETIC-1", "database_specific": {"severity": "HIGH"}}
    path.write_text(
        json.dumps(
            {
                "results": [
                    {"packages": [{"vulnerabilities": [vulnerability, vulnerability]}]}
                ]
            }
        )
    )
    result = dependency_report(path)
    assert result["unique_vulnerabilities"] == 1
    assert result["severity"] == {"HIGH": 1}
    path.write_text('{"results":[]}')
    with pytest.raises(ValueError, match="no package evidence"):
        dependency_report(path)


@pytest.mark.parametrize("failures,errors", [(1, 0), (0, 1)])
def test_required_report_failure_cannot_be_hidden_by_successful_process(
    failures, errors
):
    from reports import required_tests_executed

    assert not required_tests_executed(
        {"tests": 2, "skipped": 0, "failures": failures, "errors": errors}
    )


@pytest.mark.parametrize(
    "document",
    [
        '<testsuite tests="1" failures="-1" errors="0" skipped="0" time="1"><testcase/></testsuite>',
        '<testsuite tests="1" failures="0" errors="0" skipped="0" time="NaN"><testcase/></testsuite>',
    ],
)
def test_junit_rejects_invalid_measurements(tmp_path, document):
    path = tmp_path / "report.xml"
    path.write_text(document)
    with pytest.raises(ValueError):
        read_tests(path)


@pytest.mark.parametrize("mode,expected", [("pass", 0), ("skipped", 1), ("missing", 1)])
def test_actual_aggregate_emits_summary_and_preserves_outcome(tmp_path, mode, expected):
    import os
    import subprocess
    import sys
    from pathlib import Path

    needs = {
        name: {"result": "success"}
        for name in ("python", "patchers", "startup", "security")
    }
    if mode == "skipped":
        needs["startup"]["result"] = "skipped"
    if mode == "missing":
        del needs["startup"]
    env = os.environ.copy()
    env.pop("GITHUB_STEP_SUMMARY", None)
    env["NEEDS_JSON"] = json.dumps(needs)
    (tmp_path / ".ci-results").mkdir()
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parents[1] / "ci/reports.py")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == expected
    text = (tmp_path / ".ci-results/gate-summary.md").read_text()
    assert ("PASS" if expected == 0 else "FAIL") in text
