# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed
- Renamed the PyPI distribution from `agent-workspace` to `agent-workspace-py`.
  The shorter name is registered on PyPI to an unrelated project, so anyone
  following the previous `pip install agent-workspace` line installed that
  package instead of this worktree manager. Only the distribution name changed:
  the `agent_workspace` import package and the `agent-workspace` and `aws`
  console scripts are unchanged, and the GitHub repository name is unchanged

### Fixed
- `test_not_a_repo` no longer fails on checkouts whose temporary directory sits
  inside a Git repository, where `find_repo()` resolves to the enclosing
  repository instead of raising

## [Initial Release]

- Initial project release
