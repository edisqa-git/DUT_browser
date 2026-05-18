from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.api.snapshot_api import list_snapshots, _safe_name
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# _safe_name validation
# ---------------------------------------------------------------------------

def test_safe_name_rejects_path_traversal():
    with pytest.raises(HTTPException) as exc_info:
        _safe_name("../evil.jsonl")
    assert exc_info.value.status_code == 400


def test_safe_name_rejects_non_jsonl():
    with pytest.raises(HTTPException) as exc_info:
        _safe_name("snapshots.log")
    assert exc_info.value.status_code == 400


def test_safe_name_accepts_valid():
    assert _safe_name("snapshots.jsonl") == "snapshots.jsonl"


# ---------------------------------------------------------------------------
# list_snapshots
# ---------------------------------------------------------------------------

def test_list_snapshots_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("app.api.snapshot_api.LOG_DIR", tmp_path)
    result = list_snapshots()
    assert result == {"files": []}


def test_list_snapshots_returns_file_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr("app.api.snapshot_api.LOG_DIR", tmp_path)

    snapshot = {"test_count": 1, "device_ts": "2026-05-18 10:00:00", "cpu": {}, "wifi_clients": {}}
    jsonl = tmp_path / "snapshots.jsonl"
    jsonl.write_text(json.dumps(snapshot) + "\n", encoding="utf-8")

    result = list_snapshots()
    assert len(result["files"]) == 1
    info = result["files"][0]
    assert info["name"] == "snapshots.jsonl"
    assert info["frames"] == 1
    assert info["size_bytes"] > 0


def test_list_snapshots_ignores_non_jsonl(tmp_path, monkeypatch):
    monkeypatch.setattr("app.api.snapshot_api.LOG_DIR", tmp_path)
    (tmp_path / "session.log").write_text("hello\n")
    result = list_snapshots()
    assert result == {"files": []}


def test_list_snapshots_counts_frames_correctly(tmp_path, monkeypatch):
    monkeypatch.setattr("app.api.snapshot_api.LOG_DIR", tmp_path)

    snapshot = {"test_count": 1, "device_ts": "2026-05-18 10:00:00", "cpu": {}, "wifi_clients": {}}
    jsonl = tmp_path / "snapshots.jsonl"
    jsonl.write_text("\n".join(json.dumps(snapshot) for _ in range(5)) + "\n", encoding="utf-8")

    result = list_snapshots()
    assert result["files"][0]["frames"] == 5
