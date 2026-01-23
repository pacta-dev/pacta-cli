# Architecture Model

The architecture model defines your system structure in YAML.

## File Format

Create `architecture.yml` in your repository root:

```yaml
version: 1

system:
  id: my-system
  name: My System

containers:
  my-app:
    name: My Application
    description: Main application container
    code:
      roots:
        - src
      layers:
        ui:
          name: UI Layer
          patterns:
            - src/ui/**
        application:
          name: Application Layer
          patterns:
            - src/application/**
        domain:
          name: Domain Layer
          patterns:
            - src/domain/**
        infra:
          name: Infrastructure Layer
          patterns:
            - src/infra/**

contexts: {}
```

## Schema

### system

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique system identifier |
| `name` | string | Yes | Human-readable name |

### containers

Map of container definitions.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Container name |
| `description` | string | No | Container description |
| `context` | string | No | Bounded context reference |
| `code` | object | No | Code mapping configuration |

### code

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `roots` | list | Yes | Source root directories |
| `layers` | map | No | Layer definitions |

### layers

Map of layer definitions.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | Layer display name |
| `description` | string | No | Layer description |
| `patterns` | list | Yes | Glob patterns matching layer files |

## Example: Clean Architecture

```yaml
version: 1

system:
  id: healthcare-scheduling
  name: Healthcare Scheduling

containers:
  scheduling-api:
    name: Scheduling API
    context: scheduling
    code:
      roots:
        - services/scheduling-api
      layers:
        ui:
          name: Presentation
          patterns:
            - services/scheduling-api/api/**
        application:
          name: Use Cases
          patterns:
            - services/scheduling-api/app/**
        domain:
          name: Domain
          patterns:
            - services/scheduling-api/domain/**
        infra:
          name: Infrastructure
          patterns:
            - services/scheduling-api/infra/**
```
