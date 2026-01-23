import json
from pathlib import Path
from typing import Any

import pytest
from pacta.model.loader import DefaultArchitectureModelLoader, ModelLoadError
from pacta.model.resolver import DefaultModelResolver
from pacta.model.types import (
    ArchitectureModel,
    CodeMapping,
    Container,
    Context,
    Layer,
    Relation,
)
from pacta.model.validator import DefaultArchitectureModelValidator

# ----------------------------
# Helpers
# ----------------------------


def write_json(path: Path, obj: Any) -> Path:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    return path


def write_yaml(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def load_model(path: Path) -> ArchitectureModel:
    return DefaultArchitectureModelLoader().load(path)


# ----------------------------
# Loader: happy paths
# ----------------------------


def test_loader_json_minimal(tmp_path: Path):
    f = write_json(
        tmp_path / "architecture.json",
        {
            "version": 1,
            "containers": {},
        },
    )
    m = load_model(f)
    assert m.version == 1
    assert m.contexts == {}
    assert m.containers == {}
    assert m.relations == ()
    assert isinstance(m.metadata, dict)


def test_loader_carries_system_into_metadata(tmp_path: Path):
    f = write_json(
        tmp_path / "architecture.json",
        {
            "version": 1,
            "system": {"id": "my-sys", "name": "My System"},
            "containers": {},
        },
    )
    m = load_model(f)
    assert m.metadata.get("system", {}).get("id") == "my-sys"


def test_loader_parses_contexts_containers_layers_list_and_object_forms(tmp_path: Path):
    f = write_json(
        tmp_path / "architecture.json",
        {
            "version": 1,
            "contexts": {
                "billing": {"name": "Billing"},
                "identity": None,  # allowed
            },
            "containers": {
                "billing-api": {
                    "context": "billing",
                    "code": {
                        "roots": ["services/billing-api"],
                        "layers": {
                            "domain": ["services/billing-api/domain/**", "services/billing-api/core/**"],
                            "infra": {"patterns": ["services/billing-api/infra/**"], "description": "Infra layer"},
                        },
                    },
                    "tags": ["critical", "public"],
                }
            },
        },
    )

    m = load_model(f)

    assert set(m.contexts.keys()) == {"billing", "identity"}
    assert m.contexts["billing"].name == "Billing"
    assert m.contexts["identity"].id == "identity"

    c = m.containers["billing-api"]
    assert c.context == "billing"
    assert c.code is not None
    assert c.code.roots == ("services/billing-api",)

    assert set(c.code.layers.keys()) == {"domain", "infra"}
    assert c.code.layers["domain"].patterns[0].startswith("services/billing-api/")
    assert c.code.layers["infra"].description == "Infra layer"

    assert c.tags == ("critical", "public")


def test_loader_parses_relations_with_from_to_aliases(tmp_path: Path):
    f = write_json(
        tmp_path / "architecture.json",
        {
            "version": 1,
            "containers": {"a": {}, "b": {}},
            "relations": [
                {"from": "a", "to": "b", "protocol": "http", "description": "A calls B"},
                {"from_container": "b", "to_container": "a", "protocol": "event"},
                {"from": "", "to": "b"},  # ignored
                "not-a-dict",  # ignored
            ],
        },
    )
    m = load_model(f)

    assert len(m.relations) == 2
    assert m.relations[0].from_container == "a"
    assert m.relations[0].to_container == "b"
    assert m.relations[0].protocol == "http"


def test_loader_unknown_extension_tries_json_then_yaml(tmp_path: Path):
    # Valid JSON in .txt should load
    f = tmp_path / "architecture.txt"
    f.write_text('{"version": 1, "containers": {}}', encoding="utf-8")
    m = load_model(f)
    assert m.version == 1


def test_loader_yaml_if_available_else_graceful_error(tmp_path: Path):
    f = write_yaml(
        tmp_path / "architecture.yaml",
        """
version: 1
containers:
  svc:
    code:
      roots:
        - services/svc
      layers:
        domain:
          - services/svc/domain/**
""".strip(),
    )

    try:
        m = load_model(f)
    except ModelLoadError as e:
        # If PyYAML isn't installed, this is expected
        assert e.code == "yaml_dependency_missing"
        return

    # If PyYAML is installed, ensure parse succeeded
    assert m.version == 1
    assert "svc" in m.containers
    assert m.containers["svc"].code is not None
    assert "domain" in m.containers["svc"].code.layers


# ----------------------------
# Loader: error cases
# ----------------------------


def test_loader_missing_file_raises(tmp_path: Path):
    f = tmp_path / "missing.json"
    with pytest.raises(ModelLoadError) as ei:
        load_model(f)
    assert ei.value.code == "model_not_found"


def test_loader_root_must_be_object(tmp_path: Path):
    f = tmp_path / "architecture.json"
    f.write_text("[]", encoding="utf-8")
    with pytest.raises(ModelLoadError) as ei:
        load_model(f)
    assert ei.value.code == "invalid_model"


def test_loader_version_must_be_int(tmp_path: Path):
    f = write_json(tmp_path / "architecture.json", {"version": "1", "containers": {}})
    with pytest.raises(ModelLoadError) as ei:
        load_model(f)
    assert ei.value.code == "invalid_version"


def test_loader_contexts_must_be_object(tmp_path: Path):
    f = write_json(tmp_path / "architecture.json", {"version": 1, "contexts": [], "containers": {}})
    with pytest.raises(ModelLoadError) as ei:
        load_model(f)
    assert ei.value.code == "invalid_contexts"


def test_loader_containers_must_be_object(tmp_path: Path):
    f = write_json(tmp_path / "architecture.json", {"version": 1, "containers": []})
    with pytest.raises(ModelLoadError) as ei:
        load_model(f)
    assert ei.value.code == "invalid_containers"


def test_loader_container_must_be_object(tmp_path: Path):
    f = write_json(tmp_path / "architecture.json", {"version": 1, "containers": {"svc": "bad"}})
    with pytest.raises(ModelLoadError) as ei:
        load_model(f)
    assert ei.value.code == "invalid_container"


def test_loader_code_mapping_must_be_object(tmp_path: Path):
    f = write_json(tmp_path / "architecture.json", {"version": 1, "containers": {"svc": {"code": "nope"}}})
    with pytest.raises(ModelLoadError) as ei:
        load_model(f)
    assert ei.value.code == "invalid_code_mapping"


def test_loader_layers_must_be_object(tmp_path: Path):
    f = write_json(
        tmp_path / "architecture.json",
        {"version": 1, "containers": {"svc": {"code": {"roots": ["x"], "layers": []}}}},
    )
    with pytest.raises(ModelLoadError) as ei:
        load_model(f)
    assert ei.value.code == "invalid_layers"


def test_loader_layer_spec_must_be_list_or_object(tmp_path: Path):
    f = write_json(
        tmp_path / "architecture.json",
        {"version": 1, "containers": {"svc": {"code": {"roots": ["x"], "layers": {"domain": "bad"}}}}},
    )
    with pytest.raises(ModelLoadError) as ei:
        load_model(f)
    assert ei.value.code == "invalid_layer_spec"


def test_loader_relations_must_be_list(tmp_path: Path):
    f = write_json(tmp_path / "architecture.json", {"version": 1, "containers": {}, "relations": {}})
    with pytest.raises(ModelLoadError) as ei:
        load_model(f)
    assert ei.value.code == "invalid_relations"


# ----------------------------
# Validator tests
# ----------------------------


def test_validator_ok_model_has_no_errors():
    m = ArchitectureModel(
        version=1,
        contexts={"ctx": Context(id="ctx")},
        containers={
            "svc": Container(
                id="svc",
                context="ctx",
                code=CodeMapping(
                    roots=("services/svc",),
                    layers={"domain": Layer(id="domain", patterns=("services/svc/domain/**",))},
                ),
            )
        },
        relations=(Relation(from_container="svc", to_container="svc", protocol="http"),),
        metadata={},
    )
    errs = DefaultArchitectureModelValidator().validate(m)
    assert errs == []


def test_validator_reports_unknown_context_reference():
    m = ArchitectureModel(
        version=1,
        contexts={},  # empty
        containers={"svc": Container(id="svc", context="missing")},
        relations=(),
        metadata={},
    )
    errs = DefaultArchitectureModelValidator().validate(m)
    assert any(e.type == "config_error" and "unknown context" in e.message.lower() for e in errs)


def test_validator_reports_empty_roots_and_empty_layer_patterns():
    m = ArchitectureModel(
        version=1,
        contexts={},
        containers={
            "svc": Container(
                id="svc",
                code=CodeMapping(
                    roots=(),
                    layers={"domain": Layer(id="domain", patterns=())},
                ),
            )
        },
        relations=(),
        metadata={},
    )
    errs = DefaultArchitectureModelValidator().validate(m)
    # two different issues
    assert any("roots is empty" in e.message.lower() for e in errs)
    assert any("patterns is empty" in e.message.lower() for e in errs)


def test_validator_reports_relation_unknown_container():
    m = ArchitectureModel(
        version=1,
        contexts={},
        containers={"a": Container(id="a")},
        relations=(Relation(from_container="a", to_container="missing"),),
        metadata={},
    )
    errs = DefaultArchitectureModelValidator().validate(m)
    assert any("unknown to_container" in e.message.lower() for e in errs)


# ----------------------------
# Resolver tests
# ----------------------------


def test_resolver_builds_lookups_normalizes_dedupes_and_sorts():
    m = ArchitectureModel(
        version=1,
        contexts={"ctx": Context(id="ctx")},
        containers={
            "svc": Container(
                id="svc",
                context="ctx",
                code=CodeMapping(
                    roots=("./services\\svc/", "services/svc", "services/svc/"),
                    layers={
                        "domain": Layer(id="domain", patterns=("services\\svc\\domain/**", "services/svc/domain/**")),
                        "infra": Layer(id="infra", patterns=(" ./services/svc/infra/** ",)),
                    },
                ),
            )
        },
        relations=(),
        metadata={},
    )

    resolved = DefaultModelResolver().resolve(m)

    # container_to_context
    assert resolved.container_to_context == {"svc": "ctx"}

    # path_roots normalized + deduped + sorted
    assert resolved.path_roots["svc"] == ("services/svc",)

    # layer_patterns normalized + deduped + sorted by layer id + patterns
    lp = resolved.layer_patterns["svc"]
    assert list(lp.keys()) == ["domain", "infra"]
    assert lp["domain"] == ("services/svc/domain/**",)
    assert (
        lp["infra"] == ("./services/svc/infra/**",)
        or lp["infra"] == ("services/svc/infra/**",)
        or lp["infra"] == ("./services/svc/infra/**".lstrip("./"),)
    )


def test_resolver_deterministic_ordering_with_multiple_containers():
    m = ArchitectureModel(
        version=1,
        contexts={"c": Context(id="c")},
        containers={
            "z": Container(id="z", context="c", code=CodeMapping(roots=("b",), layers={})),
            "a": Container(id="a", context="c", code=CodeMapping(roots=("a",), layers={})),
        },
        relations=(),
        metadata={},
    )

    resolved = DefaultModelResolver().resolve(m)

    # Sorted by container id
    assert list(resolved.path_roots.keys()) == ["a", "z"]
    assert list(resolved.container_to_context.keys()) == ["a", "z"]
