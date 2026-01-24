# CLI Reference

## scan

Scan repository and evaluate architectural rules.

```bash
pacta scan [PATH] [OPTIONS]
```

**Arguments:**

| Argument | Default | Description |
|----------|---------|-------------|
| `PATH` | `.` | Repository root |

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--model FILE` | `architecture.yml` | Architecture model file |
| `--rules FILE` | `rules.pacta.yml` | Rules file (repeatable) |
| `--format {text,json}` | `text` | Output format |
| `--baseline REF` | - | Compare against baseline snapshot |
| `--save-ref REF` | - | Save snapshot under this ref |
| `--mode {full,changed_only}` | `full` | Evaluation mode |
| `-q, --quiet` | - | Summary only |
| `-v, --verbose` | - | Include all details |

**Examples:**

```bash
# Basic scan
pacta scan . --model architecture.yml --rules rules.pacta.yml

# Quiet mode (CI-friendly)
pacta scan . --model architecture.yml --rules rules.pacta.yml -q

# Save baseline
pacta scan . --model architecture.yml --rules rules.pacta.yml --save-ref baseline

# Check against baseline (fail only on new violations)
pacta scan . --model architecture.yml --rules rules.pacta.yml --baseline baseline

# JSON output for CI integration
pacta scan . --model architecture.yml --rules rules.pacta.yml --format json
```

**Example output:**

```
✗ 1 violations (1 error)

  ✗ ERROR [no-domain-infra] Domain cannot depend on Infrastructure @ src/domain/service.py:5:1
    status: new
    "app.domain.BillingService" in domain layer imports "app.infra.PostgresClient" in infra layer
```

Violations are displayed with human-readable explanations:

- **For dependency violations:** Shows which module imports/calls/uses another, with their respective layers
- **For node violations:** Shows the element type and where it was found (layer, container, context)

## snapshot save

Save architecture snapshot without running rules.

```bash
pacta snapshot save [PATH] [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--ref REF` | `latest` | Snapshot reference name |
| `--model FILE` | `architecture.yml` | Architecture model file |

**Examples:**

```bash
# Save snapshot
pacta snapshot save . --model architecture.yml --ref v1

# Save another version
pacta snapshot save . --model architecture.yml --ref v2
```

## diff

Compare two architecture snapshots.

```bash
pacta diff [PATH] --from REF --to REF
```

**Options:**

| Option | Required | Description |
|--------|----------|-------------|
| `--from REF` | Yes | Source snapshot ref |
| `--to REF` | Yes | Target snapshot ref |

**Examples:**

```bash
# Compare snapshots
pacta diff . --from v1 --to v2
```

## history show

View architecture timeline (list of snapshots).

```bash
pacta history show [PATH] [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--last N` | - | Show only last N entries |
| `--since DATE` | - | Show entries since date (ISO-8601) |
| `--branch NAME` | - | Filter by branch name |
| `--format {text,json}` | `text` | Output format |

**Examples:**

```bash
# Show all snapshots
pacta history show .

# Show last 10 entries
pacta history show . --last 10

# Filter by branch and date
pacta history show . --branch main --since 2025-01-01

# JSON output for scripting
pacta history show . --format json
```

**Example output:**

```
Architecture Timeline (3 entries)
============================================================

a1b2c3d4  2025-01-22  abc1234  main          42 nodes   87 edges   2 violations (latest)
e5f6g7h8  2025-01-20  def5678  main          42 nodes   85 edges   4 violations
12345678  2025-01-18  789abcd  feature/x     40 nodes   82 edges   3 violations
```

## history export

Export full history data for external processing or SaaS integration.

```bash
pacta history export [PATH] [OPTIONS]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--format {json,jsonl}` | `json` | Export format |
| `-o, --output FILE` | stdout | Output file path |

**Examples:**

```bash
# Export as JSON
pacta history export . --format json > history.json

# Export as JSON Lines (one entry per line)
pacta history export . --format jsonl > history.jsonl

# Export to file
pacta history export . -o export.json
```

**JSON output structure:**

```json
{
  "version": 1,
  "exported_at": "2025-01-22T12:00:00",
  "repo_root": "/path/to/repo",
  "refs": {
    "latest": "a1b2c3d4",
    "baseline": "e5f6g7h8"
  },
  "entries": [
    {
      "hash": "a1b2c3d4",
      "timestamp": "2025-01-22T12:00:00+00:00",
      "commit": "abc1234",
      "branch": "main",
      "refs": ["latest"],
      "node_count": 42,
      "edge_count": 87,
      "violations": [...]
    }
  ]
}
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success, no violations |
| `1` | Violations found |
| `2` | Engine error |
