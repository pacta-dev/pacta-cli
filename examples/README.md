# Examples

Pacta includes several example projects demonstrating different architectural patterns and use cases.

## Available Examples

| Example | Description | Best For |
|---------|-------------|----------|
| [Simple Layered App](simple-layered-app.md) | Classic N-tier architecture | Teams familiar with layered architecture |
| [Hexagonal Architecture](hexagonal-app.md) | Ports and Adapters pattern | Domain-driven design, high testability |
| [Legacy Migration](legacy-migration.md) | Baseline workflow for brownfield | Existing codebases, incremental adoption |

## Quick Start

Each example includes:

- `architecture.yml` - System and layer definitions
- `rules.pacta.yml` - Architectural constraints
- `src/` - Sample Python code demonstrating the architecture

To run any example:

```bash
cd examples/<example-name>

# One-step (scan = snapshot + check):
pacta scan . --model architecture.yml --rules rules.pacta.yml

# Or two-step:
pacta snapshot save . --model architecture.yml
pacta check . --rules rules.pacta.yml
```

## Creating Your Own

1. Copy the example closest to your needs
2. Modify `architecture.yml` to match your directory structure
3. Adjust `rules.pacta.yml` for your constraints
4. Run `pacta scan` and iterate

See the [Configuration Reference](../configuration.md) for full schema documentation.
