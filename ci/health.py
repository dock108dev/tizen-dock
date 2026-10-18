"""Read-only bounded Actions history; unavailable metrics stay null."""

from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import time

from reports import summary


def api(endpoint):
    result = subprocess.run(
        ["gh", "api", endpoint], check=True, capture_output=True, text=True, timeout=15
    )
    return json.loads(result.stdout)


def timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def aggregate(rows):
    groups = {}
    for event in sorted({row["event"] for row in rows}):
        sample = [row for row in rows if row["event"] == event]
        eligible = [
            row
            for row in sample
            if row["first_conclusion"]
            in ("success", "failure", "timed_out", "action_required", "startup_failure")
        ]
        durations = [
            row["elapsed_seconds"]
            for row in sample
            if row["elapsed_seconds"] is not None
        ]
        groups[event] = {
            "runs": len(sample),
            "conclusions": dict(Counter(row["conclusion"] for row in sample)),
            "first_attempt_sample": len(eligible),
            "first_attempt_pass_rate": sum(
                row["first_conclusion"] == "success" for row in eligible
            )
            / len(eligible)
            if eligible
            else None,
            "rerun_runs": sum(row["attempt"] > 1 for row in sample),
            "recovered_runs": sum(
                row["attempt"] > 1
                and row["first_conclusion"] == "failure"
                and row["conclusion"] == "success"
                for row in sample
            ),
            "duration_sample": len(durations),
            "median_seconds": None,
            "p95_seconds": None,
            "duration_statistics_reason": "Actions metadata lacks comparable tool, input and suite fingerprints; raw per-run timing retained",
            "failed_job_counts": dict(
                Counter(
                    j["name"]
                    for row in sample
                    for j in (row.get("jobs") or [])
                    if j["conclusion"] in ("failure", "timed_out")
                )
            ),
            "suspected_flakes": None,
        }
    return groups


def collect():
    repository = os.environ.get("GITHUB_REPOSITORY", "dock108dev/tizen-dock")
    since = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
    endpoint = f"repos/{repository}/actions/workflows/checks.yml/runs?per_page=30&status=completed&created=%3E%3D{since}"
    runs = api(endpoint)["workflow_runs"][:30]
    rows = []
    deadline = time.monotonic() + 120
    for run in runs:
        row = {
            "run_id": run["id"],
            "sha": run["head_sha"],
            "event": run["event"],
            "url": run["html_url"],
            "attempt": run["run_attempt"],
            "conclusion": run["conclusion"],
            "first_conclusion": run["conclusion"] if run["run_attempt"] == 1 else None,
            "elapsed_seconds": None,
            "queue_seconds": None,
            "job_execution_seconds_sum": None,
            "jobs": None,
            "artifact_bytes": None,
            "cache_bytes": None,
            "billing_cost": None,
        }
        try:
            if time.monotonic() < deadline:
                data = api(
                    f"repos/{repository}/actions/runs/{run['id']}/jobs?per_page=100"
                )
                jobs = data["jobs"]
                row["jobs"] = [
                    {"name": j["name"], "conclusion": j["conclusion"]} for j in jobs
                ]
                complete = (
                    data["total_count"] == len(jobs)
                    and bool(jobs)
                    and all(j["started_at"] and j["completed_at"] for j in jobs)
                )
                if complete:
                    first = min(timestamp(j["started_at"]) for j in jobs)
                    end = max(timestamp(j["completed_at"]) for j in jobs)
                    row["elapsed_seconds"] = (
                        end - timestamp(run["run_started_at"])
                    ).total_seconds()
                    row["queue_seconds"] = (
                        first - timestamp(run["created_at"])
                    ).total_seconds()
                    row["job_execution_seconds_sum"] = sum(
                        (
                            timestamp(j["completed_at"]) - timestamp(j["started_at"])
                        ).total_seconds()
                        for j in jobs
                    )
            if run["run_attempt"] > 1 and time.monotonic() < deadline:
                row["first_conclusion"] = api(
                    f"repos/{repository}/actions/runs/{run['id']}/attempts/1"
                )["conclusion"]
        except (subprocess.SubprocessError, ValueError, KeyError) as error:
            # Optional telemetry: never substitute successful results or fail correctness jobs.
            row["unavailable_reason"] = type(error).__name__
        rows.append(row)
    return {
        "since_utc_date": since,
        "max_runs": 30,
        "sample_size": len(rows),
        "groups": aggregate(rows),
        "runs": rows,
        "method": "checks.yml completed runs; event groups separate; elapsed run-start to last job-end; queue creation to first job-start; no timing aggregates without comparable fingerprints; no causal flake inference",
        "limits": "120-second enrichment budget; max 100 jobs/run; no artifact contents or billing API; historic attempts only queried for reruns",
    }


if __name__ == "__main__":
    output = Path(".ci-results/health")
    output.mkdir(parents=True, exist_ok=True)
    try:
        record = {
            "result": "PASS",
            "health": collect(),
            "tested_sha": os.environ.get("GITHUB_SHA"),
            "next_action": "Use comparable event/platform samples; failures need log diagnosis, reruns alone are not flakes.",
        }
    except (subprocess.SubprocessError, ValueError, KeyError) as error:
        record = {
            "result": "NOT RUN",
            "health": None,
            "reason": type(error).__name__,
            "next_action": "Restore read-only Actions API access. Correctness gates are independent.",
        }
    (output / "metrics.json").write_text(json.dumps(record, indent=2) + "\n")
    summary(record, output / "summary.md")
