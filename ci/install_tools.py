"""Install only checksum-pinned public CI binaries; never execute download scripts."""

import argparse
import hashlib
import io
from pathlib import Path
import platform
import tarfile
import urllib.request

TOOLS = {
    "shellcheck": (
        "koalaman/shellcheck",
        "0.11.0",
        {
            "Linux-x86_64": (
                "shellcheck-v0.11.0.linux.x86_64.tar.gz",
                "b7af85e41cc99489dcc21d66c6d5f3685138f06d34651e6d34b42ec6d54fe6f6",
            ),
            "Darwin-arm64": (
                "shellcheck-v0.11.0.darwin.aarch64.tar.gz",
                "339b930feb1ea764467013cc1f72d09cd6b869ebf1013296ba9055ab2ffbd26f",
            ),
        },
    ),
    "actionlint": (
        "rhysd/actionlint",
        "1.7.12",
        {
            "Linux-x86_64": (
                "actionlint_1.7.12_linux_amd64.tar.gz",
                "8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8",
            ),
            "Darwin-arm64": (
                "actionlint_1.7.12_darwin_arm64.tar.gz",
                "aba9ced2dee8d27fecca3dc7feb1a7f9a52caefa1eb46f3271ea66b6e0e6953f",
            ),
        },
    ),
    "gitleaks": (
        "gitleaks/gitleaks",
        "8.30.1",
        {
            "Linux-x86_64": (
                "gitleaks_8.30.1_linux_x64.tar.gz",
                "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb",
            ),
            "Darwin-arm64": (
                "gitleaks_8.30.1_darwin_arm64.tar.gz",
                "b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5",
            ),
        },
    ),
    "osv-scanner": (
        "google/osv-scanner",
        "2.7.0",
        {
            "Linux-x86_64": (
                "osv-scanner_linux_amd64",
                "160c6253e2922e9e0a6a9771c5c4c40a4b3c6090b34a3cdd5e80c96cc2e4218b",
            ),
            "Darwin-arm64": (
                "osv-scanner_darwin_arm64",
                "d4926ef8da134332543be276dff157e4c170f99ad91fc48e89448a8816bdf70b",
            ),
        },
    ),
}


def install(name, destination):
    repo, version, platforms = TOOLS[name]
    filename, checksum = platforms[f"{platform.system()}-{platform.machine()}"]
    url = f"https://github.com/{repo}/releases/download/v{version}/{filename}"
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read(100 * 1024 * 1024)
    if hashlib.sha256(data).hexdigest() != checksum:
        raise ValueError(f"{name}: release checksum mismatch")
    if filename.endswith(".tar.gz"):
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            member = archive.getmember(
                f"shellcheck-v{version}/shellcheck" if name == "shellcheck" else name
            )
            if not member.isfile():
                raise ValueError("Expected regular executable")
            data = archive.extractfile(member).read()
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / name
    target.write_bytes(data)
    target.chmod(0o755)
    print(f"{name} {version}: verified SHA256")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("tools", choices=TOOLS, nargs="+")
    args = parser.parse_args()
    for tool in args.tools:
        install(tool, args.destination)
