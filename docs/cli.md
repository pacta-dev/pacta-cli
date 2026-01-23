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

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success, no violations |
| `1` | Violations found |
| `2` | Engine error |
