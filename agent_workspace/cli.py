"""CLI for agent-workspace."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from . import __version__
from .models import AgentType, WorkspaceStatus
from .state import list_snapshots, save_snapshot, take_snapshot
from .workspace import (
    WorkspaceError,
    create_workspace,
    destroy_workspace,
    find_repo,
    get_workspace,
    list_workspaces,
    prune_workspaces,
)

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Manage isolated workspaces for parallel AI agents.",
)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"agent-workspace {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-V", callback=version_callback, is_eager=True
    ),
) -> None:
    """agent-workspace — Git worktree manager for parallel AI agents."""


@app.command()
def create(
    task: str = typer.Argument(..., help="Task description for the agent"),
    agent: AgentType = typer.Option(AgentType.CLAUDE, "--agent", "-a", help="Agent type"),
    base: Optional[str] = typer.Option(None, "--base", "-b", help="Base branch (auto-detect if omitted)"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Repository path (default: cwd)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Create a new isolated workspace for an AI agent."""
    try:
        repo_path = find_repo(repo) if repo else find_repo()
        ws = create_workspace(repo_path, task=task, agent=agent, base_branch=base)
        if json_output:
            typer.echo(json.dumps(ws.to_dict(), indent=2, default=str))
        else:
            typer.echo(f"✅ Created workspace {ws.id}")
            typer.echo(f"   Agent: {ws.agent.value}")
            typer.echo(f"   Task:  {ws.task}")
            typer.echo(f"   Branch: {ws.branch}")
            typer.echo(f"   Path:  {ws.worktree_path}")
    except WorkspaceError as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def list(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Repository path"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """List all workspaces for a repository."""
    try:
        repo_path = find_repo(repo) if repo else find_repo()
        workspaces = list_workspaces(repo_path)
        if not workspaces:
            typer.echo("No workspaces found.")
            return
        if json_output:
            typer.echo(json.dumps([w.to_dict() for w in workspaces], indent=2, default=str))
        else:
            for ws in workspaces:
                status_icon = {
                    WorkspaceStatus.ACTIVE: "🟢",
                    WorkspaceStatus.IDLE: "🟡",
                    WorkspaceStatus.MERGED: "🔵",
                    WorkspaceStatus.ABANDONED: "🔴",
                }.get(ws.status, "⚪")
                typer.echo(
                    f"{status_icon} {ws.id}  {ws.agent.value:8s}  {ws.branch:40s}  {ws.task}"
                )
    except WorkspaceError as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def destroy(
    ws_id: str = typer.Argument(..., help="Workspace ID to destroy"),
    keep_branch: bool = typer.Option(False, "--keep-branch", help="Keep the branch"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Repository path"),
) -> None:
    """Destroy a workspace and optionally its branch."""
    try:
        repo_path = find_repo(repo) if repo else find_repo()
        destroy_workspace(repo_path, ws_id, remove_branch=not keep_branch)
        typer.echo(f"✅ Destroyed workspace {ws_id}")
    except WorkspaceError as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def snapshot(
    ws_id: str = typer.Argument(..., help="Workspace ID to snapshot"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Repository path"),
) -> None:
    """Take a snapshot of a workspace's current state."""
    try:
        repo_path = find_repo(repo) if repo else find_repo()
        snap = take_snapshot(repo_path, ws_id)
        path = save_snapshot(repo_path, snap)
        typer.echo(f"✅ Snapshot saved: {path}")
        if snap.git_status.get("porcelain"):
            typer.echo(f"   Changes: {len(snap.git_status['porcelain'])} files")
        if snap.untracked_files:
            typer.echo(f"   Untracked: {len(snap.untracked_files)} files")
    except (WorkspaceError, ValueError) as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def snapshots(
    ws_id: str = typer.Argument(..., help="Workspace ID"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Repository path"),
) -> None:
    """List snapshots for a workspace."""
    try:
        repo_path = find_repo(repo) if repo else find_repo()
        snaps = list_snapshots(repo_path, ws_id)
        if not snaps:
            typer.echo("No snapshots found.")
            return
        for s in snaps:
            typer.echo(f"  {s.name}")
    except WorkspaceError as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def prune(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Repository path"),
) -> None:
    """Prune stale worktree entries."""
    try:
        repo_path = find_repo(repo) if repo else find_repo()
        pruned = prune_workspaces(repo_path)
        if pruned:
            typer.echo(f"✅ Pruned {len(pruned)} stale worktree(s)")
            for p in pruned:
                typer.echo(f"   {p}")
        else:
            typer.echo("Nothing to prune.")
    except WorkspaceError as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
