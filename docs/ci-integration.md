# CI/CD Integration

Pacta is designed for CI/CD pipelines. This guide shows how to integrate architecture checks into your workflow.

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success, no violations (or no *new* violations with baseline) |
| `1` | Violations found |
| `2` | Engine error (config issue, parse error, etc.) |

## GitHub Actions

### Basic Check

Run architecture validation on every pull request:

```yaml
name: Architecture Check

on:
  pull_request:
    branches: [main]

jobs:
  architecture:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Pacta
        run: pip install pacta

      - name: Check Architecture
        run: pacta scan . --model architecture.yml --rules rules.pacta.yml
```

### With Baseline (Recommended)

For existing projects with legacy violations, use baselines to only fail on *new* violations:

```yaml
name: Architecture Check

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  architecture:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Pacta
        run: pip install pacta

      # On main branch: update baseline
      - name: Update Baseline
        if: github.ref == 'refs/heads/main'
        run: |
          pacta scan . \
            --model architecture.yml \
            --rules rules.pacta.yml \
            --save-ref baseline

      # On PR: check against baseline
      - name: Check Against Baseline
        if: github.event_name == 'pull_request'
        run: |
          pacta scan . \
            --model architecture.yml \
            --rules rules.pacta.yml \
            --baseline baseline
```

!!! note "Persisting baselines"
    The baseline is stored in `.pacta/snapshots/`. Commit this directory to your repository, or use GitHub Actions cache/artifacts to persist it between runs.

### Pacta GitHub Action (Recommended)

The simplest way to get rich architectural PR comments. Uses `--format github` to generate a descriptive Markdown comment with structural changes, violation details, and architecture trends:

```yaml
name: Architecture Check

on:
  pull_request:
    branches: [main]

jobs:
  architecture:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - uses: akhundMurad/pacta@main
        with:
          model: architecture.yml
          rules: rules.pacta.yml
          baseline: baseline
```

The action will:

- Run `pacta scan` with `--format github` to produce a rich Markdown report
- Post (or update) a PR comment with structural changes, new/fixed violations, and architecture trends
- Fail the check if new violations are introduced (configurable via `fail-on-violations: false`)

**Action Inputs:**

| Input | Default | Description |
|-------|---------|-------------|
| `model` | `architecture.yml` | Path to architecture model |
| `rules` | `rules.pacta.yml` | Path to rules file |
| `baseline` | *(none)* | Baseline ref for incremental checks |
| `python-version` | `3.11` | Python version |
| `fail-on-violations` | `true` | Fail if new violations found |
| `pacta-version` | `pacta` | Pacta package specifier |

### JSON Output for PR Comments

Generate JSON output and post results as a PR comment:

```yaml
name: Architecture Check

on:
  pull_request:
    branches: [main]

jobs:
  architecture:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Pacta
        run: pip install pacta

      - name: Run Architecture Check
        id: pacta
        continue-on-error: true
        run: |
          pacta scan . \
            --model architecture.yml \
            --rules rules.pacta.yml \
            --baseline baseline \
            --format json > results.json

          # Extract summary for PR comment
          VIOLATIONS=$(jq '.summary.total_violations' results.json)
          NEW=$(jq '.summary.new_violations // 0' results.json)
          echo "violations=$VIOLATIONS" >> $GITHUB_OUTPUT
          echo "new=$NEW" >> $GITHUB_OUTPUT

      - name: Comment on PR
        uses: actions/github-script@v7
        with:
          script: |
            const violations = ${{ steps.pacta.outputs.violations }};
            const newViolations = ${{ steps.pacta.outputs.new }};

            let body;
            if (violations === 0) {
              body = '### Architecture Check Passed\n\nNo architectural violations found.';
            } else if (newViolations === 0) {
              body = `### Architecture Check Passed\n\n${violations} existing violation(s), 0 new.`;
            } else {
              body = `### Architecture Check Failed\n\n**${newViolations} new violation(s)** introduced.\n\nRun \`pacta scan\` locally to see details.`;
            }

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });

      - name: Fail on New Violations
        if: steps.pacta.outputs.new > 0
        run: exit 1
```

## GitLab CI

### Basic Check

```yaml
architecture:
  stage: test
  image: python:3.11
  script:
    - pip install pacta
    - pacta scan . --model architecture.yml --rules rules.pacta.yml
```

### With Baseline

```yaml
stages:
  - test

variables:
  PACTA_BASELINE: baseline

architecture:
  stage: test
  image: python:3.11
  script:
    - pip install pacta
    - |
      if [ "$CI_COMMIT_BRANCH" = "main" ]; then
        # Update baseline on main
        pacta scan . --model architecture.yml --rules rules.pacta.yml --save-ref $PACTA_BASELINE
      else
        # Check against baseline on feature branches
        pacta scan . --model architecture.yml --rules rules.pacta.yml --baseline $PACTA_BASELINE
      fi
  cache:
    paths:
      - .pacta/
```

## Pre-commit Hook

Run Pacta as a pre-commit hook to catch violations before they're committed:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pacta
        name: Architecture Check
        entry: pacta scan . --model architecture.yml --rules rules.pacta.yml -q
        language: system
        pass_filenames: false
        types: [python]
```

!!! tip "Performance"
    Use `-q` (quiet mode) for faster output in hooks. Consider running against baseline for large codebases with legacy violations.

## Makefile Integration

Add Pacta to your Makefile for easy local runs:

```makefile
.PHONY: arch arch-snapshot arch-check arch-baseline arch-ci

# Full scan (snapshot + check in one step)
arch:
	pacta scan . --model architecture.yml --rules rules.pacta.yml

# Two-step workflow
arch-snapshot:
	pacta snapshot save . --model architecture.yml

arch-check:
	pacta check . --rules rules.pacta.yml

# Update baseline
arch-baseline:
	pacta snapshot save . --model architecture.yml --ref baseline
	pacta check . --ref baseline --rules rules.pacta.yml

# Check against baseline (CI mode)
arch-ci:
	pacta scan . --model architecture.yml --rules rules.pacta.yml --baseline baseline
```

## JSON Schema

The `--format json` output follows this structure:

```json
{
  "run_info": {
    "tool_version": "0.0.5",
    "timestamp": "2025-01-22T12:00:00+00:00",
    "commit": "abc1234",
    "branch": "main"
  },
  "summary": {
    "total_violations": 5,
    "by_severity": {
      "error": 3,
      "warning": 2
    },
    "new_violations": 1,
    "existing_violations": 4,
    "fixed_violations": 0
  },
  "violations": [
    {
      "rule_id": "no_domain_to_infra",
      "rule_name": "Domain cannot depend on Infrastructure",
      "severity": "error",
      "status": "new",
      "location": {
        "file": "src/domain/user.py",
        "line": 3,
        "column": 1
      },
      "message": "Domain layer must not import from Infrastructure",
      "suggestion": "Use dependency injection...",
      "explanation": "\"myapp.domain.UserService\" in domain layer imports \"myapp.infra.Database\" in infra layer"
    }
  ]
}
```

Use `jq` to extract specific fields:

```bash
# Get new violation count
pacta scan . --format json | jq '.summary.new_violations'

# List files with violations
pacta scan . --format json | jq -r '.violations[].location.file' | sort -u

# Filter only errors
pacta scan . --format json | jq '.violations | map(select(.severity == "error"))'
```
