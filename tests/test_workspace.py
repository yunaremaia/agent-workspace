"""Tests for agent-workspace."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_workspace.models import AgentType, Workspace, WorkspaceStatus
from agent_workspace.workspace import (
    WorkspaceError,
    create_workspace,
    destroy_workspace,
    find_repo,
    get_default_branch,
    list_workspaces,
)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository for testing."""
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
    # Create an initial commit
    (repo / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True
    )
    return repo


class TestFindRepo:
    def test_find_repo_from_cwd(self, git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(git_repo)
        assert find_repo() == git_repo

    def test_find_repo_subdir(self, git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        subdir = git_repo / "src" / "module"
        subdir.mkdir(parents=True)
        monkeypatch.chdir(subdir)
        assert find_repo() == git_repo

    def test_not_a_repo(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        with pytest.raises(WorkspaceError, match="Not a git repository"):
            find_repo()


class TestGetDefaultBranch:
    def test_main(self, git_repo: Path) -> None:
        # Default branch is master or main depending on git config
        branch = get_default_branch(git_repo)
        assert branch in ("main", "master")


class TestCreateWorkspace:
    def test_create_workspace(self, git_repo: Path) -> None:
        ws = create_workspace(git_repo, task="Fix bug #123", agent=AgentType.CLAUDE)
        assert ws.id
        assert ws.agent == AgentType.CLAUDE
        assert ws.task == "Fix bug #123"
        assert ws.worktree_path.exists()
        assert (ws.worktree_path / ".git").exists() or (ws.worktree_path / ".git").is_file()



    def test_list_workspaces(self, git_repo: Path) -> None:
        create_workspace(git_repo, task="Task 1")
        create_workspace(git_repo, task="Task 2")
        workspaces = list_workspaces(git_repo)
        assert len(workspaces) == 2

    def test_destroy_workspace(self, git_repo: Path) -> None:
        ws = create_workspace(git_repo, task="Temp task")
        ws_id = ws.id
        destroy_workspace(git_repo, ws_id)
        workspaces = list_workspaces(git_repo)
        assert all(w.id != ws_id for w in workspaces)

    def test_destroy_nonexistent_raises(self, git_repo: Path) -> None:
        with pytest.raises(WorkspaceError, match="not found"):
            destroy_workspace(git_repo, "nonexistent")


class TestWorkspaceModel:
    def test_to_dict(self) -> None:
        ws = Workspace(
            id="abc12345",
            agent=AgentType.CLAUDE,
            task="test",
            branch="agent/claude/test-20260912",
            base_branch="main",
            worktree_path=Path("/tmp/test"),
            repo_path=Path("/tmp/repo"),
        )
        d = ws.to_dict()
        assert d["id"] == "abc12345"
        assert d["agent"] == "claude"
        assert d["status"] == "active"
