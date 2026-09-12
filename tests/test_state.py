"""Tests for state management and snapshots."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_workspace.models import AgentType
from agent_workspace.state import (
    list_snapshots,
    load_snapshot,
    save_snapshot,
    take_snapshot,
)
from agent_workspace.workspace import create_workspace, find_repo


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository."""
    repo = tmp_path / "test-repo"
    repo.mkdir()
    import subprocess
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo, check=True, capture_output=True,
    )
    (repo / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True
    )
    return repo


def test_take_snapshot(git_repo: Path) -> None:
    ws = create_workspace(git_repo, task="test snapshot")
    snap = take_snapshot(git_repo, ws.id)
    assert snap.workspace_id == ws.id
    assert snap.git_status is not None
    assert isinstance(snap.git_log, list)


def test_save_and_load_snapshot(git_repo: Path) -> None:
    ws = create_workspace(git_repo, task="test save")
    snap = take_snapshot(git_repo, ws.id)
    path = save_snapshot(git_repo, snap)
    assert path.exists()

    loaded = load_snapshot(path)
    assert loaded.workspace_id == ws.id
    assert loaded.id == snap.id


def test_list_snapshots(git_repo: Path) -> None:
    ws = create_workspace(git_repo, task="test list")
    snap = take_snapshot(git_repo, ws.id)
    save_snapshot(git_repo, snap)

    snaps = list_snapshots(git_repo, ws.id)
    assert len(snaps) == 1


def test_list_snapshots_empty(git_repo: Path) -> None:
    snaps = list_snapshots(git_repo, "nonexistent")
    assert snaps == []
