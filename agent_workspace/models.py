"""Data models for agent-workspace."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Supported AI agent types."""
    CLAUDE = "claude"
    CODEX = "codex"
    OPENCODE = "opcode"
    CURSOR = "cursor"
    CUSTOM = "custom"


class WorkspaceStatus(str, Enum):
    """Status of a workspace."""
    ACTIVE = "active"
    IDLE = "idle"
    MERGED = "merged"
    ABANDONED = "abandoned"


class Workspace(BaseModel):
    """Represents an isolated workspace for an AI agent."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent: AgentType
    task: str
    branch: str
    base_branch: str
    worktree_path: Path
    repo_path: Path
    status: WorkspaceStatus = WorkspaceStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable dict."""
        return {
            "id": self.id,
            "agent": self.agent.value,
            "task": self.task,
            "branch": self.branch,
            "base_branch": self.base_branch,
            "worktree_path": str(self.worktree_path),
            "repo_path": str(self.repo_path),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


class Snapshot(BaseModel):
    """State snapshot of a workspace."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    workspace_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    git_status: dict[str, Any] = Field(default_factory=dict)
    git_log: list[str] = Field(default_factory=list)
    untracked_files: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
