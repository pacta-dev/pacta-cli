<p align="center">
  <img src="https://raw.githubusercontent.com/akhundMurad/pacta/main/assets/logo-ascii.png" alt="Pacta" width="400">
</p>

<p align="center">
  <strong>Architecture Insights, Governance & Versioned Design</strong>
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

Pacta turns software architecture into versioned, queryable data — so teams can see, compare, and reason about architectural change over time, not just block violations.

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

- **Architecture snapshots** — version your architecture like code
- **History & trends** — track how dependencies, coupling, and violations evolve over time
- **Diffs** — compare architectural states like Git commits
- **Metrics & insights** — nodes, edges, layers, instability, drift
- **Rules & governance** — express architectural intent and enforce it incrementally
- **Baseline mode** — govern change without being blocked by legacy debt

## Think of Pacta like Git for architecture

| Git | Pacta |
|-----|-------|
| `git add` | `pacta snapshot save` — capture an architectural snapshot |
| `git commit --verify` | `pacta check` — evaluate rules against a snapshot |
| `git commit` | `pacta scan` — snapshot + check in one step |
| `git log` | `pacta history` — timeline and trends of architectural states |
| `git diff` | `pacta diff` — compare two snapshots |
| branch protection | `rules.pacta.yml` — governance that prevents drift |

See the [Getting Started](https://akhundmurad.github.io/pacta/getting-started/) guide for a full walkthrough.

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
- [ ] Future: Architecture Intelligence Layer:
  - Cross-repository insights
  - Historical trend analysis
  - Team-level governance and reporting

## License

Apache-2.0. See [LICENSE](https://github.com/akhundMurad/pacta/blob/main/LICENSE).
