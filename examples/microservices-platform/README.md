# Microservices Platform Example

This example demonstrates the **v2 schema** with nested containers, container kinds, and cross-service rules.

## Architecture

The platform consists of three containers:

- **billing-service** (`kind: service`) — handles invoicing
    - **invoice-module** (`kind: module`) — nested module for invoice domain logic
- **identity-service** (`kind: service`) — handles authentication
- **shared-utils** (`kind: library`) — shared utilities

## Key v2 Features

- **`kind`** — every container declares whether it's a `service`, `module`, or `library`
- **`contains`** — `billing-service` nests `invoice-module` inside it
- **`interactions`** — v2 alias for `relations`
- **Dot-qualified IDs** — the nested module is addressed as `billing-service.invoice-module`
- **Context inheritance** — `invoice-module` inherits `context: billing` from its parent

## Rules

The rules demonstrate v2-specific fields:

- `from.service != to.service` — detect cross-service dependencies
- `from.within == library` / `to.within == service` — enforce library independence
- `from.layer` / `to.layer` — standard layer constraints

### `kind` vs `within`

For nested containers, there's an important distinction:

| Field | Meaning | Example |
|-------|---------|---------|
| `kind` | Immediate container's kind | `module` for code in `invoice-module` |
| `within` | Top-level container's kind | `service` for any code inside `billing-service` |

**Why use `within`?** Using `to.kind == service` would NOT match code inside nested modules (like `invoice-module`), because the immediate kind is `module`. Using `to.within == service` matches ANY code inside the service hierarchy.

## Running

```bash
cd examples/microservices-platform
pacta scan . --model architecture.yml --rules rules.pacta.yml
```

This will detect a violation because `libs/shared/money.py` imports from `services/billing/domain/invoice/model/invoice.py`.
