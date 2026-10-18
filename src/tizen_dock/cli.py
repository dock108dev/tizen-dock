"""Owner-operated Tizen customization tools. Device records stay in .local/."""

import argparse
import asyncio
import base64
import importlib
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import sys
import time
import uuid

from .contracts import PROFILE, ROOT, sha, verify_build
from .contracts import verify_backup as verify_snapshot


def private_dir(path):
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def save_json(path, value):
    private_dir(path.parent)
    path.write_text(json.dumps(value, indent=2) + "\n")
    path.chmod(0o600)


def config(path):
    c = json.loads(path.read_text())
    ipaddress.IPv4Address(c["host"])
    if c.get("callback_host"):
        ipaddress.IPv4Address(c["callback_host"])
    for key in ("sdb", "upstream", "payloads"):
        p = Path(c[key]).expanduser()
        c[key] = str((ROOT / p).resolve() if not p.is_absolute() else p.resolve())
    if not isinstance(c.get("model"), str) or not c["model"].strip():
        raise ValueError("Set model to the TV’s actual model name")
    return c


def adapter(c):
    sys.path.insert(0, str(Path(c["upstream"]) / "src"))
    os.environ["SDB"] = c["sdb"]
    return importlib.import_module("samsung_tv_root.sdb").SdbClient(
        Path(c["sdb"]), c["host"], timeout=15
    )


def sdk(c, command):
    result = adapter(c).capture(command, timeout=30).output
    match = re.search(r"\n\[exit:(\d+)\]\s*$", result)
    if not match or int(match[1]):
        raise RuntimeError("TV command failed; see local record: " + result[-500:])
    return result[: match.start()].rstrip()


def root(c, command):
    adapter(c)
    probe = importlib.import_module("samsung_tv_root.archive_root").probe
    result = asyncio.run(
        probe(
            c["host"],
            model=c["model"],
            callback_host=c.get("callback_host"),
            accept_timeout=15,
            command_timeout=45,
            commands=(command,),
            payloads=Path(c["payloads"]),
        )
    )
    log = ROOT / ".local/logs" / (str(time.time_ns()) + ".json")
    save_json(log, result)
    rows = result.get("commands", [])
    if len(rows) != 1 or rows[0]["exit_code"]:
        raise RuntimeError("Root command failed; private record: " + str(log))
    print("Private record:", log, file=sys.stderr)
    return rows[0]["stdout"]


def script_command(text):
    return "printf %s " + base64.b64encode(text.encode()).decode() + " | base64 -d | sh"


def restart(c):
    # The temporary root namespace cannot launch Home correctly on this TV.
    return sdk(
        c,
        "app_launcher -k com.samsung.tv.csfs -u 5001; "
        "app_launcher -s com.samsung.tv.csfs -u 5001; "
        "ps -eo pid,comm | grep csfs",
    )


def backup(c):
    stamp = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    dest = private_dir(ROOT / ".local/backups" / stamp)
    remote = "/home/owner/share/tmp/sdk_tools/tizen-dock-backup-" + stamp
    p = json.loads(PROFILE.read_text())
    files = [x["path"] for x in p["assemblies"]] + list(p["references"].values())
    files += [x["path"][:-4] + ".ni.dll" for x in p["assemblies"]]
    data = "/opt/usr/home/owner/apps_rw/com.samsung.tv.csfs/data"
    # Snapshot databases through SQLite and freeze Home only while archiving caches.
    text = f"""set -eu
mkdir -p {remote}
trap 'test -z "$pids" || kill -CONT $pids 2>/dev/null || true' EXIT
pids=""
sqlite3 /opt/dbspace/.pkgmgr_parser.db ".backup '{remote}/registry-global.db'"
sqlite3 /opt/dbspace/user/5001/.pkgmgr_parser.db ".backup '{remote}/registry-user.db'"
pids=$(ps -eo pid,comm | awk '$2 == "DN_sung.tv.csfs" {{print $1}}')
[ -z "$pids" ] || kill -STOP $pids
tar -czf {remote}.tar.gz -C / {" ".join(shlex.quote(f.lstrip("/")) for f in files)} {data.lstrip("/")} {remote.lstrip("/")}/registry-global.db {remote.lstrip("/")}/registry-user.db
"""
    text += f"stat -c %s {remote}.tar.gz\nsha256sum {remote}.tar.gz\n"
    meta = root(c, script_command(text)).strip().splitlines()
    size, expected = int(meta[-2]), meta[-1].split()[0]
    if size <= 0 or size > 64 * 1024 * 1024:
        raise ValueError("Unexpected archive size; remote snapshot retained")
    archive = dest / "snapshot.tar.gz"
    # Bound each root response below the agent's 1 MiB output limit.
    with archive.open("wb") as f:
        for index in range((size + 262143) // 262144):
            data = root(
                c,
                f"dd if={remote}.tar.gz bs=262144 skip={index} count=1 2>/dev/null | base64",
            )
            f.write(base64.b64decode(data, validate=False))
    archive.chmod(0o600)
    if archive.stat().st_size != size or sha(archive) != expected:
        raise RuntimeError("Backup integrity failed; remote snapshot retained")
    save_json(
        dest / "manifest.json",
        {
            "archive": archive.name,
            "sha256": expected,
            "bytes": size,
            "model": c["model"],
            "profile": sha(PROFILE),
            "note": "Current mounted view. Take before customization; not a full firmware image.",
        },
    )
    root(
        c,
        f"rm -f {remote}.tar.gz {remote}/registry-global.db {remote}/registry-user.db "
        f"{remote}/registry-global.db-journal {remote}/registry-user.db-journal; rmdir {remote}",
    )
    print("Verified private backup:", dest)


def app_change(c, app_id, enable):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", app_id):
        raise ValueError("Invalid app ID")
    # Durable intent record precedes mutation, including the authentic original state.
    state = root(
        c,
        f'''sqlite3 -readonly /opt/dbspace/.pkgmgr_parser.db "SELECT app_disable FROM package_app_info WHERE app_id='{app_id}';"''',
    ).strip()
    if state not in ("true", "false"):
        raise ValueError("App not found or ambiguous state")
    record = ROOT / ".local/changes" / (str(time.time_ns()) + ".json")
    save_json(
        record,
        {
            "app_id": app_id,
            "before": state,
            "requested": "false" if enable else "true",
            "complete": False,
        },
    )
    flag, expected = ("-A", "false") if enable else ("-D", "true")
    output = root(
        c,
        f"""set -e
pkgcmd {flag} -t app -n {shlex.quote(app_id)} --uid 5001
state=$(sqlite3 -readonly /opt/dbspace/.pkgmgr_parser.db "SELECT app_disable FROM package_app_info WHERE app_id='{app_id}';")
[ "$state" = {expected} ]
echo APP_STATE_VERIFIED
""",
    )
    value = json.loads(record.read_text())
    value["complete"] = True
    save_json(record, value)
    print(output.strip(), "Restore using the saved before state:", record)


def verify_backup(path):
    return verify_snapshot(path, PROFILE)


def restore_script():
    paths = [x["path"] for x in json.loads(PROFILE.read_text())["assemblies"]]
    return "set -eu\n" + "\n".join(
        f"nsenter -t 1 -m -- umount -l {shlex.quote(f)} || true"
        for path in paths
        for f in (path, path[:-4] + ".ni.dll")
    )


def apply(c, directory, backup_path):
    verify_backup(backup_path)
    manifest = verify_build(directory, PROFILE)
    client = adapter(c)
    for name in manifest["files"]:
        client.push(
            directory / name, PurePosixPath("/home/owner/share/tmp/sdk_tools") / name
        )
    print(root(c, script_command((directory / "apply.sh").read_text())).strip())
    try:
        print(restart(c))
    except Exception:
        print("Home launch failed: removing trial overlays", file=sys.stderr)
        root(c, script_command(restore_script()))
        print(restart(c))
        raise


def main():
    os.umask(0o077)
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=ROOT / "config.json")
    sp = ap.add_subparsers(dest="action", required=True)
    sp.add_parser("doctor")
    sp.add_parser("connect")
    sp.add_parser("status")
    sp.add_parser("backup")
    sp.add_parser("restore-menu")
    sp.add_parser("restart-home")
    for name in ("sdk", "root"):
        p = sp.add_parser(name)
        g = p.add_mutually_exclusive_group(required=True)
        g.add_argument("--command")
        g.add_argument("--script", type=Path)
    for name in ("disable-app", "enable-app"):
        p = sp.add_parser(name)
        p.add_argument("app_id")
        p.add_argument("--backup", type=Path, required=True)
    p = sp.add_parser("apply")
    p.add_argument("--build", type=Path, required=True)
    p.add_argument("--backup", type=Path, required=True)
    for name in ("install-startup", "startup-status"):
        p = sp.add_parser(name)
        p.add_argument("--package", type=Path, required=True)
    args = ap.parse_args()
    try:
        c = config(args.config)
        if args.action == "doctor":
            print("Configuration valid; TV untouched.")
            for key in ("sdb", "upstream", "payloads"):
                if not Path(c[key]).exists():
                    raise ValueError("Missing " + key + ": " + c[key])
            print("Local dependency paths exist. Use connect to check the TV.")
        elif args.action == "connect":
            client = adapter(c)
            client.connect()
            client.require_device()
            print("Connected to configured TV")
        elif args.action == "status":
            print(
                sdk(c, "uname -m; cat /etc/tizen-release; ps -eo pid,comm | grep csfs")
            )
        elif args.action == "backup":
            backup(c)
        elif args.action in ("sdk", "root"):
            command = (
                args.command
                if args.command
                else script_command(args.script.read_text())
            )
            output = sdk(c, command) if args.action == "sdk" else root(c, command)
            print(output, end="" if output.endswith("\n") else "\n")
        elif args.action in ("disable-app", "enable-app"):
            verify_backup(args.backup)
            app_change(c, args.app_id, args.action == "enable-app")
        elif args.action == "apply":
            apply(c, args.build, args.backup)
        elif args.action == "install-startup":
            from .startup import install

            install(c, args.package)
        elif args.action == "startup-status":
            from .startup import status

            print(json.dumps(status(c, args.package), indent=2))
        elif args.action == "restore-menu":
            print(root(c, script_command(restore_script())))
            print(restart(c))
        elif args.action == "restart-home":
            print(restart(c))
    except (Exception, KeyboardInterrupt) as exc:
        print("Stopped:", exc, file=sys.stderr)
        raise SystemExit(1)
