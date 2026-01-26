# Hexagonal Architecture Example

This example demonstrates how to use Pacta to enforce [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/) (also known as Ports and Adapters).

## Architecture Overview

```mermaid
flowchart TB
    subgraph Driving["Driving Side (Primary)"]
        PA[Primary Adapters<br/>Controllers, CLI, Event Handlers]
    end

    subgraph Application["Application Core"]
        IP[Inbound Ports<br/>Use Case Interfaces]
        subgraph Domain["DOMAIN"]
            D[Entities<br/>Domain Services]
        end
        OP[Outbound Ports<br/>Repository Interfaces]
    end

    subgraph Driven["Driven Side (Secondary)"]
        SA[Secondary Adapters<br/>Database, APIs, Queues]
    end

    PA -->|uses| IP
    IP -->|calls| D
    D -->|uses| OP
    SA -.->|implements| OP

    style Domain fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style D fill:#bbdefb,stroke:#1565c0
    style IP fill:#fff8e1,stroke:#f57f17
    style OP fill:#fff8e1,stroke:#f57f17
    style PA fill:#f3e5f5,stroke:#7b1fa2
    style SA fill:#e8f5e9,stroke:#2e7d32
```

## Directory Structure

```
src/
├── domain/                    # Core business logic (center of hexagon)
│   ├── product.py             # Domain entity
│   └── product_service.py     # Domain service
│
├── ports/
│   ├── inbound/               # Driving ports (use case interfaces)
│   │   └── catalog_use_case.py
│   └── outbound/              # Driven ports (repository interfaces)
│       └── product_repository.py
│
└── adapters/
    ├── primary/               # Driving adapters (controllers, CLI)
    │   └── api_controller.py
    └── secondary/             # Driven adapters (database, APIs)
        └── postgres_product_repository.py
```

## Key Rules

| Rule | Description |
|------|-------------|
| Domain → Adapters | **Forbidden** - Domain must not know about adapters |
| Domain → Outbound Ports | **Allowed** - Domain uses repository interfaces |
| Ports → Adapters | **Forbidden** - Ports are interfaces, adapters implement them |
| Primary Adapters → Domain | **Warning** - Should go through inbound ports |
| Secondary Adapters → Outbound Ports | **Allowed** - Implements the interface |
| Adapters → Adapters | **Forbidden** - Adapters should be independent |

## Usage

```bash
# Run architecture check
pacta scan . --model architecture.yml --rules rules.pacta.yml

# Expected output (clean architecture):
# ✓ 0 violations
```

## Dependency Flow

Dependencies always point **inward** toward the domain:

```mermaid
flowchart LR
    PA[Primary<br/>Adapters] --> IP[Inbound<br/>Ports] --> D((DOMAIN))
    SA[Secondary<br/>Adapters] --> OP[Outbound<br/>Ports] --> D

    style D fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
```

This ensures:
- Domain is isolated and testable
- Adapters can be swapped without changing business logic
- The application is framework-agnostic
