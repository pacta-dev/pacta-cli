<p align="center">
  <img src="https://raw.githubusercontent.com/akhundMurad/pacta/main/assets/logo-ascii.png" alt="Pacta" width="400">
</p>

<p align="center">
  <strong>Architecture Governance & Architecture-as-Code</strong>
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

> **Warning:** Experimental. Expect breaking changes until release 0.1.0

Pacta is an architecture governance tool that helps teams define architectural intent, gain insights through metrics and historical trends, detect architectural drift, and evolve codebases safely without blocking delivery.

```bash
pip install pacta
```

<p align="center">
  <img src="https://raw.githubusercontent.com/akhundMurad/pacta/main/assets/demo.gif" alt="Pacta Demo" width="700">
</p>

Supported languages:

- Python
- Java (coming soon)
- Go (coming soon)
- C# (coming soon)

## Why?

Codebases rot. Architecture degrades through small changes no one tracks. Pacta turns architecture into something measurable, reviewable, and enforceable — catching drift early, not months later.

## What it does

- **Static analysis** — parses Python AST, builds a system graph
- **Layer enforcement** — domain can't import from infra, etc.
- **Snapshots** — version your architecture like code
- **Baseline mode** — fail only on *new* violations, not legacy debt
- **History tracking** — view architecture evolution over time
- **Trend analysis** — track violations, nodes, edges over time with charts

## Quick example

> This is a minimal example. See the docs for advanced rules, baselines, and history.

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

### Baseline workflow

Got legacy violations? Save a baseline and only fail on new ones:

```bash
# Save current state
pacta scan . --model architecture.yml --rules rules.pacta.yml --save-ref baseline

# Later, in CI — fail only on new violations
pacta scan . --model architecture.yml --rules rules.pacta.yml --baseline baseline
```

### History tracking

Every scan creates a content-addressed snapshot. Inspect how your architecture evolves over time:

```bash
# View timeline
$ pacta history show --last 5

# View trends over time (violations, nodes, edges, coupling)
$ pacta history trends .
```

## Docs

- [CLI Reference](https://akhundmurad.github.io/pacta/cli/)
- [Architecture Model](https://akhundmurad.github.io/pacta/architecture/)
- [Rules DSL](https://akhundmurad.github.io/pacta/rules/)

## Roadmap (short)

- [x] Open-source CLI and analysis engine
- [x] Content-addressed snapshots with history tracking
- [x] Trend analysis with chart export
- [ ] Architecture visualization (Mermaid, D2)
- [ ] Health metrics (drift score, instability)
- [ ] Optional hosted service (future):
  - Cross-repository insights
  - Historical trend analysis
  - Team-level governance and reporting

## License

Apache-2.0. See [LICENSE](./LICENSE).
