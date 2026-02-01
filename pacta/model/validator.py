from dataclasses import dataclass

from pacta.model.types import ArchitectureModel, Container, ContainerKind
from pacta.reporting.types import EngineError


@dataclass(frozen=True, slots=True)
class DefaultArchitectureModelValidator:
    """
    Structural validation of ArchitectureModel.

    Returns EngineError objects (non-fatal) so engine can proceed even with a broken model.
    """

    def validate(self, model: ArchitectureModel) -> list[EngineError]:
        errors: list[EngineError] = []

        # version sanity
        if model.version <= 0:
            errors.append(
                EngineError(
                    type="config_error",
                    message="Model 'version' must be a positive integer.",
                    location=None,
                    details={"version": model.version},
                )
            )

        # contexts
        for ctx_id, ctx in model.contexts.items():
            if not ctx_id or ctx_id.strip() != ctx_id:
                errors.append(
                    EngineError(
                        type="config_error",
                        message="Context id must be a non-empty trimmed string.",
                        location=None,
                        details={"context_id": ctx_id},
                    )
                )
            if ctx.id != ctx_id:
                errors.append(
                    EngineError(
                        type="config_error",
                        message="Context.id must match map key.",
                        location=None,
                        details={"key": ctx_id, "id": ctx.id},
                    )
                )

        # containers (flat includes nested)
        flat = model.containers_flat
        for cid, c in flat.items():
            self._validate_container(model, cid, c, errors)

        # v2: validate kind and child containment
        if model.version >= 2:
            self._validate_v2_containers(flat, errors)

        # v2: check for duplicate IDs in flat namespace
        # (already impossible if _collect_containers works correctly, but guard against
        # children whose local IDs collide when dot-qualified)

        # relations reference known containers (use flat namespace)
        all_ids = set(flat.keys())
        for r in model.relations:
            if r.from_container not in all_ids:
                errors.append(
                    EngineError(
                        type="config_error",
                        message=f"Relation references unknown from_container '{r.from_container}'."
                        f" Available: {sorted(all_ids)}.",
                        location=None,
                        details={"from_container": r.from_container, "available": sorted(all_ids)},
                    )
                )
            if r.to_container not in all_ids:
                errors.append(
                    EngineError(
                        type="config_error",
                        message=f"Relation references unknown to_container '{r.to_container}'."
                        f" Available: {sorted(all_ids)}.",
                        location=None,
                        details={"to_container": r.to_container, "available": sorted(all_ids)},
                    )
                )

        return errors

    def _validate_v2_containers(
        self,
        flat: dict[str, Container] | object,
        errors: list[EngineError],
    ) -> None:
        for cid, c in flat.items():  # type: ignore[union-attr]
            # kind must be valid
            if c.kind is not None and c.kind not in ContainerKind:
                errors.append(
                    EngineError(
                        type="config_error",
                        message=f"Container '{cid}' has invalid kind '{c.kind}'."
                        f" Must be one of: {', '.join(k.value for k in ContainerKind)}.",
                        location=None,
                        details={"container_id": cid, "kind": str(c.kind)},
                    )
                )

            # child code.roots must be sub-paths of parent code.roots
            if c.parent is not None and c.code is not None:
                parent = flat.get(c.parent)  # type: ignore[union-attr]
                if parent is not None and parent.code is not None:
                    parent_roots = parent.code.roots
                    for root in c.code.roots:
                        if not any(root.startswith(pr) for pr in parent_roots):
                            errors.append(
                                EngineError(
                                    type="config_error",
                                    message=f"Container '{cid}' code root '{root}' is not"
                                    f" under parent '{c.parent}' roots {list(parent_roots)}.",
                                    location=None,
                                    details={
                                        "container_id": cid,
                                        "root": root,
                                        "parent_id": c.parent,
                                        "parent_roots": list(parent_roots),
                                    },
                                )
                            )

    def _validate_container(
        self,
        model: ArchitectureModel,
        cid: str,
        c: Container,
        errors: list[EngineError],
    ) -> None:
        if not cid or cid.strip() != cid:
            errors.append(
                EngineError(
                    type="config_error",
                    message="Container id must be a non-empty trimmed string.",
                    location=None,
                    details={"container_id": cid},
                )
            )
        if c.id != cid:
            errors.append(
                EngineError(
                    type="config_error",
                    message="Container.id must match map key.",
                    location=None,
                    details={"key": cid, "id": c.id},
                )
            )

        if c.context is not None and c.context not in model.contexts:
            errors.append(
                EngineError(
                    type="config_error",
                    message="Container references unknown context.",
                    location=None,
                    details={"container_id": cid, "context": c.context},
                )
            )

        if c.code is None:
            return

        # roots must exist and be non-empty strings (MVP structural check only)
        roots = c.code.roots
        if not isinstance(roots, tuple):
            errors.append(
                EngineError(
                    type="config_error",
                    message="Container.code.roots must be a tuple/list of strings.",
                    location=None,
                    details={"container_id": cid},
                )
            )
        if len(roots) == 0:
            errors.append(
                EngineError(
                    type="config_error",
                    message="Container.code.roots is empty. Provide at least one root path.",
                    location=None,
                    details={"container_id": cid},
                )
            )
        else:
            for r in roots:
                if not isinstance(r, str) or not r.strip():
                    errors.append(
                        EngineError(
                            type="config_error",
                            message="Container.code.roots contains an invalid path.",
                            location=None,
                            details={"container_id": cid, "root": r},
                        )
                    )

        # layers: each layer must have at least one pattern
        for layer_id, layer in c.code.layers.items():
            patterns = layer.patterns
            if not isinstance(patterns, tuple):
                errors.append(
                    EngineError(
                        type="config_error",
                        message="Layer.patterns must be a tuple/list of strings.",
                        location=None,
                        details={"container_id": cid, "layer_id": layer_id},
                    )
                )
                continue
            if len(patterns) == 0:
                errors.append(
                    EngineError(
                        type="config_error",
                        message="Layer.patterns is empty. Provide at least one glob pattern.",
                        location=None,
                        details={"container_id": cid, "layer_id": layer_id},
                    )
                )
                continue
            for p in patterns:
                if not isinstance(p, str) or not p.strip():
                    errors.append(
                        EngineError(
                            type="config_error",
                            message="Layer.patterns contains an invalid glob pattern.",
                            location=None,
                            details={"container_id": cid, "layer_id": layer_id, "pattern": p},
                        )
                    )
