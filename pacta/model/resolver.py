from collections.abc import Mapping
from dataclasses import dataclass, replace

from pacta.model.types import ArchitectureModel, Container


@dataclass(frozen=True, slots=True)
class DefaultModelResolver:
    """
    Computes convenience lookup tables on the model.

    This keeps ArchitectureModel immutable: we return a new instance with populated fields:
      - container_to_context
      - path_roots
      - layer_patterns

    For v2 models with nested containers:
      - Rebuilds the container tree with ``parent`` set on children
      - Children inherit parent ``context`` unless they define their own
      - Populates lookups for all containers (including nested, via containers_flat)
    """

    def resolve(self, model: ArchitectureModel) -> ArchitectureModel:
        # Rebuild container tree with parent pointers and context inheritance
        resolved_containers = _resolve_children(model.containers, parent_qualified_id=None, parent_context=None)

        model = replace(model, containers=resolved_containers)

        container_to_context: dict[str, str] = {}
        path_roots: dict[str, tuple[str, ...]] = {}
        layer_patterns: dict[str, dict[str, tuple[str, ...]]] = {}

        for cid, c in model.containers_flat.items():
            if c.context:
                container_to_context[cid] = c.context

            if c.code is not None:
                roots = tuple(_norm_path(p) for p in c.code.roots if isinstance(p, str) and p.strip())
                path_roots[cid] = tuple(sorted(set(roots)))

                layer_map: dict[str, tuple[str, ...]] = {}
                for layer_id, layer in c.code.layers.items():
                    pats = tuple(_norm_glob(p) for p in layer.patterns if isinstance(p, str) and p.strip())
                    layer_map[layer_id] = tuple(sorted(set(pats)))
                layer_patterns[cid] = dict(sorted(layer_map.items(), key=lambda kv: kv[0]))

        # deterministic ordering for dicts
        container_to_context = dict(sorted(container_to_context.items(), key=lambda kv: kv[0]))
        path_roots = dict(sorted(path_roots.items(), key=lambda kv: kv[0]))
        layer_patterns = dict(sorted(layer_patterns.items(), key=lambda kv: kv[0]))

        return replace(
            model,
            container_to_context=container_to_context,
            path_roots=path_roots,
            layer_patterns=layer_patterns,
        )


def _resolve_children(
    containers: Mapping[str, Container],
    parent_qualified_id: str | None,
    parent_context: str | None,
) -> dict[str, Container]:
    """Recursively rebuild containers with ``parent`` and inherited ``context``."""
    out: dict[str, Container] = {}
    for cid, c in containers.items():
        qualified = f"{parent_qualified_id}.{cid}" if parent_qualified_id else cid
        context = c.context if c.context is not None else parent_context

        resolved_children: dict[str, Container] = {}
        if c.children:
            resolved_children = _resolve_children(c.children, parent_qualified_id=qualified, parent_context=context)

        out[cid] = replace(c, parent=parent_qualified_id, context=context, children=resolved_children)
    return out


def _norm_path(p: str) -> str:
    # Keep it simple and stable across OS:
    # - use forward slashes
    # - strip leading "./"
    s = p.strip().replace("\\", "/")
    while s.startswith("./"):
        s = s[2:]
    return s.rstrip("/") if s != "/" else s


def _norm_glob(p: str) -> str:
    # For globs we keep them mostly intact but normalize slashes.
    return p.strip().replace("\\", "/")
