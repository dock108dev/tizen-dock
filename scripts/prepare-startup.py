"""Prepare a private, device-authorized v4 startup widget from the current build."""

import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tizen_dock.contracts import ROOT
from tizen_dock.startup import reapply_script

os.umask(0o077)

ap = argparse.ArgumentParser(description=__doc__)
for name in (
    "build",
    "backup",
    "payloads",
    "certificates",
    "device-id",
    "output",
):
    ap.add_argument("--" + name, type=Path, required=True)
a = ap.parse_args()
if not a.output.resolve().is_relative_to((ROOT / ".local").resolve()):
    raise SystemExit("Startup output must remain under ignored .local/")
script = reapply_script(a.build, a.backup)
if a.output.exists():
    raise SystemExit("Output already exists; preserve the previous package")
a.output.mkdir(parents=True, mode=0o700)
shutil.copytree(ROOT / "startup", a.output / "widget")
widget = a.output / "widget"
(widget / "service/reapply.sh").write_text(script)
key = secrets.token_hex(32)
(a.output / "status-token").write_text(key)
(a.output / "status-token").chmod(0o600)
(widget / "service/status-key.json").write_text(json.dumps({"key": key}))
page = widget / "app.js"
page.write_text(page.read_text().replace("__STATUS_KEY__", key))
(widget / "payload").mkdir()
for name in ("SamsungTvArchiveRoot", "SamsungTvRootAgent"):
    for suffix in (".dll", ".deps.json", ".runtimeconfig.json"):
        shutil.copyfile(
            a.payloads / (name + suffix), widget / "payload" / (name + suffix)
        )
subprocess.run(
    [
        "node",
        str(ROOT / "scripts/sign-startup.cjs"),
        str(a.output.resolve()),
        str(a.certificates.resolve()),
        str(a.device_id.resolve()),
    ],
    check=True,
)
print("Private startup package:", a.output)
