# Contributing to Pacta

Thank you for your interest in contributing to Pacta!
This project is in active development, and all contributions are welcome — from bug reports to feature proposals and pull requests.

## Project Structure

```
pacta/
├── pacta/                 # Main package
│   ├── analyzers/         # Language analyzers (Python, etc.)
│   ├── cli/               # Command-line interface
│   ├── core/              # Engine and configuration
│   ├── ir/                # Intermediate representation
│   ├── mapping/           # Layer mapping and enrichment
│   ├── model/             # Architecture model (types, loader, resolver)
│   ├── plugins/           # Plugin system and interfaces
│   ├── reporting/         # Report generation and renderers
│   ├── rules/             # Rule DSL (parser, compiler, evaluator)
│   ├── snapshot/          # Snapshot management and diffing
│   ├── utils/             # Utility functions
│   └── vcs/               # Version control integration (git)
├── tests/                 # Test suite (mirrors package structure)
├── docs/                  # MkDocs documentation
├── examples/              # Example projects
└── assets/                # Logo and other assets
```

## Development Setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
# Clone the repository
git clone https://github.com/pacta-dev/pacta-cli.git
cd pacta

# Install dependencies with dev tools
make dev
# or: uv sync --group dev
```

## Development Workflow

### Running Tests

```bash
make test
# or: uv run pytest

# With coverage
make test-cov
```

### Linting and Formatting

```bash
# Check for linting issues
make lint

# Auto-format code
make format
```

### Type Checking

```bash
make typecheck
# or: uv run ty check pacta
```

### Documentation

```bash
# Serve docs locally
make docs

# Build docs
make docs-build
```

### Building

```bash
make build
# or: uv build
```

## How to Contribute

### 1. Open an Issue

If you find a bug or want to propose a feature, please open an issue first.
This helps keep discussion organized and ensures we're aligned before work begins.

### 2. Fork & Create a Branch

```bash
git checkout -b feature/my-feature
```

### 3. Write Clear, Minimal Code

- Follow the existing coding style (enforced by ruff)
- Add tests for new features in the appropriate `tests/` subdirectory
- Use [Conventional Commits](https://www.conventionalcommits.org/) for commit messages

### Commit Message Format

We use conventional commits to auto-generate the changelog. Format:

```
<type>(<scope>): <description>

[optional body]
```

**Types:**

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks |
| `perf` | Performance improvement |

**Examples:**

```bash
feat(cli): add history trends command
fix(rules): handle empty when block gracefully
docs(readme): add installation instructions
refactor(ir): simplify node merging logic
```

The changelog is generated with `make changelog` (requires [git-cliff](https://git-cliff.org/)).

### 4. Run Tests and Checks

Make sure all tests and checks pass before submitting a PR:

```bash
make lint
make typecheck
make test
```

### 5. Submit a Pull Request

Link the related issue and describe your changes clearly.

## Code of Conduct

Be respectful and constructive. We aim to create a friendly, collaborative environment.

---

Thank you for helping improve Pacta!
