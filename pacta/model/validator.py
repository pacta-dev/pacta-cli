# SPDX-License-Identifier: AGPL-3.0-only
#
# Copyright (c) 2026 Pacta Contributors
#
# This file is part of Pacta.
#
# Pacta is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, version 3 only.
#
# Pacta is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.

from dataclasses import dataclass

from pacta.model.types import ArchitectureModel, Container
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

        # containers
        for cid, c in model.containers.items():
            self._validate_container(model, cid, c, errors)

        # relations reference known containers
        for r in model.relations:
            if r.from_container not in model.containers:
                errors.append(
                    EngineError(
                        type="config_error",
                        message="Relation references unknown from_container.",
                        location=None,
                        details={"from_container": r.from_container},
                    )
                )
            if r.to_container not in model.containers:
                errors.append(
                    EngineError(
                        type="config_error",
                        message="Relation references unknown to_container.",
                        location=None,
                        details={"to_container": r.to_container},
                    )
                )

        return errors

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
