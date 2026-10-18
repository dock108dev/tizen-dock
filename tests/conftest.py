"""Offline tests may not open network connections or read owner configuration."""

from pathlib import Path
import socket
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "ci"))


@pytest.fixture(autouse=True)
def no_network(monkeypatch, tmp_path):
    def denied(*args, **kwargs):
        raise AssertionError("Network access forbidden in synthetic tests")

    from tizen_dock import cli

    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "adapter", denied)
    monkeypatch.setattr(cli, "root", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
