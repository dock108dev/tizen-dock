"""Shared source-input identity and artifact validation for all entry points."""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Profile contents identify the input set in backup and build manifests.
PROFILE = ROOT / "profiles/tu7000-2301.json"
REMOTE = "/home/owner/share/tizen-dock/menu-overlay"


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(262144), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_artifact_name(name):
    if not isinstance(name, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", name
    ):
        raise ValueError("Unsafe artifact filename")
    return name


def verify_backup(path, profile=PROFILE):
    if (path / "manifest.json").is_symlink() or (path / "snapshot.tar.gz").is_symlink():
        raise ValueError("Symlink in backup")
    manifest = json.loads((path / "manifest.json").read_text())
    if manifest.get("profile") != sha(profile):
        raise ValueError("Backup profile mismatch")
    if manifest.get("archive") != "snapshot.tar.gz":
        raise ValueError("Unexpected archive name")
    archive = path / manifest["archive"]
    if sha(archive) != manifest["sha256"]:
        raise ValueError("Backup checksum mismatch")
    return archive


def verify_build(directory, profile=PROFILE):
    if (directory / "manifest.json").is_symlink():
        raise ValueError("Symlink in build manifest")
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest.get("profile_sha256") != sha(profile):
        raise ValueError("Build profile mismatch")
    required = {"apply.sh"} | {
        item["name"] + ".dll" for item in json.loads(profile.read_text())["assemblies"]
    }
    files = manifest.get("files")
    if not isinstance(files, dict) or not required.issubset(files):
        raise ValueError("Build file mismatch: incomplete manifest")
    for name, expected in files.items():
        validate_artifact_name(name)
        if (
            Path(name).name != name
            or (directory / name).is_symlink()
            or not (directory / name).is_file()
            or sha(directory / name) != expected
        ):
            raise ValueError("Build file mismatch: " + name)
    return manifest
