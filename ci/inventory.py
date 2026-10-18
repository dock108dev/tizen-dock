"""Inventory the locked CI environment without guessing absent license metadata."""

import importlib.metadata
import json
from pathlib import Path
import re
import sys


def inventory(lock):
    rows = []
    for name, version in re.findall(
        r"^([A-Za-z0-9_.-]+)==([^\s]+)", lock.read_text(), re.MULTILINE
    ):
        dist = importlib.metadata.distribution(name)
        if dist.version != version:
            raise ValueError("Installed version differs from lock: " + name)
        metadata = dist.metadata
        classifiers = metadata.get_all("Classifier") or []
        license_value = metadata.get("License-Expression") or next(
            (c for c in classifiers if c.startswith("License ::")), None
        )
        rows.append(
            {"name": name, "version": version, "license_metadata": license_value}
        )
    if not rows:
        raise ValueError("Empty dependency inventory")
    return rows


if __name__ == "__main__":
    print(json.dumps(inventory(Path(sys.argv[1])), indent=2))
