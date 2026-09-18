# agent-workspace

Git worktree manager for parallel AI agents.

## Why

When running multiple AI coding agents (Claude Code, Codex, OpenCode) in parallel, each needs an isolated workspace. Git worktrees are the standard primitive, but managing 5-10 of them manually is error-prone:

- Tracking which agent is in which workspace
- Cleaning up orphaned worktrees
- Saving/restoring context between sessions
- Running hooks before/after agent sessions

`agent-workspace` gives you a single CLI to create, list, snapshot, and destroy workspaces — with state persistence and a JSON output mode for automation.

## Install

```bash
pip install agent-workspace
```

Or from source:

```bash
pip install git+https://github.com/yunaremaia/agent-workspace.git
```

## Docker

The repository includes a minimal container with Python, Git, and
`agent-workspace` installed. Build it with:

```bash
docker build -t agent-workspace .
```

The Compose setup mounts the current repository at `/workspace` and keeps the
workspace registry and worktrees in a named volume:

```bash
docker compose run --rm agent-workspace list
docker compose run --rm agent-workspace create "Fix authentication bug" --agent claude
```

To use a direct Docker command instead, mount a Git repository and set the
working directory:

```bash
docker run --rm -it \
  -v "$PWD:/workspace" \
  -w /workspace \
  agent-workspace list
```

The mounted directory must be a Git repository. Git credentials and SSH keys
are intentionally not copied into the image; mount them explicitly when a
workflow needs access to a private remote.

## Quick Start

```bash
# Create a workspace for Claude Code
agent-workspace create "Fix authentication bug" --agent claude

# List all workspaces
agent-workspace list

# Take a snapshot of current state
agent-workspace snapshot <workspace-id>

# Destroy when done
agent-workspace destroy <workspace-id>
```

## Commands

| Command   | Description                          |
|-----------|--------------------------------------|
| `create`  | Create a new isolated workspace      |
| `list`    | List all workspaces                  |
| `destroy` | Tear down a workspace                |
| `snapshot`| Capture current state                |
| `snapshots`| List saved snapshots                |
| `prune`   | Remove stale worktree entries        |

## JSON Output

All commands support `--json` for scripting:

```bash
agent-workspace list --json | jq '.[] | select(.status=="active")'
```

## State Persistence

Workspaces are tracked in `.agent-workspaces/registry.json` inside your repository. Snapshots are stored in `.agent-workspaces/snapshots/<id>/`.

## Comparison with Worktrunk

| Feature | Worktrunk | agent-workspace |
|----------------------|-----------|-----------------|
| Language             | Rust      | Python          |
| Git worktree         | ✅        | ✅              |
| State snapshots      | ❌        | ✅              |
| Session registry     | ❌        | ✅              |
| JSON output          | ❌        | ✅              |
| Hooks system         | ❌        | ✅ (planned)    |
| driftcheck integration| ❌       | ✅ (planned)    |

## License

MIT
