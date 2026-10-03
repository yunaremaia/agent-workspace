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

# Every command prefix that installs this project, whatever the source.
_INSTALL_PREFIXES = ("pip install ", "pip3 install ", "uv tool install ")

# The README states outright that the upload has not landed. Keyed off the wording
# so the two cannot drift apart silently.
_UNPUBLISHED_NOTICE = "does not resolve yet"


def _distribution_name() -> str:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["name"]


def _install_commands(text: str) -> list[list[str]]:
    """Return the argument lists of every install command in *text*."""
    commands = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(_INSTALL_PREFIXES):
            continue
        commands.append(stripped.split()[2:])
    return commands


def _pip_install_targets(text: str) -> list[str]:
    """Return the package names `pip install` lines in *text* would fetch."""
    targets = []
    for tokens in _install_commands(text):
        for token in tokens:
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
    """Any PyPI install target must equal `project.name`, not a stale name.

    Before the first upload lands the README legitimately offers only a VCS
    source, and there is then no PyPI target to check. Asserting a target must
    exist made that state a build failure instead of a supported one, so the
    invariant is applied per-target: zero targets is fine, wrong ones are not.
    """
    targets = set(_pip_install_targets(readme_text))
    assert targets <= {_distribution_name()}, (
        f"README installs {sorted(targets)} but the distribution is "
        f"{_distribution_name()!r}"
    )


def test_readme_offers_an_install_route(readme_text: str) -> None:
    """A source install or a PyPI install must be documented, whichever applies.

    This is the guard the PyPI-target test gave up: the README must never end up
    with no way to install at all, which is how this test file rotted silently
    when the install line moved from PyPI to Git.
    """
    assert _install_commands(readme_text), (
        "README documents no install command; a reader cannot get this package"
    )


def test_pypi_notice_matches_the_install_lines(readme_text: str) -> None:
    """The 'not on PyPI yet' notice must agree with the install lines.

    Once the upload lands the notice has to go, or the README tells readers to
    install from Git while implying a published release exists.
    """
    advertised = _UNPUBLISHED_NOTICE in readme_text
    if advertised:
        assert not _pip_install_targets(readme_text), (
            "README still warns that the upload has not landed, yet advertises "
            f"a PyPI target {sorted(set(_pip_install_targets(readme_text)))}"
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