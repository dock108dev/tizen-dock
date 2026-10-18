"""Extract only build inputs from a checksum-verified private TV snapshot."""

import argparse
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--backup", type=Path, required=True)
ap.add_argument("--output", type=Path, required=True)
a = ap.parse_args()
m = json.loads((a.backup / "manifest.json").read_text())
if m["archive"] != "snapshot.tar.gz":
    raise SystemExit("Unexpected archive name")
archive = a.backup / m["archive"]
if hashlib.sha256(archive.read_bytes()).hexdigest() != m["sha256"]:
    raise SystemExit("Archive checksum mismatch")
profile = json.loads((ROOT / "profiles/tu7000-2301.json").read_text())
wanted = {x["path"].lstrip("/"): x["name"] + ".dll" for x in profile["assemblies"]}
wanted.update(
    {path.lstrip("/"): name + ".dll" for name, path in profile["references"].items()}
)
if a.output.exists():
    raise SystemExit("Output already exists")
a.output.mkdir(parents=True, mode=0o700)
with tarfile.open(archive, "r:gz") as t:
    for path, name in wanted.items():
        member = t.getmember(path)
        if not member.isfile() or member.size > 16 * 1024 * 1024:
            raise SystemExit("Unexpected archive member")
        with t.extractfile(member) as source:
            (a.output / name).write_bytes(source.read())
print("Private build inputs:", a.output)
