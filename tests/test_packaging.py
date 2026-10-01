"""Guard the PyPI distribution name against collisions with other packages.

The `agent-workspace` name on PyPI belongs to an unrelated project (a restricted
file-operation workspace, Apache-2.0, backed by a Rust core). Anyone following
this README's install command would have installed that other project instead of
this worktree manager. The distribution therefore ships as `agent-workspace-py`.

These tests fail if the install line regresses to the colliding short name, or if
`project.name` stops carrying the `-py` suffix that keeps it unambiguous.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
README = REPO_ROOT / "README.md"

# The PyPI name owned by someone else. Never advertise this as an install target.
TAKEN_ON_PYPI = "agent-workspace"

# The distribution name this project owns.
EXPECTED_DISTRIBUTION = "agent-workspace-py"

# Install forms that legitimately refer to the source tree, not to PyPI.
_LOCAL_INSTALL = re.compile(r"^(?:\.|git\+|\.git/|/|\.venv)")


def _distribution_name() -> str:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["name"]


def _pip_install_targets(text: str) -> list[str]:
    """Return the package names `pip install` lines in *text* would fetch."""
    targets = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(("pip install ", "pip3 install ", "uv tool install ")):
            continue
        for token in stripped.split()[2:]:
            # Skip flags and anything that points at a path, VCS URL or extras.
            if token.startswith("-") or "[" in token:
                continue
            if _LOCAL_INSTALL.match(token):
                continue
            targets.append(token.split("==")[0].split(">=")[0].split("<")[0])
    return targets


@pytest.fixture(scope="module")
def readme_text() -> str:
    return README.read_text(encoding="utf-8")


def test_distribution_name_carries_py_suffix() -> None:
    """`project.name` must stay disambiguated from the name taken on PyPI."""
    name = _distribution_name()
    assert name != TAKEN_ON_PYPI, (
        f"project.name is {TAKEN_ON_PYPI!r}, which is registered to another "
        "project on PyPI; use a name that is actually free"
    )
    assert name == EXPECTED_DISTRIBUTION
    assert name.endswith("-py"), f"expected a '-py' suffix, got {name!r}"


def test_readme_never_offers_the_taken_name(readme_text: str) -> None:
    """No install line may resolve to the name owned by another project."""
    assert TAKEN_ON_PYPI not in _pip_install_targets(readme_text), (
        f"README offers `pip install {TAKEN_ON_PYPI}`, which installs a different "
        "project from PyPI; advertise the -py distribution instead"
    )


def test_readme_install_target_matches_distribution(readme_text: str) -> None:
    """Every PyPI install target must equal `project.name`, not a stale name."""
    targets = _pip_install_targets(readme_text)
    assert targets, "expected the README to contain at least one pip install line"
    assert set(targets) == {_distribution_name()}, (
        f"README installs {sorted(set(targets))} but the distribution is "
        f"{_distribution_name()!r}"
    )


def test_module_and_console_script_are_unchanged() -> None:
    """A distribution rename must not touch the import name or the CLI name."""
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    scripts = project["scripts"]
    assert scripts["agent-workspace"] == "agent_workspace.cli:app"
    assert (REPO_ROOT / "agent_workspace" / "__init__.py").is_file()


def test_github_release_is_not_advertised_before_first_publish(readme_text: str) -> None:
    """No PyPI badge may exist while the distribution is still unpublished.

    `img.shields.io/pypi/v/agent-workspace-py` renders "not found" until the first
    upload lands, so the badge is added after publishing, not before.
    """
    assert "img.shields.io/pypi/" not in readme_text, (
        "README carries a PyPI badge but the distribution has not been published; "
        "shields.io renders it as 'not found'"
    )