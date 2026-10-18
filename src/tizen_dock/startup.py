"""Generate startup restoration from the deployed build, never a second payload list."""

import json
import hashlib
import re
import shlex
import tarfile

from .contracts import PROFILE, REMOTE, sha, verify_backup, verify_build


def reapply_script(build, backup):
    manifest = verify_build(build, PROFILE)
    if manifest.get("renderer_version") != "v4":
        raise ValueError("Startup requires the current v4 build")
    archive = verify_backup(backup, PROFILE)
    profile = json.loads(PROFILE.read_text())
    quote = shlex.quote
    checks = ["#!/bin/sh", "set -eu", "changed=0", 'mounted=""']
    mounts = []
    with tarfile.open(archive, "r:gz") as snapshot:
        for name, digest in manifest["files"].items():
            if name == "apply.sh":
                continue
            checks.append(
                f'[ "$(nsenter -t 1 -m -- sha256sum {quote(REMOTE + "/" + name)} | cut -d " " -f 1)" = {digest} ] || {{ echo PAYLOAD_CHANGED_ABORT; exit 1; }}'
            )
        for item in profile["assemblies"]:
            payload = REMOTE + "/" + item["name"] + ".dll"
            expected = manifest["files"][item["name"] + ".dll"]
            for target in (item["path"], item["path"][:-4] + ".ni.dll"):
                member = snapshot.getmember(target.lstrip("/"))
                if not member.isfile():
                    raise ValueError("Unexpected backup member")
                original = hashlib.sha256(
                    snapshot.extractfile(member).read()
                ).hexdigest()
                if (
                    target.endswith(".dll")
                    and not target.endswith(".ni.dll")
                    and original != item["sha256"]
                ):
                    raise ValueError("Backup is not pristine: " + item["name"])
                checks += [
                    f'current=$(nsenter -t 1 -m -- sha256sum {quote(target)} | cut -d " " -f 1)',
                    f'case "$current" in {original}|{expected}) ;; *) echo FIRMWARE_CHANGED_ABORT; exit 1;; esac',
                ]
                mounts += [
                    f'current=$(nsenter -t 1 -m -- sha256sum {quote(target)} | cut -d " " -f 1)',
                    f'if [ "$current" != {expected} ]; then',
                    f" nsenter -t 1 -m -- mount --bind {quote(payload)} {quote(target)}",
                    f' mounted="{target} $mounted"',
                    " changed=1",
                    "fi",
                ]
    checks.append(
        "trap 'for target in $mounted; do nsenter -t 1 -m -- umount -l \"$target\" || true; done' EXIT"
    )
    return "\n".join(
        checks
        + mounts
        + [
            "trap - EXIT",
            'if [ "$changed" = 1 ]; then echo DOCK_REAPPLIED; else echo DOCK_ALREADY_PRESENT; fi',
            "",
        ]
    )


def install(c, package):
    """Install only a signed package bound to the explicitly selected TV."""
    from pathlib import PurePosixPath
    import zipfile
    from . import cli

    manifest = json.loads((package / "package.json").read_text())
    expected_names = {"startup.wgt", "device-profile.xml"}
    if set(manifest.get("files", {})) != expected_names:
        raise ValueError("Incomplete startup package manifest")
    for name, digest in manifest["files"].items():
        if (package / name).is_symlink() or sha(package / name) != digest:
            raise ValueError("Startup package changed")
    with zipfile.ZipFile(package / "startup.wgt") as widget:
        if not {"author-signature.xml", "signature1.xml"}.issubset(widget.namelist()):
            raise ValueError("Startup widget must be signed")
    client = cli.adapter(c)
    client.connect()
    client.require_device()
    identity = client.run(
        ("-s", client.serial, "shell", "0", "getduid"), check=True
    ).stdout.strip()
    if (
        not identity
        or hashlib.sha256(identity.encode()).hexdigest() != manifest["device_sha256"]
    ):
        raise ValueError("Startup package belongs to a different TV")
    before = cli.sdk(c, "vconftool get db/sdk/develop/ip")
    cli.save_json(
        package / "developer-host-before.json",
        {"original": before, "startup_host": "127.0.0.1"},
    )
    cli.sdk(c, "mkdir -p /home/owner/share/tizen-dock-boot")
    for name in sorted(expected_names):
        client.push(
            package / name, PurePosixPath("/home/owner/share/tmp/sdk_tools") / name
        )
    result = client.run(
        (
            "-s",
            client.serial,
            "shell",
            "0",
            "vd_appinstall",
            "tizendock0",
            "/home/owner/share/tmp/sdk_tools/startup.wgt",
        ),
        check=True,
        timeout=180,
    )
    cli.save_json(
        package / "install-result.json",
        {"stdout": result.stdout, "stderr": result.stderr},
    )
    # A transport exit alone is insufficient; require the actual application to launch.
    print(cli.sdk(c, "app_launcher -s tizendock0.app -u 5001"))
    value = cli.sdk(
        c,
        "vconftool set -f -t string db/sdk/develop/ip 127.0.0.1; vconftool get db/sdk/develop/ip",
    )
    if "value = 127.0.0.1 (String)" not in value:
        raise RuntimeError(
            "Startup host configuration was not verified; original setting retained in package records"
        )
    # This SDB service accepts one active client. Hand ownership to the TV helper.
    client.run(("disconnect", client.serial), check=True)


def status(c, package):
    import urllib.request
    import urllib.error

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise urllib.error.HTTPError(
                req.full_url, code, "Status redirects are forbidden", headers, fp
            )

    key = (package / "status-token").read_text().strip()
    if not re.fullmatch(r"[a-f0-9]{64}", key):
        raise ValueError("Invalid private status key")
    request = urllib.request.Request(
        "http://" + c["host"] + ":8098/status", headers={"X-Tizen-Dock-Status": key}
    )
    # Tokens are scoped to this TV: never use environment proxies or follow redirects.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=4) as response:
        data = response.read(65537)
    if len(data) > 65536:
        raise ValueError("Oversized startup status response")
    return json.loads(data)
