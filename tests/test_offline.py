import base64
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tarfile
from unittest.mock import Mock, patch
import zlib

import pytest
from tizen_dock import cli

ROOT = Path(__file__).resolve().parents[1]


def snapshot(directory):
    (directory / "snapshot.tar.gz").write_bytes(b"synthetic")
    (directory / "manifest.json").write_text(
        json.dumps(
            {
                "archive": "snapshot.tar.gz",
                "sha256": cli.sha(directory / "snapshot.tar.gz"),
                "profile": cli.sha(cli.PROFILE),
            }
        )
    )


def overlay(directory):
    files = ["apply.sh"] + [
        x["name"] + ".dll" for x in json.loads(cli.PROFILE.read_text())["assemblies"]
    ]
    for name in files:
        (directory / name).write_bytes(b"synthetic")
    manifest = {
        "profile_sha256": cli.sha(cli.PROFILE),
        "files": {name: cli.sha(directory / name) for name in files},
    }
    (directory / "manifest.json").write_text(json.dumps(manifest))
    return manifest


@pytest.mark.parametrize(
    "output", ["missing marker", "output\n[exit:1]\n", "output\n[exit:12]\n"]
)
def test_sdk_rejects_missing_or_failed_status(output):
    client = Mock()
    client.capture.return_value.output = output
    with patch.object(cli, "adapter", return_value=client), pytest.raises(RuntimeError):
        cli.sdk({}, "synthetic command")


def test_sdk_success_returns_only_output():
    client = Mock()
    client.capture.return_value.output = "synthetic\n[exit:0]\n"
    with patch.object(cli, "adapter", return_value=client):
        assert cli.sdk({}, "synthetic") == "synthetic"


@pytest.mark.parametrize("app_id", ["x' OR 1=1", "x\nshutdown", "x y", "$(x)", ""])
def test_app_id_rejection_never_connects(app_id):
    with patch.object(cli, "root") as root, pytest.raises(ValueError):
        cli.app_change({}, app_id, False)
    root.assert_not_called()


def test_completed_app_change_keeps_authentic_original(tmp_path):
    with (
        patch.object(cli, "ROOT", tmp_path),
        patch.object(cli, "root", side_effect=["true\n", "APP_STATE_VERIFIED\n"]),
    ):
        cli.app_change({}, "Synthetic.App", True)
    record = json.loads(next((tmp_path / ".local/changes").glob("*.json")).read_text())
    assert record == {
        "app_id": "Synthetic.App",
        "before": "true",
        "requested": "false",
        "complete": True,
    }


def test_apply_recovery_removes_overlay_and_restarts(tmp_path):
    backup = tmp_path / "backup"
    backup.mkdir()
    snapshot(backup)
    build = tmp_path / "build"
    build.mkdir()
    manifest = overlay(build)
    client = Mock()
    with (
        patch.object(cli, "adapter", return_value=client),
        patch.object(cli, "root", return_value="synthetic") as root,
        patch.object(
            cli, "restart", side_effect=[RuntimeError("launch failed"), "restored"]
        ) as restart,
    ):
        with pytest.raises(RuntimeError, match="launch failed"):
            cli.apply({}, build, backup)
    assert client.push.call_count == len(manifest["files"])
    assert restart.call_count == 2
    rollback = base64.b64decode(root.call_args.args[1].split()[2]).decode()
    assert rollback == cli.restore_script()


@pytest.mark.parametrize(
    "files", [{}, {"unlisted.dll": "0" * 64}, {"apply.sh": "0" * 64}]
)
def test_incomplete_build_never_contacts_tv(tmp_path, files):
    snapshot(tmp_path)
    build = tmp_path / "build"
    build.mkdir()
    (build / "manifest.json").write_text(
        json.dumps({"profile_sha256": cli.sha(cli.PROFILE), "files": files})
    )
    with (
        patch.object(cli, "adapter") as adapter,
        pytest.raises(ValueError, match="Build file mismatch"),
    ):
        cli.apply({}, build, tmp_path)
    adapter.assert_not_called()


def test_build_cannot_follow_symlink_outside_directory(tmp_path):
    snapshot(tmp_path)
    build = tmp_path / "build"
    build.mkdir()
    overlay(build)
    source = build / "apply.sh"
    source.unlink()
    outside = tmp_path / "outside.sh"
    outside.write_bytes(b"synthetic")
    source.symlink_to(outside)
    with patch.object(cli, "adapter") as adapter, pytest.raises(ValueError):
        cli.apply({}, build, tmp_path)
    adapter.assert_not_called()


def execute(script, *args):
    return subprocess.run(
        [sys.executable, str(ROOT / script), *map(str, args)],
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.parametrize("framing", ["bad\nx\nEOFCOBA\n", "1\nx\nmissing\n"])
def test_cache_editor_refuses_unknown_framing(tmp_path, framing):
    source = tmp_path / "input"
    source.mkdir()
    (source / ".appLayerCache.1").write_text(framing)
    result = execute(
        "scripts/edit-home-cache.py",
        "--input",
        source,
        "--output",
        tmp_path / "out",
        "--remove",
        "d/webapp@SYNTHETIC",
    )
    assert result.returncode != 0
    assert not (tmp_path / "out/apply.sh").exists()
    assert (source / ".appLayerCache.1").read_text() == framing


def test_extraction_only_emits_allowlisted_regular_inputs(tmp_path):
    profile = json.loads(cli.PROFILE.read_text())
    paths = [item["path"].lstrip("/") for item in profile["assemblies"]] + [
        path.lstrip("/") for path in profile["references"].values()
    ]
    archive = tmp_path / "snapshot.tar.gz"
    with tarfile.open(archive, "w:gz") as target:
        for path in [*paths, "../../must-not-extract"]:
            entry = tarfile.TarInfo(path)
            entry.size = 9
            target.addfile(entry, io.BytesIO(b"synthetic"))
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "archive": archive.name,
                "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "profile": cli.sha(cli.PROFILE),
            }
        )
    )
    output = tmp_path / "out"
    result = execute(
        "scripts/extract-originals.py", "--backup", tmp_path, "--output", output
    )
    assert result.returncode == 0, result.stderr
    assert len(list(output.iterdir())) == len(paths)
    assert all(path.read_bytes() == b"synthetic" for path in output.iterdir())
    assert not (tmp_path / "must-not-extract").exists()


def read_png(path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    chunks = []
    offset = 8
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        checksum = struct.unpack(
            ">I", data[offset + 8 + length : offset + 12 + length]
        )[0]
        assert zlib.crc32(kind + payload) & 0xFFFFFFFF == checksum
        chunks.append((kind, payload))
        offset += length + 12
    width, height = struct.unpack(">II", chunks[0][1][:8])
    raw = zlib.decompress(b"".join(d for kind, d in chunks if kind == b"IDAT"))
    assert len(raw) == height * (1 + 4 * width)
    return width, height, raw


@pytest.mark.parametrize(
    "script,filename,dimensions",
    [
        ("scripts/draw-assets.py", "compact-dock-background-v3.png", (1600, 250)),
        ("patchers/dock-v4/make-assets.py", "focus-ring-v4.png", (512, 512)),
    ],
)
def test_generated_artwork_dimensions_crc_and_transparency(
    tmp_path, script, filename, dimensions
):
    assert execute(script, tmp_path).returncode == 0
    width, height, raw = read_png(tmp_path / filename)
    assert (width, height) == dimensions
    assert raw[4] == 0  # Corner alpha: no opaque rectangular crop.
    assert any(
        raw[row * (width * 4 + 1) + 4 * (width // 2) + 4] for row in range(height)
    )


def test_backup_uses_bounded_chunks_and_records_verified_integrity(tmp_path):
    data = b"synthetic" * 33000
    digest = hashlib.sha256(data).hexdigest()
    chunks = [
        base64.b64encode(data[i : i + 262144]).decode()
        for i in range(0, len(data), 262144)
    ]
    with (
        patch.object(cli, "ROOT", tmp_path),
        patch.object(
            cli, "root", side_effect=[f"{len(data)}\n{digest}  snapshot\n", *chunks, ""]
        ) as root,
    ):
        cli.backup({"model": "UN65TU7000FXZA"})
    directory = next((tmp_path / ".local/backups").iterdir())
    assert (directory / "snapshot.tar.gz").read_bytes() == data
    manifest = json.loads((directory / "manifest.json").read_text())
    assert manifest["sha256"] == digest
    assert manifest["bytes"] == len(data)
    assert root.call_count == len(chunks) + 2
    assert root.call_args.args[1].startswith("rm -f ")
    cleanup = root.call_args.args[1]
    assert "registry-global.db-journal" in cleanup
    assert "registry-user.db-journal" in cleanup
    assert "*" not in cleanup  # Only this backup's named scratch files are removed.
    assert (directory / "snapshot.tar.gz").stat().st_mode & 0o777 == 0o600


def test_corrupt_backup_download_keeps_remote_snapshot(tmp_path):
    data = b"synthetic"
    with (
        patch.object(cli, "ROOT", tmp_path),
        patch.object(
            cli,
            "root",
            side_effect=[
                f"{len(data)}\n{'0' * 64} snapshot\n",
                base64.b64encode(data).decode(),
            ],
        ) as root,
    ):
        with pytest.raises(RuntimeError, match="integrity"):
            cli.backup({"model": "UN65TU7000FXZA"})
    assert root.call_count == 2
    assert not list((tmp_path / ".local/backups").glob("*/manifest.json"))


def test_changed_complete_build_hash_never_contacts_tv(tmp_path):
    snapshot(tmp_path)
    build = tmp_path / "build"
    build.mkdir()
    overlay(build)
    (build / "apply.sh").write_text("changed after manifest")
    with (
        patch.object(cli, "adapter") as adapter,
        pytest.raises(ValueError, match="Build file mismatch"),
    ):
        cli.apply({}, build, tmp_path)
    adapter.assert_not_called()


@pytest.mark.parametrize("model", ["UN65TU7000FXZA", "UN65AU8000FXZA", "Another-TV"])
def test_model_name_is_metadata_not_compatibility_policy(tmp_path, model):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "host": "192.0.2.50",
                "model": model,
                "sdb": "tools/sdb",
                "upstream": "upstream",
                "payloads": "payloads",
            }
        )
    )
    assert cli.config(path)["model"] == model


def test_connect_does_not_report_success_without_registered_device(capsys):
    client = Mock()
    client.require_device.side_effect = RuntimeError("No registered device")
    with (
        patch.object(cli, "config", return_value={}),
        patch.object(cli, "adapter", return_value=client),
        patch.object(sys, "argv", ["tizen-dock", "connect"]),
        pytest.raises(SystemExit),
    ):
        cli.main()
    client.connect.assert_called_once()
    client.require_device.assert_called_once()
    assert "Connected to configured TV" not in capsys.readouterr().out


def test_extraction_and_apply_reject_same_mismatched_backup(tmp_path):
    snapshot(tmp_path)
    path = tmp_path / "manifest.json"
    value = json.loads(path.read_text())
    value["profile"] = "0" * 64
    path.write_text(json.dumps(value))
    output = tmp_path / "out"
    result = execute(
        "scripts/extract-originals.py", "--backup", tmp_path, "--output", output
    )
    assert result.returncode != 0
    assert "Backup profile mismatch" in result.stderr
    assert not output.exists()
    with (
        patch.object(cli, "adapter") as adapter,
        pytest.raises(ValueError, match="profile mismatch"),
    ):
        cli.apply({}, tmp_path / "missing-build", tmp_path)
    adapter.assert_not_called()
