# Rules DSL

Define architectural rules in `rules.pacta.yml`.

## Rule Structure

```yaml
rule:
  id: rule-id
  name: Rule Name
  description: What this rule enforces
  severity: error | warning | info
  target: dependency
  when:
    all:
      - condition1
      - condition2
  action: forbid | allow
  message: Violation message
  suggestion: How to fix
```

## Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique rule identifier |
| `name` | string | Yes | Human-readable name |
| `description` | string | No | Detailed description |
| `severity` | string | Yes | `error`, `warning`, or `info` |
| `target` | string | Yes | What to evaluate (e.g., `dependency`) |
| `when` | object | Yes | Conditions for the rule |
| `action` | string | Yes | `forbid` or `allow` |
| `message` | string | Yes | Message shown on violation |
| `suggestion` | string | No | Remediation guidance |

## Conditions

### Layer Conditions

```yaml
from.layer == domain    # Source is domain layer
to.layer == infra       # Target is infra layer
```

### Combining Conditions

```yaml
# All conditions must match
when:
  all:
    - from.layer == domain
    - to.layer == infra

# Any condition can match
when:
  any:
    - to.layer == domain
    - to.layer == application
```

## Example: Clean Architecture Rules

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
      - to.layer == infra
  action: forbid
  message: Domain layer must not depend on Infrastructure layer
  suggestion: Use dependency injection and define interfaces in the domain layer

# Domain cannot depend on Application
rule:
  id: no_domain_to_application
  name: Domain must not depend on Application
  severity: error
  target: dependency
  when:
    all:
      - from.layer == domain
      - to.layer == application
  action: forbid
  message: Domain layer must not depend on Application layer
  suggestion: Move shared logic to the domain layer

# Domain cannot depend on UI
rule:
  id: no_domain_to_ui
  name: Domain must not depend on UI
  severity: error
  target: dependency
  when:
    all:
      - from.layer == domain
      - to.layer == ui
  action: forbid
  message: Domain layer must not depend on UI layer
  suggestion: Keep domain models free from presentation concerns

# UI should not directly access Infrastructure
rule:
  id: no_ui_to_infra
  name: UI should not directly access Infrastructure
  severity: warning
  target: dependency
  when:
    all:
      - from.layer == ui
      - to.layer == infra
  action: forbid
  message: UI layer should not directly depend on Infrastructure layer
  suggestion: Access infrastructure through application services instead
```
