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

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pacta.model.types import ArchitectureModel, CodeMapping, Container, Context, Layer, Relation


@dataclass(frozen=True, slots=True)
class ModelLoadError(Exception):
    code: str
    message: str
    details: Mapping[str, Any] | None = None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class DefaultArchitectureModelLoader:
    """
    Loads an ArchitectureModel from architecture.yaml / architecture.yml / architecture.json
    """

    def load(self, path: Path) -> ArchitectureModel:
        if not isinstance(path, Path):
            path = Path(path)

        if not path.exists():
            raise ModelLoadError(code="model_not_found", message=f"Model file does not exist: {path}")

        data = self._read_model_file(path)

        if not isinstance(data, dict):
            raise ModelLoadError(code="invalid_model", message="Architecture model root must be a mapping/object.")

        version = data.get("version", 1)
        if not isinstance(version, int):
            raise ModelLoadError(code="invalid_version", message="'version' must be an integer.")

        metadata: dict[str, Any] = {}
        # carry system into metadata (README has system section)
        system = data.get("system")
        if isinstance(system, dict):
            metadata["system"] = dict(system)

        raw_meta = data.get("metadata")
        if isinstance(raw_meta, dict):
            # user-provided metadata wins, but keep system too
            for k, v in raw_meta.items():
                metadata[k] = v

        contexts = self._parse_contexts(data.get("contexts"))
        containers = self._parse_containers(data.get("containers"))

        raw_relations = data.get("relations") if data.get("relations") is not None else data.get("communication") or ()

        relations = self._parse_relations(raw_relations)

        return ArchitectureModel(
            version=version,
            contexts=contexts,
            containers=containers,
            relations=relations,
            metadata=metadata,
        )

    def _read_model_file(self, path: Path) -> Any:
        suffix = path.suffix.lower()
        raw = path.read_text(encoding="utf-8")

        if suffix == ".json":
            return json.loads(raw)

        if suffix in (".yaml", ".yml"):
            try:
                import yaml
            except Exception as e:
                raise ModelLoadError(
                    code="yaml_dependency_missing",
                    message="YAML model requires optional dependency PyYAML.",
                    details={"hint": "pip install pyyaml", "path": str(path)},
                ) from e
            return yaml.safe_load(raw)

        # Unknown extension: try JSON then YAML (if available)
        try:
            return json.loads(raw)
        except Exception:
            try:
                import yaml
            except Exception as e:
                raise ModelLoadError(
                    code="unsupported_extension",
                    message=f"Unsupported model file extension: {path.suffix!s}",
                    details={"supported": [".yaml", ".yml", ".json"]},
                ) from e
            return yaml.safe_load(raw)

    def _parse_contexts(self, raw: Any) -> dict[str, Context]:
        if raw is None:
            return {}

        if not isinstance(raw, dict):
            raise ModelLoadError(code="invalid_contexts", message="'contexts' must be a mapping/object.")

        out: dict[str, Context] = {}
        for ctx_id, spec in raw.items():
            if not isinstance(ctx_id, str) or not ctx_id.strip():
                continue
            if spec is None:
                out[ctx_id] = Context(id=ctx_id)
                continue
            if not isinstance(spec, dict):
                raise ModelLoadError(
                    code="invalid_context",
                    message=f"Context '{ctx_id}' must be an object.",
                )
            out[ctx_id] = Context(
                id=ctx_id,
                name=spec.get("name"),
                description=spec.get("description"),
            )
        return out

    def _parse_containers(self, raw: Any) -> dict[str, Container]:
        if raw is None:
            return {}

        if not isinstance(raw, dict):
            raise ModelLoadError(code="invalid_containers", message="'containers' must be a mapping/object.")

        out: dict[str, Container] = {}
        for cid, spec in raw.items():
            if not isinstance(cid, str) or not cid.strip():
                continue
            if not isinstance(spec, dict):
                raise ModelLoadError(code="invalid_container", message=f"Container '{cid}' must be an object.")

            code = self._parse_code_mapping(spec.get("code"))
            tags = spec.get("tags") or ()
            tags_tuple: tuple[str, ...]
            if isinstance(tags, list):
                tags_tuple = tuple(str(t) for t in tags if str(t))
            elif isinstance(tags, tuple):
                tags_tuple = tuple(str(t) for t in tags if str(t))
            else:
                tags_tuple = ()

            out[cid] = Container(
                id=cid,
                name=spec.get("name"),
                context=spec.get("context"),
                description=spec.get("description"),
                code=code,
                tags=tags_tuple,
            )

        return out

    def _parse_code_mapping(self, raw: Any) -> CodeMapping | None:
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise ModelLoadError(code="invalid_code_mapping", message="'code' must be an object when present.")

        roots_raw = raw.get("roots") or ()
        if isinstance(roots_raw, list):
            roots = tuple(str(x) for x in roots_raw if str(x).strip())
        elif isinstance(roots_raw, tuple):
            roots = tuple(str(x) for x in roots_raw if str(x).strip())
        elif isinstance(roots_raw, str) and roots_raw.strip():
            roots = (roots_raw.strip(),)
        else:
            roots = ()

        layers_raw = raw.get("layers")
        layers = self._parse_layers(layers_raw)

        return CodeMapping(roots=roots, layers=layers)

    def _parse_layers(self, raw: Any) -> dict[str, Layer]:
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise ModelLoadError(code="invalid_layers", message="'layers' must be a mapping/object.")

        out: dict[str, Layer] = {}
        for lid, spec in raw.items():
            if not isinstance(lid, str) or not lid.strip():
                continue

            # Support:
            # layers:
            #   domain: ["**/domain/**", ...]
            # OR:
            #   domain: { patterns: [...], description: "..." }
            if isinstance(spec, list):
                patterns = tuple(str(p) for p in spec if str(p).strip())
                out[lid] = Layer(id=lid, patterns=patterns)
                continue

            if isinstance(spec, dict):
                pats = spec.get("patterns") or spec.get("globs") or spec.get("paths") or ()
                if isinstance(pats, list):
                    patterns = tuple(str(p) for p in pats if str(p).strip())
                elif isinstance(pats, tuple):
                    patterns = tuple(str(p) for p in pats if str(p).strip())
                elif isinstance(pats, str) and pats.strip():
                    patterns = (pats.strip(),)
                else:
                    patterns = ()

                out[lid] = Layer(
                    id=lid,
                    patterns=patterns,
                    description=spec.get("description"),
                )
                continue

            raise ModelLoadError(
                code="invalid_layer_spec",
                message=f"Layer '{lid}' must be a list of patterns or an object.",
            )

        return out

    def _parse_relations(self, raw: Any) -> tuple[Relation, ...]:
        if raw is None:
            return ()

        if raw == ():
            return ()

        if not isinstance(raw, list):
            raise ModelLoadError(code="invalid_relations", message="'relations' must be a list when present.")

        rels: list[Relation] = []
        for item in raw:
            if not isinstance(item, dict):
                continue

            # support "from"/"to" or "from_container"/"to_container"
            fc = item.get("from_container") or item.get("from")
            tc = item.get("to_container") or item.get("to")
            if not isinstance(fc, str) or not isinstance(tc, str) or not fc.strip() or not tc.strip():
                continue

            rels.append(
                Relation(
                    from_container=fc,
                    to_container=tc,
                    protocol=item.get("protocol"),
                    description=item.get("description"),
                )
            )

        return tuple(rels)
