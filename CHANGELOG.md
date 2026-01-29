# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.6] - 2026-01-29

### Added

- **reporting:** Add GitHub PR markdown renderer with trends and diff detail names
- **cli:** Add GitHub report format with snapshot-based trends summary
- **action:** Add composite GitHub Action for Pacta architecture review
- **action:** Add target_dir input to control scan root

### Documentation

- Add GitHub Action integration guide and document github output format
- **ci-integration:** Add GitHub Action comment example and document target_dir input

### Miscellaneous

- Update changelog for v0.0.5
- **ci:** Simplify changelog PR workflow
- **cli:** Remove unused __future__ annotations import from _trends.py
- **ci:** Update test-action workflow to use simple-layered-app example
- **examples:** Track pacta snapshots for simple-layered-app
- **gitignore:** Remove test-action GitHub workflow
- **examples/simple-layered-app:** Remove pacta snapshot objects and latest ref

### Ci

- Add workflow to test action and support local pacta install option

## [0.0.5] - 2026-01-27

### Added

- **cli:** Add `check` command to evaluate rules against saved snapshots
- **cli:** Document new `pacta check` command and two-step snapshot workflow

### Changed

- Format argparse argument and remove unused import

### Documentation

- Add new example docs pages and example projects (layered, hexagonal, legacy migration)
- Update CLI and examples for snapshot save/check workflow

### Fixed

- **check:** Update existing snapshot object in-place and save optional extra ref
- **ci:** Use --force-with-lease when pushing changelog updates

### Testing

- **cli:** Reformat assertion for save refs call args

## [0.0.4] - 2026-01-26

### Documentation

- Refresh README and getting started with architecture snapshot/history narrative

### Miscellaneous

- **ci:** Create PR for changelog updates instead of pushing to main

## [0.0.3] - 2026-01-25

### Added

- **cli:** Show human-readable violation explanations in text output
- **cli:** Add history commands and content-addressed snapshot store
- **cli:** Add `history trends` with ASCII charts and optional matplotlib export
- **docs:** Document history trends command and add chart example
- **model:** Add optional layer name field and load from spec

### Documentation

- **contributing:** Expand contributing guide with project structure and dev workflow
- **readme:** Reposition as architecture governance tool and add demo gif
- Add changelog and expand MkDocs documentation

### Miscellaneous

- **license:** Switch to Apache-2.0 and bump version to 0.0.2
- Apply formatting and typing tweaks in history output and tests
- **cli:** Remove redundant module docstrings and __future__ imports from chart modules
- **dev:** Add pytest-cov to dev dependencies

## [0.0.2] - 2026-01-23

### Miscellaneous

- **license:** Switch to Apache-2.0 and bump version to 0.0.2

## [0.0.1] - 2026-01-23

[0.0.6]: https://github.com/pacta-dev/pacta-cli/compare/v0.0.5...v0.0.6
[0.0.5]: https://github.com/pacta-dev/pacta-cli/compare/v0.0.4...v0.0.5
[0.0.4]: https://github.com/pacta-dev/pacta-cli/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/pacta-dev/pacta-cli/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/pacta-dev/pacta-cli/compare/v0.0.1...v0.0.2

