import hashlib
import io
import json
import subprocess
from unittest.mock import Mock
import tarfile
import zipfile

import pytest
from tizen_dock import cli, startup
from tizen_dock.contracts import sha


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    profile = tmp_path / "profile.json"
    assemblies = [
        {
            "name": name,
            "path": "/system/" + name + ".dll",
            "sha256": hashlib.sha256(b"original").hexdigest(),
        }
        for name in ("Home", "Feed", "Ads", "Renderer")
    ]
    profile.write_text(json.dumps({"assemblies": assemblies}))
    monkeypatch.setattr(startup, "PROFILE", profile)
    build = tmp_path / "build"
    build.mkdir()
    for name in [
        "apply.sh",
        *(x["name"] + ".dll" for x in assemblies),
        "focus-ring-v4.png",
    ]:
        (build / name).write_bytes(b"overlay")
    manifest = {
        "renderer_version": "v4",
        "profile_sha256": sha(profile),
        "files": {p.name: sha(p) for p in build.iterdir()},
    }
    (build / "manifest.json").write_text(json.dumps(manifest))
    backup = tmp_path / "backup"
    backup.mkdir()
    archive = backup / "snapshot.tar.gz"
    with tarfile.open(archive, "w:gz") as target:
        for item in assemblies:
            for suffix, data in ((".dll", b"original"), (".ni.dll", b"native")):
                member = tarfile.TarInfo("system/" + item["name"] + suffix)
                member.size = len(data)
                target.addfile(member, io.BytesIO(data))
    (backup / "manifest.json").write_text(
        json.dumps(
            {"archive": archive.name, "sha256": sha(archive), "profile": sha(profile)}
        )
    )
    return build, backup


def test_startup_uses_build_hashes_and_checks_all_files_before_mounts(bundle):
    script = startup.reapply_script(*bundle)
    assert script.index("PAYLOAD_CHANGED_ABORT") < script.index("mount --bind")
    assert script.rindex("FIRMWARE_CHANGED_ABORT") < script.index("mount --bind")
    assert script.count("mount --bind") == 8
    assert "focus-ring-v4.png" in script
    assert "trap - EXIT" in script
    subprocess.run(["sh", "-n"], input=script, text=True, check=True)


def test_startup_rejects_changed_build(bundle):
    (bundle[0] / "Renderer.dll").write_bytes(b"changed")
    with pytest.raises(ValueError, match="Build file mismatch"):
        startup.reapply_script(*bundle)


def test_startup_rejects_older_build(bundle):
    path = bundle[0] / "manifest.json"
    value = json.loads(path.read_text())
    value["renderer_version"] = "v3"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="current v4"):
        startup.reapply_script(*bundle)


def test_startup_rejects_changed_backup(bundle):
    (bundle[1] / "snapshot.tar.gz").write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        startup.reapply_script(*bundle)


def test_install_rejects_package_for_another_tv_before_push(tmp_path, monkeypatch):
    with zipfile.ZipFile(tmp_path / "startup.wgt", "w") as widget:
        widget.writestr("author-signature.xml", "synthetic")
        widget.writestr("signature1.xml", "synthetic")
    (tmp_path / "device-profile.xml").write_text("synthetic")
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "device_sha256": "0" * 64,
                "files": {
                    name: sha(tmp_path / name)
                    for name in ("startup.wgt", "device-profile.xml")
                },
            }
        )
    )
    client = Mock()
    client.run.return_value.stdout = "synthetic-current-tv"
    monkeypatch.setattr(cli, "adapter", lambda c: client)
    with pytest.raises(ValueError, match="different TV"):
        startup.install({}, tmp_path)
    client.push.assert_not_called()


@pytest.mark.parametrize(
    "name", ["$(id).png", "x`id`.png", 'x".png', "x\n.png", "../x.png", "x\\y.png"]
)
def test_build_rejects_unsafe_filenames_before_any_device_access(bundle, name):
    from tizen_dock.contracts import verify_build

    build, _ = bundle
    path = build / "manifest.json"
    value = json.loads(path.read_text())
    value["files"][name] = "0" * 64
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="Unsafe artifact filename"):
        verify_build(build, startup.PROFILE)


def test_backup_rejects_symlink_archive(bundle, tmp_path):
    from tizen_dock.contracts import verify_backup

    _, backup = bundle
    target = tmp_path / "outside.tar.gz"
    archive = backup / "snapshot.tar.gz"
    archive.rename(target)
    archive.symlink_to(target)
    with pytest.raises(ValueError, match="Symlink"):
        verify_backup(backup, startup.PROFILE)


def test_status_does_not_use_proxies_or_follow_redirects(tmp_path, monkeypatch):
    import urllib.request
    import urllib.error

    (tmp_path / "status-token").write_text("a" * 64)
    handlers = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, maximum):
            assert maximum == 65537
            return b'{"state":"active"}'

    class Opener:
        def open(self, request, timeout):
            assert request.full_url == "http://192.0.2.50:8098/status"
            assert timeout == 4
            return Response()

    def build(*args):
        handlers.extend(args)
        return Opener()

    monkeypatch.setattr(urllib.request, "build_opener", build)
    assert startup.status({"host": "192.0.2.50"}, tmp_path)["state"] == "active"
    assert handlers[0].proxies == {}
    with pytest.raises(urllib.error.HTTPError, match="redirects are forbidden"):
        handlers[1].redirect_request(
            urllib.request.Request("http://192.0.2.50:8098/status"),
            None,
            302,
            "",
            {},
            "https://untrusted.example",
        )


def test_invalid_status_key_never_builds_request(tmp_path, monkeypatch):
    import urllib.request

    (tmp_path / "status-token").write_text("invalid")
    build = Mock()
    monkeypatch.setattr(urllib.request, "build_opener", build)
    with pytest.raises(ValueError, match="Invalid private status key"):
        startup.status({"host": "192.0.2.50"}, tmp_path)
    build.assert_not_called()


def test_install_hands_access_to_local_tv_and_preserves_previous_host(
    tmp_path, monkeypatch
):
    with zipfile.ZipFile(tmp_path / "startup.wgt", "w") as widget:
        widget.writestr("author-signature.xml", "synthetic")
        widget.writestr("signature1.xml", "synthetic")
    (tmp_path / "device-profile.xml").write_text("synthetic")
    identity = "synthetic-tv"
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "device_sha256": hashlib.sha256(identity.encode()).hexdigest(),
                "files": {
                    name: sha(tmp_path / name)
                    for name in ("startup.wgt", "device-profile.xml")
                },
            }
        )
    )
    client = Mock()
    client.run.return_value.stdout = identity
    client.run.return_value.stderr = ""
    monkeypatch.setattr(cli, "adapter", lambda c: client)
    sdk = Mock(
        side_effect=[
            "db/sdk/develop/ip, value = 192.0.2.10 (String)",
            "",
            "launched",
            "db/sdk/develop/ip, value = 127.0.0.1 (String)",
        ]
    )
    monkeypatch.setattr(cli, "sdk", sdk)
    startup.install({}, tmp_path)
    assert "192.0.2.10" in (tmp_path / "developer-host-before.json").read_text()
    assert sdk.call_args.args[1].startswith("vconftool set -f")
    assert client.run.call_args.args[0] == ("disconnect", client.serial)
