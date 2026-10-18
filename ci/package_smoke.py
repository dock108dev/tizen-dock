"""Fresh public-source export and editable install. Does not read owner state."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import tarfile
import json

from check_source import ROOT, public_files


def run(args, **kwargs):
    subprocess.run(args, check=True, timeout=120, **kwargs)


def smoke(output):
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="tizen-export-") as temporary:
        root = Path(temporary)
        export = root / "source"
        for relative in public_files():
            source = ROOT / relative
            if source.is_symlink():
                raise ValueError("Source export refuses symlinks")
            target = export / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        run(
            [
                sys.executable,
                "-m",
                "build",
                "--no-isolation",
                "--sdist",
                "--outdir",
                str(root / "dist"),
                str(export),
            ]
        )
        # Install the actual source distribution, so omitted tracked inputs fail here.
        with tarfile.open(next((root / "dist").glob("*.tar.gz"))) as archive:
            archive.extractall(root / "unpacked", filter="data")
        export = next((root / "unpacked").iterdir())
        for name in (
            "scripts/build-overlays.py",
            "profiles/tu7000-2301.json",
            "global.json",
            "patchers/dock-v4/Patcher.csproj",
            "ci/requirements.txt",
            "src/tizen_dock/contracts.py",
            "src/tizen_dock/startup.py",
            "scripts/prepare-startup.py",
            "scripts/sign-startup.cjs",
            "startup/config.xml",
            "startup/app.js",
            "startup/app.css",
            ".prettierrc.json",
            "ci/suites/startup.py",
            "startup/service/main.js",
            "startup/service/platform.js",
            "startup/VETRO-LICENSE",
            "startup/ROOT-RESEARCH-LICENSE",
            "package-lock.json",
            "tests/startup-ci.test.cjs",
        ):
            if not (export / name).is_file():
                raise ValueError("Missing source distribution input: " + name)
        run([sys.executable, "-m", "venv", str(root / "env")])
        python = root / "env/bin/python"
        run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--require-hashes",
                "-r",
                str(export / "ci/requirements.txt"),
            ]
        )
        run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--no-build-isolation",
                "-e",
                str(export),
            ]
        )
        inventory = subprocess.run(
            [
                str(python),
                str(export / "ci/inventory.py"),
                str(export / "ci/requirements.txt"),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output.with_name("inventory.json").write_text(inventory.stdout)
        run([str(root / "env/bin/tizen-dock"), "--help"], cwd=root)
        run([str(python), str(export / "ci/run.py"), "--help"], cwd=root)
        paths = {name: str(root / name) for name in ("sdb", "upstream", "payloads")}
        for name in paths.values():
            Path(name).mkdir()
        config = root / "synthetic.json"
        config.write_text(
            json.dumps({"host": "192.0.2.1", "model": "Synthetic-CI-TV", **paths})
        )
        run(
            [str(python), "-m", "tizen_dock", "--config", str(config), "doctor"],
            cwd=root,
        )
        sizes = {p.name: p.stat().st_size for p in (root / "dist").iterdir()}
        output.write_text(
            json.dumps(
                {
                    "bytes": sizes,
                    "elapsed_seconds": time.monotonic() - started,
                    "scope": "public source export, offline help and synthetic doctor; no device",
                    "baseline": None,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    smoke(Path(sys.argv[1]))
