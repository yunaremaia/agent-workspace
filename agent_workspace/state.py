"""State persistence and snapshots for agent-workspace."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import Snapshot


def take_snapshot(repo_path: Path, ws_id: str) -> Snapshot:
    """Capture current state of a workspace."""
    from .workspace import get_workspace
    ws = get_workspace(repo_path, ws_id)
    if ws is None:
        raise ValueError(f"Workspace '{ws_id}' not found")

    # Git status
    result = subprocess.run(
        ["git", "-C", str(ws.worktree_path), "status", "--porcelain"],
        capture_output=True, text=True, check=False,
    )
    status_lines = result.stdout.strip().splitlines() if result.stdout else []

    # Git log
    result = subprocess.run(
        ["git", "-C", str(ws.worktree_path), "log", "--oneline", "-20"],
        capture_output=True, text=True, check=False,
    )
    log_lines = result.stdout.strip().splitlines() if result.stdout else []

    return Snapshot(
        workspace_id=ws_id,
        git_status={"porcelain": status_lines},
        git_log=log_lines,
        untracked_files=[l[3:] for l in status_lines if l.startswith("?? ")],
    )


def save_snapshot(repo_path: Path, snapshot: Snapshot) -> Path:
    """Persist snapshot to disk. Returns path to saved file."""
    snapshots_dir = repo_path / ".agent-workspaces" / "snapshots" / snapshot.workspace_id
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    ts = snapshot.timestamp.strftime("%Y%m%d-%H%M%S")
    path = snapshots_dir / f"{snapshot.id}-{ts}.json"
    path.write_text(json.dumps(snapshot.model_dump(), indent=2, default=str))
    return path


def list_snapshots(repo_path: Path, ws_id: str) -> list[Path]:
    """List snapshot files for a workspace, newest first."""
    snapshots_dir = repo_path / ".agent-workspaces" / "snapshots" / ws_id
    if not snapshots_dir.exists():
        return []
    return sorted(snapshots_dir.glob("*.json"), reverse=True)


def load_snapshot(path: Path) -> Snapshot:
    """Load a snapshot from disk."""
    data = json.loads(path.read_text())
    return Snapshot(**data)
