"""Build source-only overlays from an owner's exact, private original assemblies."""

import argparse
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tizen_dock.contracts import PROFILE, REMOTE, ROOT, sha, validate_artifact_name


def load_artwork(artwork_map):
    if artwork_map is None:
        return {}
    if artwork_map.is_symlink() or artwork_map.stat().st_size > 65536:
        raise ValueError("Invalid artwork map file")
    mapping = json.loads(artwork_map.read_text())
    if not isinstance(mapping, dict) or not 1 <= len(mapping) <= 64:
        raise ValueError("Artwork map must contain 1–64 exact titles and PNG filenames")
    for title, name in mapping.items():
        validate_artifact_name(name)
        if (
            not isinstance(title, str)
            or not title.strip()
            or len(title) > 256
            or not name.endswith(".png")
        ):
            raise ValueError("Invalid artwork map entry")
        if name.startswith(("compact-dock-", "focus-ring-")):
            raise ValueError("Artwork conflicts with generated assets")
        source = artwork_map.parent / name
        if (
            source.is_symlink()
            or not source.is_file()
            or source.stat().st_size > 8 * 1024 * 1024
        ):
            raise ValueError("Invalid artwork file: " + name)
        with source.open("rb") as stream:
            header = stream.read(24)
        if (
            len(header) != 24
            or header[:8] != b"\x89PNG\r\n\x1a\n"
            or header[12:16] != b"IHDR"
            or struct.unpack(">II", header[16:24]) != (512, 512)
        ):
            raise ValueError("Artwork must be a 512 × 512 PNG: " + name)
    return mapping


def build(originals, output, artwork_map=None):
    mapping = load_artwork(artwork_map)
    profile_path = PROFILE
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
    v3 = output / "ImplNUI.v3.dll"
    (output / "ImplNUI.dll").rename(v3)
    subprocess.run(
        [sys.executable, str(ROOT / "patchers/dock-v4/make-assets.py"), str(output)],
        check=True,
    )
    extra = []
    if mapping:
        for name in set(mapping.values()):
            shutil.copyfile(artwork_map.parent / name, output / name)
        frozen_map = output / "artwork-map.json"
        frozen_map.write_text(json.dumps(mapping))
        extra = [frozen_map]
    run("dock-v4", v3, output / "ImplNUI.dll", originals, REMOTE, *extra)
    v3.unlink()
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
        "renderer_version": "v4",
        "visual_acceptance": "pending on target TV",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Private build:", output, "Review apply.sh before using apply.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--originals", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument(
        "--artwork-map",
        type=Path,
        help="Private exact-title map; 512px PNGs alongside it",
    )
    args = ap.parse_args()
    build(
        args.originals.resolve(),
        args.output.resolve(),
        args.artwork_map.resolve() if args.artwork_map else None,
    )
