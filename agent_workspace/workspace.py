"""Core workspace manager for agent-workspace."""
from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import AgentType, Workspace, WorkspaceStatus


class WorkspaceError(Exception):
    """Raised when a workspace operation fails."""


def _git(repo_path: Path, *args: str, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    """Run a git command and return the result."""
    cmd = ["git", "-C", str(repo_path), *args]
    return subprocess.run(cmd, check=check, capture_output=capture, text=True)


def _git_worktree(repo_path: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git worktree subcommand."""
    return _git(repo_path, "worktree", *args, check=check, capture=True)


def find_repo(path: Optional[Path] = None) -> Path:
    """Walk up from *path* until a .git directory is found."""
    current = Path.cwd() if path is None else path.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    raise WorkspaceError("Not a git repository (or any of the parent directories)")


def get_default_branch(repo_path: Path) -> str:
    """Detect the default branch of the repository."""
    # First, try the local branch list
    result = _git(repo_path, "branch", "--format=%(refname:short)", check=False)
    if result.returncode == 0 and result.stdout:
        branches = [b.strip() for b in result.stdout.strip().splitlines()]
        # Prefer main over master
        if "main" in branches:
            return "main"
        if "master" in branches:
            return "master"
        if branches:
            return branches[0]
    # Fallback to remote HEAD
    result = _git(repo_path, "symbolic-ref", "refs/remotes/origin/HEAD", check=False)
    if result.returncode == 0:
        return result.stdout.strip().split("/")[-1]
    raise WorkspaceError("Could not determine default branch")


def create_workspace(
    repo_path: Path,
    task: str,
    agent: AgentType = AgentType.CLAUDE,
    base_branch: Optional[str] = None,
    branch_prefix: str = "agent",
) -> Workspace:
    """Create a new isolated workspace using git worktree.

    The worktree lives at ``repo_path/.agent-workspaces/<id>/``.
    """
    repo_path = repo_path.resolve()

    # Determine base branch
    if base_branch is None:
        base_branch = get_default_branch(repo_path)

    # Generate a branch name
    slug = task.lower().replace(" ", "-").replace("/", "-")[:40]
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    branch = f"{branch_prefix}/{agent.value}/{slug}-{ts}"

    # Create the worktree directory under the repo
    worktree_base = repo_path / ".agent-workspaces"
    worktree_base.mkdir(exist_ok=True)

    # Use a short ID for the directory name
    import uuid
    ws_id = str(uuid.uuid4())[:8]
    worktree_path = worktree_base / ws_id
    worktree_path.mkdir()

    # Create the worktree
    result = _git_worktree(
        repo_path, "add", "-b", branch, str(worktree_path), base_branch, check=False
    )
    if result.returncode != 0:
        # Clean up
        worktree_path.rmdir()
        raise WorkspaceError(f"Failed to create worktree: {result.stderr.strip()}")

    ws = Workspace(
        id=ws_id,
        agent=agent,
        task=task,
        branch=branch,
        base_branch=base_branch,
        worktree_path=worktree_path,
        repo_path=repo_path,
    )
    _save_registry(repo_path, ws)
    return ws


def list_workspaces(repo_path: Path) -> list[Workspace]:
    """Return all workspaces known to this repository."""
    registry_path = repo_path / ".agent-workspaces" / "registry.json"
    if not registry_path.exists():
        return []
    import json
    data = json.loads(registry_path.read_text())
    workspaces = []
    for entry in data:
        entry["worktree_path"] = Path(entry["worktree_path"])
        entry["repo_path"] = Path(entry["repo_path"])
        workspaces.append(Workspace(**entry))
    return workspaces


def get_workspace(repo_path: Path, ws_id: str) -> Optional[Workspace]:
    """Look up a workspace by its ID."""
    for ws in list_workspaces(repo_path):
        if ws.id == ws_id:
            return ws
    return None


def destroy_workspace(repo_path: Path, ws_id: str, remove_branch: bool = True) -> None:
    """Tear down a workspace and optionally its branch."""
    ws = get_workspace(repo_path, ws_id)
    if ws is None:
        raise WorkspaceError(f"Workspace '{ws_id}' not found")

    # Remove the worktree
    result = _git_worktree(repo_path, "remove", str(ws.worktree_path), "--force", check=False)
    if result.returncode != 0:
        raise WorkspaceError(f"Failed to remove worktree: {result.stderr.strip()}")

    # Remove the branch
    if remove_branch:
        _git(repo_path, "branch", "-D", ws.branch, check=False)

    ws.status = WorkspaceStatus.ABANDONED
    _remove_from_registry(repo_path, ws_id)


def prune_workspaces(repo_path: Path) -> list[str]:
    """Remove worktree entries whose directories no longer exist."""
    result = _git_worktree(repo_path, "prune", check=False)
    pruned: list[str] = []
    if result.returncode == 0 and result.stdout:
        for line in result.stdout.strip().splitlines():
            pruned.append(line.strip())
    return pruned


def _save_registry(repo_path: Path, ws: Workspace) -> None:
    """Persist workspace metadata to registry.json."""
    import json
    registry_path = repo_path / ".agent-workspaces" / "registry.json"
    if registry_path.exists():
        data = json.loads(registry_path.read_text())
    else:
        data = []
    data.append(ws.to_dict())
    registry_path.write_text(json.dumps(data, indent=2, default=str))


def _remove_from_registry(repo_path: Path, ws_id: str) -> None:
    """Remove a workspace entry from the registry."""
    import json
    registry_path = repo_path / ".agent-workspaces" / "registry.json"
    if not registry_path.exists():
        return
    data = json.loads(registry_path.read_text())
    data = [e for e in data if e.get("id") != ws_id]
    registry_path.write_text(json.dumps(data, indent=2, default=str))
