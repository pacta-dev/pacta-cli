# Troubleshooting

Common issues and frequently asked questions about Pacta.

## Common Errors

### "No analyzers found"

**Error:**
```
Error: No analyzers found for the given repository
```

**Cause:** Pacta couldn't find any supported language analyzers for your codebase.

**Solution:**

1. Ensure you have Python files (`.py`) in the directories specified in `roots`
2. Check that your `architecture.yml` has correct `roots` paths:
   ```yaml
   containers:
     myapp:
       code:
         roots:
           - src  # This directory must exist and contain .py files
   ```
3. Verify the paths are relative to your repository root

### "Model validation failed"

**Error:**
```
Error: Model validation failed: [details]
```

**Cause:** Your `architecture.yml` has invalid structure or missing required fields.

**Solution:**

Check for these common issues:

1. Missing `version` field (must be `1`):
   ```yaml
   version: 1  # Required
   system:
     id: myapp
   ```

2. Missing `system.id`:
   ```yaml
   system:
     id: myapp  # Required
     name: My Application
   ```

3. Invalid layer patterns (must be valid glob patterns):
   ```yaml
   layers:
     domain:
       patterns:
         - src/domain/**  # Correct
         - src/domain/*   # Only matches one level
   ```

### "Rules parsing error"

**Error:**
```
Error: Failed to parse rules file: [details]
```

**Cause:** Your `rules.pacta.yml` has invalid YAML syntax or rule structure.

**Solution:**

1. Validate YAML syntax (use a YAML linter)
2. Ensure each rule has required fields:
   ```yaml
   rule:
     id: my_rule          # Required
     name: My Rule        # Required
     severity: error      # Required: error, warning, or info
     target: dependency   # Required: dependency or node
     when:                # Required
       all:
         - from.layer == domain
     action: forbid       # Required: forbid or allow
   ```

3. Check condition syntax:
   ```yaml
   # Correct
   when:
     all:
       - from.layer == domain
       - to.layer == infra

   # Wrong (missing quotes around strings with spaces)
   when:
     all:
       - from.layer == my domain  # Error!
   ```

### "Baseline not found"

**Error:**
```
Error: Baseline 'baseline' not found
```

**Cause:** You're trying to compare against a baseline that doesn't exist.

**Solution:**

1. Create a baseline first:
   ```bash
   pacta scan . --model architecture.yml --rules rules.pacta.yml --save-ref baseline
   ```

2. Check that `.pacta/` directory exists and contains snapshots:
   ```bash
   ls -la .pacta/snapshots/objects/
   ls -la .pacta/snapshots/refs/
   ```

3. If using CI, ensure the `.pacta/` directory is cached or committed

### "Permission denied" reading files

**Error:**
```
Error: Permission denied: [file path]
```

**Cause:** Pacta doesn't have read access to some files in your repository.

**Solution:**

1. Check file permissions: `ls -la [file]`
2. Ensure you're running Pacta with appropriate user permissions
3. In CI, verify the checkout step has correct permissions

## Frequently Asked Questions

### How do I ignore test files?

Configure your `architecture.yml` to exclude test directories from the `roots`:

```yaml
containers:
  myapp:
    code:
      roots:
        - src           # Include
        # - tests       # Don't include tests
```

Or, if tests are inside `src/`, use layer patterns that exclude them:

```yaml
layers:
  domain:
    patterns:
      - src/domain/**
      - "!src/domain/tests/**"  # Exclude tests
```

### Can I use multiple rules files?

Yes, use the `--rules` option multiple times:

```bash
pacta scan . \
  --model architecture.yml \
  --rules rules/base.pacta.yml \
  --rules rules/strict.pacta.yml
```

Rules from all files are combined and evaluated together.

### What languages are supported?

Currently supported:

- **Python** - Full support via AST analysis

Coming soon:

- Java
- Go
- C#

### How do baselines work?

Baselines are content-addressed snapshots of your architecture at a point in time. They're stored in `.pacta/snapshots/`:

- **Objects** (`.pacta/snapshots/objects/`) - Immutable snapshot files named by 8-char hash
- **Refs** (`.pacta/snapshots/refs/`) - Named pointers (like `baseline`, `latest`) to object hashes

1. **Create baseline:** Saves current violations with a reference name
   ```bash
   pacta scan . --save-ref baseline
   ```

2. **Compare against baseline:** Only reports *new* violations
   ```bash
   pacta scan . --baseline baseline
   ```

3. **Violation statuses:**
   - `new` - Violation introduced after baseline (fails CI)
   - `existing` - Violation present in baseline (doesn't fail CI)
   - `fixed` - Violation in baseline but now resolved

### How do I see what changed between scans?

Use the `diff` command:

```bash
# Save two snapshots
pacta snapshot save . --ref v1
# ... make changes ...
pacta snapshot save . --ref v2

# Compare them
pacta diff . --from v1 --to v2
```

### Can I run Pacta on a monorepo?

Yes. Define multiple containers in your `architecture.yml`:

```yaml
containers:
  service-a:
    code:
      roots: [services/service-a/src]
      layers:
        domain:
          patterns: [services/service-a/src/domain/**]
        infra:
          patterns: [services/service-a/src/infra/**]

  service-b:
    code:
      roots: [services/service-b/src]
      layers:
        domain:
          patterns: [services/service-b/src/domain/**]
        infra:
          patterns: [services/service-b/src/infra/**]
```

### Why am I seeing violations I didn't expect?

Common causes:

1. **Glob patterns too broad:** Check that your layer patterns don't overlap
   ```yaml
   # Overlapping - src/domain/utils.py matches both!
   domain:
     patterns: [src/domain/**]
   utils:
     patterns: [src/**/utils/**]
   ```

2. **Transitive dependencies:** Module A imports B, B imports C. If A is in domain and C is in infra, you might see violations even if B is in application.

3. **Re-exports:** Python re-exports (e.g., `from .submodule import *`) can create unexpected dependencies.

Debug with verbose output:
```bash
pacta scan . --model architecture.yml --rules rules.pacta.yml -v
```

### How do I track architecture metrics over time?

Use the history commands:

```bash
# View timeline of snapshots
pacta history show . --last 20

# View violation trends
pacta history trends . --metric violations

# View coupling trends (edges/nodes ratio)
pacta history trends . --metric density

# Export as image for documentation
pacta history trends . --output trends.png
```

### What's the performance impact on large codebases?

Pacta parses Python AST, which is fast but scales with codebase size. For large codebases:

1. **Limit scope:** Only include relevant directories in `roots`
2. **Use quiet mode:** `-q` reduces output processing time
3. **Incremental checks:** Consider `--mode changed_only` (if supported)

Typical performance:
- Small projects (<100 files): <1 second
- Medium projects (100-1000 files): 1-5 seconds
- Large projects (1000+ files): 5-30 seconds

## Getting Help

If you're stuck:

1. Check the [CLI Reference](cli.md) for command options
2. Look at the [example project](https://github.com/akhundMurad/pacta/tree/main/examples/simple-layered-app)
3. [Open an issue](https://github.com/akhundMurad/pacta/issues) on GitHub
