"""Validate public examples, documentation links and source-only privacy boundary."""

import json
from pathlib import Path
import re
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def public_files():
    # Includes current untracked fixes, excludes ignored owner files and CI outputs.
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [Path(p) for p in result.stdout.decode().split("\0") if p]


def check():
    files = public_files()
    for name in files:
        if (
            name.parts[0] in (".local", ".venv")
            or str(name) == "config.json"
            or name.suffix
            in (".dll", ".pdb", ".db", ".pem", ".key", ".p12", ".wgt", ".tpk")
        ):
            raise ValueError(f"Private/generated input in public source: {name}")
        if name.suffix == ".json":
            json.loads((ROOT / name).read_text())
        if name.suffix == ".md":
            for target in re.findall(
                r"\[[^\]]*\]\(([^)\s]+)\)", (ROOT / name).read_text()
            ):
                if ":" in target or target.startswith("#"):
                    continue
                dest = (ROOT / name.parent / target.split("#")[0]).resolve()
                if not dest.is_relative_to(ROOT) or not dest.exists():
                    raise ValueError(f"Broken local link in {name}: {target}")
    lock = (ROOT / "ci/requirements.txt").read_text()
    for line in (ROOT / "ci/requirements.in").read_text().splitlines():
        if line and not line.startswith("#"):
            if not re.fullmatch(r"[A-Za-z0-9_.-]+==[0-9][A-Za-z0-9_.-]*", line):
                raise ValueError("CI input must use exact versions")
            if not re.search(r"^" + re.escape(line) + r"(?: \\)?$", lock, re.MULTILINE):
                raise ValueError("CI lock drift: " + line)
    tomllib.loads((ROOT / "pyproject.toml").read_text())
    profile = json.loads((ROOT / "profiles/tu7000-2301.json").read_text())
    assert len(profile["assemblies"]) == 4
    assert all(
        re.fullmatch("[a-f0-9]{64}", item["sha256"]) for item in profile["assemblies"]
    )
    print(
        f"Validated {len(files)} public files, JSON examples, profile and local Markdown links"
    )


if __name__ == "__main__":
    check()
