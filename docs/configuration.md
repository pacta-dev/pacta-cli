# Configuration Reference

Complete schema documentation for Pacta configuration files.

## architecture.yml

The architecture model file defines your system structure, containers, and layers.

### Full Schema

```yaml
version: 1                    # Required, must be 1

system:
  id: string                  # Required, unique identifier
  name: string                # Required, display name

containers:
  <container-id>:             # Container identifier (e.g., backend, api)
    name: string              # Optional, display name
    description: string       # Optional, description
    code:
      roots:                  # Required, directories to scan
        - string              # Relative paths from repo root
      layers:
        <layer-id>:           # Layer identifier (e.g., domain, infra)
          name: string        # Optional, display name
          description: string # Optional, description
          patterns:           # Required, glob patterns
            - string          # Patterns matching files in this layer

contexts:                     # Optional, bounded contexts
  <context-id>:
    name: string
    containers:
      - string                # Container IDs in this context

relations:                    # Optional, high-level container relations
  - from: string              # Container ID
    to: string                # Container ID
    type: string              # Relation type (e.g., uses, calls)
```

### Fields Reference

#### system

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier for the system |
| `name` | string | Yes | Human-readable name |

#### containers

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | Human-readable name |
| `description` | string | No | Container description |
| `code.roots` | list[string] | Yes | Directories to scan for source code |
| `code.layers` | map | Yes | Layer definitions |

#### layers

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | Human-readable name |
| `description` | string | No | Layer description |
| `patterns` | list[string] | Yes | Glob patterns matching files in this layer |

**Glob pattern examples:**

| Pattern | Matches |
|---------|---------|
| `src/domain/**` | All files under `src/domain/` recursively |
| `src/domain/*.py` | Python files directly in `src/domain/` |
| `src/**/models.py` | Any `models.py` under `src/` |
| `!src/domain/tests/**` | Exclude (negate) test files |

### Example: Clean Architecture

```yaml
version: 1
system:
  id: ecommerce
  name: E-Commerce Platform

containers:
  order-service:
    name: Order Service
    description: Handles order processing and management
    code:
      roots:
        - services/orders/src
      layers:
        domain:
          name: Domain Layer
          description: Core business logic and entities
          patterns:
            - services/orders/src/domain/**
        application:
          name: Application Layer
          description: Use cases and orchestration
          patterns:
            - services/orders/src/application/**
        infrastructure:
          name: Infrastructure Layer
          description: External services and persistence
          patterns:
            - services/orders/src/infrastructure/**
        presentation:
          name: Presentation Layer
          description: API controllers and DTOs
          patterns:
            - services/orders/src/api/**
```

---

## rules.pacta.yml

The rules file defines architectural constraints using Pacta's rule DSL.

### Full Schema

```yaml
rule:
  id: string                  # Required, unique rule identifier
  name: string                # Required, human-readable name
  description: string         # Optional, detailed description
  severity: error|warning|info # Required
  target: dependency|node     # Required, what to evaluate
  when:                       # Required, conditions
    all:                      # All conditions must match
      - <condition>
    any:                      # Any condition must match
      - <condition>
  action: forbid|allow|require # Required
  message: string             # Optional, shown on violation
  suggestion: string          # Optional, how to fix
```

### Fields Reference

#### Rule Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier (used in output) |
| `name` | string | Yes | Human-readable rule name |
| `description` | string | No | Detailed explanation |
| `severity` | enum | Yes | `error`, `warning`, or `info` |
| `target` | enum | Yes | `dependency` (edges) or `node` (vertices) |
| `when` | object | Yes | Conditions that trigger the rule |
| `action` | enum | Yes | `forbid`, `allow`, or `require` |
| `message` | string | No | Explanation shown on violation (auto-generated if omitted) |
| `suggestion` | string | No | How to fix the issue |

#### Severity Levels

| Level | Description | CI Behavior |
|-------|-------------|-------------|
| `error` | Critical violation | Fails CI (exit code 1) |
| `warning` | Should be addressed | Reported but doesn't fail |
| `info` | Informational | Tracked for visibility |

#### Condition Syntax

**Property access:**

| Property | Target | Description |
|----------|--------|-------------|
| `from.layer` | dependency | Source node's layer |
| `to.layer` | dependency | Target node's layer |
| `from.container` | dependency | Source node's container |
| `to.container` | dependency | Target node's container |
| `layer` | node | Node's layer |
| `container` | node | Node's container |
| `kind` | node | Node type (module, class, function) |

**Operators:**

| Operator | Example | Description |
|----------|---------|-------------|
| `==` | `from.layer == domain` | Equality |
| `!=` | `to.layer != infra` | Inequality |
| `in` | `from.layer in [domain, application]` | Value in list |
| `not_in` | `to.layer not_in [infra, external]` | Value not in list |
| `glob` | `from.fqname glob "*.service.*"` | Glob pattern match |
| `matches` | `from.fqname matches ".*Service$"` | Regex match |
| `contains` | `tags contains "legacy"` | Collection contains value |

**Combinators:**

```yaml
# All conditions must be true (AND)
when:
  all:
    - from.layer == domain
    - to.layer == infra

# Any condition must be true (OR)
when:
  any:
    - to.layer == infra
    - to.layer == external

# Nested combinators
when:
  all:
    - from.layer == domain
    - any:
        - to.layer == infra
        - to.layer == external
```

### Example: Complete Rules File

```yaml
# Domain cannot depend on Infrastructure
rule:
  id: no_domain_to_infra
  name: Domain must not depend on Infrastructure
  description: |
    The domain layer contains pure business logic and should not
    depend on technical implementation details.
  severity: error
  target: dependency
  when:
    all:
      - from.layer == domain
      - to.layer == infrastructure
  action: forbid
  message: Domain layer must not import from Infrastructure layer
  suggestion: Use dependency injection and define interfaces in the domain layer

---
# Domain cannot depend on Presentation
rule:
  id: no_domain_to_presentation
  name: Domain must not depend on Presentation
  severity: error
  target: dependency
  when:
    all:
      - from.layer == domain
      - to.layer == presentation
  action: forbid
  message: Domain layer must not depend on Presentation layer

---
# Application can use Domain (allowed, tracked for info)
rule:
  id: app_uses_domain
  name: Application uses Domain
  severity: info
  target: dependency
  when:
    all:
      - from.layer == application
      - to.layer == domain
  action: allow
  message: Application layer correctly using Domain layer
```

---

## .pacta/ Directory

Pacta stores data in a `.pacta/` directory at your repository root.

```
.pacta/
└── snapshots/
    ├── objects/             # Content-addressed snapshot storage
    │   ├── a1b2c3d4.json    # 8-char hash prefix filename
    │   ├── e5f6a7b8.json
    │   └── ...
    └── refs/                # Named references to snapshots
        ├── latest           # Text file containing hash of most recent snapshot
        ├── baseline         # Text file containing hash (created with --save-ref)
        └── ...
```

### Snapshots

Snapshots are content-addressed (stored by hash of contents). They include:

- Architecture IR (nodes and edges)
- Violation list
- Metadata (timestamp, commit, branch, tool version)

### References

References are named pointers to snapshot hashes:

| Ref | Description |
|-----|-------------|
| `latest` | Automatically updated on each scan/check |
| `baseline` | Created with `--save-ref baseline` |
| Custom | Any name you choose with `--save-ref <name>` |

### Git Integration

**Recommended:** Commit `.pacta/` to version control for:

- Persistent baselines across team members
- History tracking with commits
- CI/CD baseline comparison

Add to `.gitignore` only if you don't need persistent baselines:

```gitignore
# Ignore Pacta data (not recommended)
.pacta/
```
