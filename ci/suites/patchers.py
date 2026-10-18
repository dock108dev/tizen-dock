"""Patchers suite definitions for the shared offline runner."""

from pathlib import Path
import shutil
import sys
import tempfile

from check_source import ROOT


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
