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

[0.0.5]: https://github.com/pacta-dev/pacta-cli/compare/v0.0.4...v0.0.5

