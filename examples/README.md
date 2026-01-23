# Pacta Examples

## simple-layered-app

A Python application demonstrating clean architecture with four layers:

```
src/
├── ui/           # Controllers, API endpoints
├── application/  # Use cases, services
├── domain/       # Business logic, models
└── infra/        # Repositories, database
```

### Files

- `architecture.yml` - Defines layers and their file patterns
- `rules.pacta.yml` - Architectural rules (e.g., domain cannot depend on infra)

### Try it

```bash
cd simple-layered-app

# Scan for violations
pacta scan src \
  --model architecture.yml \
  --rules rules.pacta.yml

# Quiet mode (summary only)
pacta scan src \
  --model architecture.yml \
  --rules rules.pacta.yml -q

# Verbose mode (all details)
pacta scan src \
  --model architecture.yml \
  --rules rules.pacta.yml -v

# Save a baseline
pacta scan src \
  --model architecture.yml \
  --rules rules.pacta.yml \
  --save-ref baseline

# Compare against baseline
pacta scan src \
  --model architecture.yml \
  --rules rules.pacta.yml \
  --baseline baseline

# Save architecture snapshot (without running rules)
pacta snapshot save src \
  --model architecture.yml \
  --ref v1

# Save another snapshot
pacta snapshot save src \
  --model architecture.yml \
  --ref v2

# Compare two snapshots
pacta diff src --from v1 --to v2
```
