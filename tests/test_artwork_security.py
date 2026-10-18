import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "build_overlays_security", ROOT / "scripts/build-overlays.py"
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


@pytest.mark.parametrize(
    "name", ["$(id).png", 'x".png', "x`id`.png", "x\n.png", "../x.png"]
)
def test_artwork_names_fail_before_build_or_output_creation(tmp_path, name):
    mapping = tmp_path / "artwork.json"
    mapping.write_text(json.dumps({"App": name}))
    with (
        patch.object(builder.subprocess, "run") as run,
        pytest.raises(ValueError, match="Unsafe artifact filename"),
    ):
        builder.build(tmp_path / "originals", tmp_path / "output", mapping)
    run.assert_not_called()
    assert not (tmp_path / "output").exists()


def test_artwork_rejects_symlinks_and_mismatched_dimensions(tmp_path):
    source = tmp_path / "art.png"
    source.write_bytes(b"not a PNG")
    mapping = tmp_path / "artwork.json"
    mapping.write_text(json.dumps({"App": source.name}))
    with pytest.raises(ValueError, match="512"):
        builder.load_artwork(mapping)
    source.unlink()
    source.symlink_to(tmp_path / "outside")
    with pytest.raises(ValueError, match="Invalid artwork file"):
        builder.load_artwork(mapping)


def test_startup_generation_refuses_public_output_before_reading_inputs(tmp_path):
    import subprocess
    import sys

    args = [sys.executable, str(ROOT / "scripts/prepare-startup.py")]
    for name in (
        "build",
        "backup",
        "payloads",
        "certificates",
        "device-id",
        "output",
    ):
        args += ["--" + name, str(tmp_path / name)]
    result = subprocess.run(args, capture_output=True, text=True, timeout=10)
    assert result.returncode != 0
    assert "under ignored .local/" in result.stderr
    assert not (tmp_path / "output").exists()
