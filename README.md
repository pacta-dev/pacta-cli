<p align="center">
  <img src="assets/logo-ascii.png" alt="Pacta" width="400">
</p>

<p align="center">
  <strong>Architecture Testing & Architecture-as-Code</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/pacta/">PyPI</a> •
  <a href="https://akhundmurad.github.io/pacta/">Docs</a> •
  <a href="https://github.com/akhundMurad/pacta/issues">Issues</a>
</p>

<p align="center">
  <a href="https://pypi.org/project/pacta/"><img src="https://img.shields.io/pypi/v/pacta?color=green" alt="PyPI - Version"></a>
  <a href="https://pypi.org/project/pacta/"><img src="https://img.shields.io/pypi/pyversions/pacta?color=green" alt="PyPI - Python Version"></a>
  <img src="https://img.shields.io/github/license/akhundMurad/pacta" alt="GitHub License">
</p>

---

> **Warning:** Experimental. Expect breaking changes.

Pacta enforces architectural rules in your codebase. Define layers, set boundaries, catch violations in CI.

Supported languages:
- Python
- Java (coming soon)
- Go (coming soon)
- C# (coming soon)

```bash
pip install pacta
pacta scan . --model architecture.yml --rules rules.pacta.yml
```

## Why?

Codebases rot. The "clean architecture" you designed becomes spaghetti after a few quarters. Pacta catches violations early — in PRs, not post-mortems.

## What it does

- **Static analysis** — parses Python AST, builds import graph
- **Layer enforcement** — domain can't import from infra, etc.
- **Baseline mode** — fail only on *new* violations, not legacy debt
- **Snapshots** — version your architecture like code
- **History tracking** — view architecture evolution over time

## Quick example

Define your layers in `architecture.yml`:

```yaml
version: 1
system:
  id: myapp
  name: My App

containers:
  backend:
    code:
      roots: [src]
      layers:
        domain:
          patterns: [src/domain/**]
        infra:
          patterns: [src/infra/**]
```

Add rules in `rules.pacta.yml`:

```yaml
rule:
  id: no_domain_to_infra
  name: Domain cannot depend on Infrastructure
  severity: error
  target: dependency
  when:
    all:
      - from.layer == domain
      - to.layer == infra
  action: forbid
  message: Domain layer must not import from Infrastructure
```

Run it:

```bash
$ pacta scan . --model architecture.yml --rules rules.pacta.yml

✗ 2 violations (2 error) [2 new]
  ✗ ERROR [no_domain_to_infra] Domain cannot depend on Infrastructure @ src/domain/user.py:3:1
    status: new
    Domain layer must not import from Infrastructure
```

## Baseline workflow

Got legacy violations? Save a baseline and only fail on new ones:

```bash
# Save current state
pacta scan . --model architecture.yml --rules rules.pacta.yml --save-ref baseline

# Later, in CI — fail only on new violations
pacta scan . --model architecture.yml --rules rules.pacta.yml --baseline baseline
```

## History tracking

Every scan creates a content-addressed snapshot. View your architecture evolution:

```bash
# View timeline
$ pacta history show --last 5

Architecture Timeline (5 entries)
============================================================
a1b2c3d4  2025-01-22  abc1234  main    42 nodes  87 edges  2 violations (latest)
e5f6g7h8  2025-01-20  def5678  main    42 nodes  85 edges  4 violations
...

# Export for external tools
pacta history export --format json > history.json
```

## Docs

- [CLI Reference](https://akhundmurad.github.io/pacta/cli/)
- [Architecture Model](https://akhundmurad.github.io/pacta/architecture/)
- [Rules DSL](https://akhundmurad.github.io/pacta/rules/)

## Roadmap (short)

- [x] Open-source CLI and analysis engine
- [x] Content-addressed snapshots with history tracking
- [ ] Architecture visualization (Mermaid, D2)
- [ ] Health metrics (drift score, instability)
- [ ] Proprietary hosted service with:
  - Cross-repository insights
  - Historical trend analysis
  - Team-level governance and reporting

## License

Apache-2.0. See [LICENSE](./LICENSE).
