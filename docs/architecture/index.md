# Architecture Model

The architecture model defines your system structure in YAML.

Pacta supports two schema versions:

- **v1** — Flat containers with layers. Simple and sufficient for single-service architectures.
- **v2** — Nested containers with `kind` and `contains`. Designed for microservices and modular monoliths.

The loader auto-detects the version from the `version:` key. If absent, v1 is assumed.
