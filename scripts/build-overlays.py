"""Build source-only overlays from an owner's exact, private original assemblies."""

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REMOTE = "/home/owner/share/tizen-dock/menu-overlay"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(originals, output):
    profile_path = ROOT / "profiles/tu7000-2301.json"
    profile = json.loads(profile_path.read_text())
    for item in profile["assemblies"]:
        if sha(originals / (item["name"] + ".dll")) != item["sha256"]:
            raise ValueError("Original assembly mismatch: " + item["name"])
    for name in profile["references"]:
        if not (originals / (name + ".dll")).is_file():
            raise ValueError("Missing private reference assembly: " + name)
    if output.exists():
        raise ValueError("Output already exists; select a new directory")
    output.mkdir(parents=True, mode=0o700)

    def run(name, *args):
        dest = ROOT / ".local/patcher-tools" / name
        subprocess.run(
            [
                "dotnet",
                "build",
                str(ROOT / "patchers" / name / "Patcher.csproj"),
                "-o",
                str(dest),
                "--nologo",
                "-v",
                "q",
            ],
            check=True,
        )
        subprocess.run(
            ["dotnet", str(dest / "Patcher.dll"), *(str(a) for a in args)], check=True
        )

    run(
        "layout",
        originals / "CompHome.dll",
        output / "CompHome.dll",
        "Tizen.Tv.App.CoBA.Components.Home.CompHome/HomeComponentCache",
    )
    run(
        "layout",
        originals / "CompTerra.dll",
        output / "CompTerra.empty.dll",
        "ContentsBrowser.CompTerraLayerList",
    )
    run("terra", output / "CompTerra.empty.dll", output / "CompTerra.dll")
    run(
        "layout",
        originals / "CompAdvertise.dll",
        output / "CompAdvertise.dll",
        "Tizen.Tv.App.CoBA.Components.Advertise.AdvertiseLauncherElement",
    )
    run("dock-v1", originals / "ImplNUI.dll", output / "ImplNUI.v1.dll")
    run("dock-v2", output / "ImplNUI.v1.dll", output / "ImplNUI.v2.dll", originals)
    run("dock-v3", output / "ImplNUI.v2.dll", output / "ImplNUI.dll", originals)
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/draw-assets.py"), str(output)], check=True
    )
    for name in ("CompTerra.empty.dll", "ImplNUI.v1.dll", "ImplNUI.v2.dll"):
        (output / name).unlink()
    # The unmodified source DLL remains on the system partition. Every bind is
    # made in PID 1's mount namespace and is rolled back on partial failure.
    script = [
        "#!/bin/sh",
        "set -eu",
        f"stage={REMOTE}",
        '[ ! -e "$stage" ] || { echo EXISTING_PROJECT_STAGE_ABORT; exit 1; }',
    ]
    for x in profile["assemblies"]:
        script.append(
            f'[ "$(nsenter -t 1 -m -- sha256sum {shlex.quote(x["path"])} | cut -d " " -f 1)" = {x["sha256"]} ] || {{ echo ORIGINAL_MISMATCH_{x["name"]}; exit 1; }}'
        )
    script += [
        'mkdir -p "$stage"',
        'mounted=""',
        "trap 'for path in $mounted; do nsenter -t 1 -m -- umount -l \"$path\" || true; done' EXIT",
    ]
    files = list(output.glob("*.dll")) + list(output.glob("*.png"))
    original = profile["assemblies"][0]["path"]
    for f in files:
        script += [
            f'cp -a {shlex.quote(original)} "$stage/{f.name}"',
            f'cat /home/owner/share/tmp/sdk_tools/{f.name} > "$stage/{f.name}"',
            f'chmod 644 "$stage/{f.name}"',
            f'[ "$(sha256sum "$stage/{f.name}" | cut -d " " -f 1)" = {sha(f)} ] || exit 1',
        ]
    for x in profile["assemblies"]:
        for path in (x["path"], x["path"][:-4] + ".ni.dll"):
            script += [
                f'nsenter -t 1 -m -- mount --bind "$stage/{x["name"]}.dll" {shlex.quote(path)}',
                f'mounted="{path} $mounted"',
            ]
    script += ["trap - EXIT", "echo TEMPORARY_OVERLAYS_INSTALLED"]
    (output / "apply.sh").write_text("\n".join(script) + "\n")
    files.append(output / "apply.sh")
    manifest = {
        "profile_sha256": sha(profile_path),
        "files": {f.name: sha(f) for f in files},
        "experimental": True,
        "visual_acceptance": "unconfirmed for v3",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Private build:", output, "Review apply.sh before using apply.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--originals", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    build(args.originals.resolve(), args.output.resolve())
