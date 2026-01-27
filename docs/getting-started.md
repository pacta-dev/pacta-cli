# Getting Started

You're six months into a project. The codebase that started clean now has database calls in the domain layer, circular dependencies nobody remembers adding, and a "quick fix" that coupled two services together. You know the architecture drifted — but when? How much? Is it getting worse?

Pacta answers these questions. It versions your architecture like Git versions your code, so you can see exactly how your system evolves over time.

---

## Your First Snapshot

Install Pacta:

```bash
pip install pacta
```

Create `architecture.yml` to describe your system's layers:

```yaml
version: 1
system:
  id: myapp
  name: My Application

containers:
  backend:
    code:
      roots: [src]
      layers:
        domain:
          patterns: [src/domain/**]
        application:
          patterns: [src/application/**]
        infra:
          patterns: [src/infra/**]
```

Now capture a snapshot:

```bash
pacta snapshot . --model architecture.yml
```

Pacta just analyzed every module and dependency in your codebase and stored a content-addressed snapshot in `.pacta/`. This snapshot is immutable — a permanent record of your architecture at this moment.

---

## Watching Architecture Change

A week passes. Your team ships features, fixes bugs, refactors code. Run another snapshot:

```bash
pacta snapshot . --model architecture.yml
```

Now you have two points in time. See what changed:

```bash
pacta history show --last 5
```

```
TIMESTAMP            SNAPSHOT    NODES  EDGES  VIOLATIONS
2024-01-22 14:30:00  f7a3c2...   48     82     0
2024-01-15 10:00:00  abc123...   45     78     0
```

Three new modules, four new dependencies. But are things getting better or worse? View the trend:

```bash
pacta history trends . --metric edges
```

```
Edge Count Trend (5 entries)
============================

 82 │                              ●
    │               ●--------------
 79 │    ●----------
    │
 76 ├●---
    └────────────────────────────────
      Jan 15                   Jan 22

Trend: ↑ Increasing (+6 over period)
First: 76 edges (Jan 15)
Last:  82 edges (Jan 22)

Average: 79 edges
Min: 76, Max: 82
```

Coupling is climbing. You caught drift early — before it became a problem someone complains about in a retrospective.

Need to share this with the team? Export as an image:

```bash
pip install pacta[viz]  # one-time install for chart export
pacta history trends . --metric edges --output coupling-trend.png
```

This generates a publication-ready chart with trend annotations — drop it into a PR, a Slack thread, or your architecture docs.

---

## Adding Guardrails

You want to protect what you've built. Create `rules.pacta.yml`:

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

Run a check against your snapshot:

```bash
# Option A: Check the snapshot you already have
pacta check . --rules rules.pacta.yml

# Option B: Or do snapshot + check in one step
pacta scan . --model architecture.yml --rules rules.pacta.yml
```

```
✗ 2 violations (2 error) [2 new]

  ✗ ERROR [no_domain_to_infra] @ src/domain/user.py:3:1
    status: new
    Domain layer must not import from Infrastructure
```

Two violations. But wait — this is a legacy codebase. You can't fix everything today.

---

## Living with Legacy

Save the current state as a baseline:

```bash
pacta scan . --model architecture.yml --rules rules.pacta.yml --save-ref baseline
```

Now future scans compare against this baseline:

```bash
pacta scan . --model architecture.yml --rules rules.pacta.yml --baseline baseline
```

New violations fail CI. Existing ones are tracked but tolerated. You can pay down debt at your own pace while preventing new debt from accumulating.

A month later, you check progress:

```bash
pacta history trends . --metric violations
```

```
Violations Trend (8 entries)
============================

 12 ├●
    │ ●---●
  8 │      ●---●
    │           ●---●
  4 │                ●
    └────────────────────────────────
      Feb 01                   Feb 28

Trend: ↓ Improving (-8 over period)
First: 12 violations (Feb 01)
Last:  4 violations (Feb 28)

Average: 7 violations
Min: 4, Max: 12
```

You're winning. Export it for the next retro:

```bash
pacta history trends . --metric violations --output debt-burndown.png
```

---

## The Bigger Picture

Traditional architecture tools give you a pass/fail at a point in time. Pacta gives you something different: a versioned history of your architecture that you can query, compare, and trend.

When someone asks "when did our architecture start degrading?" — you have the answer. When a refactor claims to improve coupling — you can measure it. When leadership wants proof that technical debt is being addressed — you have the chart.

Architecture stops being something that "just happens" and becomes something you observe, understand, and control.

---

## Reference

**Project structure:**

```
myproject/
├── architecture.yml      # Layer definitions
├── rules.pacta.yml       # Governance rules
├── src/
│   ├── domain/
│   ├── application/
│   └── infra/
└── .pacta/               # Snapshot storage
```

**Next steps:**

- [CLI Reference](cli.md) — Commands and options
- [Architecture Model](architecture.md) — Configuration schema
- [Rules DSL](rules.md) — Rule conditions
- [CI Integration](ci-integration.md) — Automate in your pipeline
