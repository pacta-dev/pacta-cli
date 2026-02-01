from pacta.ir.types import (
    ArchitectureIR,
    CanonicalId,
    DepType,
    IREdge,
    IRNode,
    Language,
    SymbolKind,
)
from pacta.mapping.enricher import DefaultArchitectureEnricher
from pacta.model.resolver import DefaultModelResolver
from pacta.model.types import (
    ArchitectureModel,
    CodeMapping,
    Container,
    ContainerKind,
    Context,
    Layer,
)

# ----------------------------
# Test Fixtures
# ----------------------------


def build_test_model() -> ArchitectureModel:
    """
    Build a test architecture model with:
      - Two contexts: billing, identity
      - Two containers: billing-api, identity-service
      - Four layers: ui, application, domain, infra
    """
    contexts = {
        "billing": Context(id="billing", name="Billing Context"),
        "identity": Context(id="identity", name="Identity Context"),
    }

    containers = {
        "billing-api": Container(
            id="billing-api",
            name="Billing API",
            context="billing",
            code=CodeMapping(
                roots=("services/billing-api",),
                layers={
                    "ui": Layer(
                        id="ui",
                        patterns=("services/billing-api/api/**",),
                    ),
                    "application": Layer(
                        id="application",
                        patterns=("services/billing-api/app/**",),
                    ),
                    "domain": Layer(
                        id="domain",
                        patterns=("services/billing-api/domain/**",),
                    ),
                    "infra": Layer(
                        id="infra",
                        patterns=("services/billing-api/infra/**",),
                    ),
                },
            ),
            tags=("critical", "public-api"),
        ),
        "identity-service": Container(
            id="identity-service",
            name="Identity Service",
            context="identity",
            code=CodeMapping(
                roots=("services/identity",),
                layers={
                    "domain": Layer(
                        id="domain",
                        patterns=("services/identity/core/**",),
                    ),
                    "infra": Layer(
                        id="infra",
                        patterns=("services/identity/db/**",),
                    ),
                },
            ),
            tags=("critical",),
        ),
    }

    model = ArchitectureModel(
        version=1,
        contexts=contexts,
        containers=containers,
        relations=(),
        metadata={},
    )

    # Resolve lookups
    return DefaultModelResolver().resolve(model)


def build_test_ir() -> ArchitectureIR:
    """
    Build a test IR with nodes and edges.
    """
    nodes = (
        IRNode(
            id=CanonicalId(
                language=Language.PYTHON,
                code_root="billing-api",
                fqname="services.billing.api.routes",
            ),
            kind=SymbolKind.MODULE,
            name="routes",
            path="services/billing-api/api/routes.py",
        ),
        IRNode(
            id=CanonicalId(
                language=Language.PYTHON,
                code_root="billing-api",
                fqname="services.billing.domain.invoice",
            ),
            kind=SymbolKind.MODULE,
            name="invoice",
            path="services/billing-api/domain/invoice.py",
        ),
        IRNode(
            id=CanonicalId(
                language=Language.PYTHON,
                code_root="billing-api",
                fqname="services.billing.infra.db",
            ),
            kind=SymbolKind.MODULE,
            name="db",
            path="services/billing-api/infra/db.py",
        ),
        IRNode(
            id=CanonicalId(
                language=Language.PYTHON,
                code_root="identity",
                fqname="services.identity.core.user",
            ),
            kind=SymbolKind.MODULE,
            name="user",
            path="services/identity/core/user.py",
        ),
        IRNode(
            id=CanonicalId(
                language=Language.PYTHON,
                code_root="other",
                fqname="lib.utils",
            ),
            kind=SymbolKind.MODULE,
            name="utils",
            path="lib/utils.py",
        ),
    )

    edges = (
        IREdge(
            src=nodes[0].id,  # api.routes
            dst=nodes[1].id,  # domain.invoice
            dep_type=DepType.IMPORT,
        ),
        IREdge(
            src=nodes[1].id,  # domain.invoice
            dst=nodes[2].id,  # infra.db
            dep_type=DepType.IMPORT,
        ),
        IREdge(
            src=nodes[0].id,  # api.routes
            dst=nodes[3].id,  # identity.core.user
            dep_type=DepType.IMPORT,
        ),
    )

    return ArchitectureIR(
        schema_version=1,
        produced_by="test",
        repo_root="/test",
        nodes=nodes,
        edges=edges,
        metadata={},
    )


# ----------------------------
# Enricher Tests
# ----------------------------


def test_enricher_enriches_nodes_with_container_layer_context_tags():
    model = build_test_model()
    ir = build_test_ir()
    enricher = DefaultArchitectureEnricher()

    enriched = enricher.enrich(ir, model)

    # Check node 0: services/billing-api/api/routes.py
    n0 = enriched.nodes[0]
    assert n0.container == "billing-api"
    assert n0.layer == "ui"
    assert n0.context == "billing"
    assert n0.tags == ("critical", "public-api")

    # Check node 1: services/billing-api/domain/invoice.py
    n1 = enriched.nodes[1]
    assert n1.container == "billing-api"
    assert n1.layer == "domain"
    assert n1.context == "billing"
    assert n1.tags == ("critical", "public-api")

    # Check node 2: services/billing-api/infra/db.py
    n2 = enriched.nodes[2]
    assert n2.container == "billing-api"
    assert n2.layer == "infra"
    assert n2.context == "billing"
    assert n2.tags == ("critical", "public-api")

    # Check node 3: services/identity/core/user.py
    n3 = enriched.nodes[3]
    assert n3.container == "identity-service"
    assert n3.layer == "domain"
    assert n3.context == "identity"
    assert n3.tags == ("critical",)

    # Check node 4: lib/utils.py (no match)
    n4 = enriched.nodes[4]
    assert n4.container is None
    assert n4.layer is None
    assert n4.context is None
    assert n4.tags == ()


def test_enricher_enriches_edges_with_src_dst_metadata():
    model = build_test_model()
    ir = build_test_ir()
    enricher = DefaultArchitectureEnricher()

    enriched = enricher.enrich(ir, model)

    # Edge 0: api.routes -> domain.invoice (both in billing-api)
    e0 = enriched.edges[0]
    assert e0.src_container == "billing-api"
    assert e0.src_layer == "ui"
    assert e0.src_context == "billing"
    assert e0.dst_container == "billing-api"
    assert e0.dst_layer == "domain"
    assert e0.dst_context == "billing"

    # Edge 1: domain.invoice -> infra.db (both in billing-api)
    e1 = enriched.edges[1]
    assert e1.src_container == "billing-api"
    assert e1.src_layer == "domain"
    assert e1.src_context == "billing"
    assert e1.dst_container == "billing-api"
    assert e1.dst_layer == "infra"
    assert e1.dst_context == "billing"

    # Edge 2: api.routes (billing-api) -> identity.core.user (identity-service)
    e2 = enriched.edges[2]
    assert e2.src_container == "billing-api"
    assert e2.src_layer == "ui"
    assert e2.src_context == "billing"
    assert e2.dst_container == "identity-service"
    assert e2.dst_layer == "domain"
    assert e2.dst_context == "identity"


def test_enricher_prefers_longest_matching_root():
    """
    Test that enricher prefers the longest (most specific) root match.
    """
    contexts = {"ctx": Context(id="ctx")}
    containers = {
        "root-container": Container(
            id="root-container",
            context="ctx",
            code=CodeMapping(
                roots=("services",),
                layers={},
            ),
        ),
        "specific-container": Container(
            id="specific-container",
            context="ctx",
            code=CodeMapping(
                roots=("services/billing",),
                layers={},
            ),
        ),
    }
    model = ArchitectureModel(
        version=1,
        contexts=contexts,
        containers=containers,
        relations=(),
        metadata={},
    )
    model = DefaultModelResolver().resolve(model)

    node = IRNode(
        id=CanonicalId(
            language=Language.PYTHON,
            code_root="test",
            fqname="services.billing.invoice",
        ),
        kind=SymbolKind.MODULE,
        path="services/billing/invoice.py",
    )

    ir = ArchitectureIR(
        schema_version=1,
        produced_by="test",
        repo_root="/test",
        nodes=(node,),
        edges=(),
        metadata={},
    )

    enricher = DefaultArchitectureEnricher()
    enriched = enricher.enrich(ir, model)

    # Should match "specific-container" (longer root)
    assert enriched.nodes[0].container == "specific-container"


def test_enricher_handles_node_without_path():
    """
    Test that nodes without path are not enriched with container/layer.
    """
    model = build_test_model()
    node = IRNode(
        id=CanonicalId(
            language=Language.PYTHON,
            code_root="test",
            fqname="unknown",
        ),
        kind=SymbolKind.MODULE,
        path=None,  # No path
    )

    ir = ArchitectureIR(
        schema_version=1,
        produced_by="test",
        repo_root="/test",
        nodes=(node,),
        edges=(),
        metadata={},
    )

    enricher = DefaultArchitectureEnricher()
    enriched = enricher.enrich(ir, model)

    assert enriched.nodes[0].container is None
    assert enriched.nodes[0].layer is None
    assert enriched.nodes[0].context is None


def test_enricher_normalizes_paths_with_backslashes_and_leading_dot_slash():
    """
    Test that path normalization works correctly (cross-platform).
    """
    contexts = {"ctx": Context(id="ctx")}
    containers = {
        "svc": Container(
            id="svc",
            context="ctx",
            code=CodeMapping(
                roots=("services/billing",),
                layers={
                    "domain": Layer(
                        id="domain",
                        patterns=("services/billing/domain/**",),
                    ),
                },
            ),
        ),
    }
    model = ArchitectureModel(
        version=1,
        contexts=contexts,
        containers=containers,
        relations=(),
        metadata={},
    )
    model = DefaultModelResolver().resolve(model)

    # Node with Windows-style path
    node = IRNode(
        id=CanonicalId(
            language=Language.PYTHON,
            code_root="test",
            fqname="services.billing.domain.invoice",
        ),
        kind=SymbolKind.MODULE,
        path=".\\services\\billing\\domain\\invoice.py",  # Windows style
    )

    ir = ArchitectureIR(
        schema_version=1,
        produced_by="test",
        repo_root="/test",
        nodes=(node,),
        edges=(),
        metadata={},
    )

    enricher = DefaultArchitectureEnricher()
    enriched = enricher.enrich(ir, model)

    # Should normalize and match correctly
    assert enriched.nodes[0].container == "svc"
    assert enriched.nodes[0].layer == "domain"


def test_enricher_returns_same_ir_if_no_model():
    """
    Test that enricher handles empty model gracefully.
    """
    model = ArchitectureModel(
        version=1,
        contexts={},
        containers={},
        relations=(),
        metadata={},
    )
    model = DefaultModelResolver().resolve(model)

    ir = build_test_ir()
    enricher = DefaultArchitectureEnricher()
    enriched = enricher.enrich(ir, model)

    # All nodes should have no enrichment
    for node in enriched.nodes:
        assert node.container is None
        assert node.layer is None
        assert node.context is None
        assert node.tags == ()


def test_enricher_handles_edge_with_missing_nodes():
    """
    Test that enricher handles edges where src/dst nodes don't exist in IR.
    """
    model = build_test_model()

    # Create an edge with non-existent nodes
    edge = IREdge(
        src=CanonicalId(
            language=Language.PYTHON,
            code_root="test",
            fqname="nonexistent.src",
        ),
        dst=CanonicalId(
            language=Language.PYTHON,
            code_root="test",
            fqname="nonexistent.dst",
        ),
        dep_type=DepType.IMPORT,
    )

    ir = ArchitectureIR(
        schema_version=1,
        produced_by="test",
        repo_root="/test",
        nodes=(),  # No nodes
        edges=(edge,),
        metadata={},
    )

    enricher = DefaultArchitectureEnricher()
    enriched = enricher.enrich(ir, model)

    # Edge should have no enrichment
    assert enriched.edges[0].src_container is None
    assert enriched.edges[0].src_layer is None
    assert enriched.edges[0].src_context is None
    assert enriched.edges[0].dst_container is None
    assert enriched.edges[0].dst_layer is None
    assert enriched.edges[0].dst_context is None


def test_enricher_layer_matching_respects_order():
    """
    Test that first matching layer wins if multiple patterns match.
    """
    contexts = {"ctx": Context(id="ctx")}
    containers = {
        "svc": Container(
            id="svc",
            context="ctx",
            code=CodeMapping(
                roots=("services/app",),
                layers={
                    "broad": Layer(
                        id="broad",
                        patterns=("services/app/**",),  # Matches everything
                    ),
                    "specific": Layer(
                        id="specific",
                        patterns=("services/app/domain/**",),  # More specific
                    ),
                },
            ),
        ),
    }
    model = ArchitectureModel(
        version=1,
        contexts=contexts,
        containers=containers,
        relations=(),
        metadata={},
    )
    model = DefaultModelResolver().resolve(model)

    node = IRNode(
        id=CanonicalId(
            language=Language.PYTHON,
            code_root="test",
            fqname="services.app.domain.entity",
        ),
        kind=SymbolKind.MODULE,
        path="services/app/domain/entity.py",
    )

    ir = ArchitectureIR(
        schema_version=1,
        produced_by="test",
        repo_root="/test",
        nodes=(node,),
        edges=(),
        metadata={},
    )

    enricher = DefaultArchitectureEnricher()
    enriched = enricher.enrich(ir, model)

    # Should match "broad" (first in deterministic order)
    # ModelResolver sorts layers by id, so "broad" comes before "specific"
    assert enriched.nodes[0].layer == "broad"


def test_enricher_immutability():
    """
    Test that original IR is not mutated.
    """
    model = build_test_model()
    ir = build_test_ir()
    enricher = DefaultArchitectureEnricher()

    # Store original values
    original_node_container = ir.nodes[0].container
    original_edge_src_container = ir.edges[0].src_container

    enriched = enricher.enrich(ir, model)

    # Original IR should be unchanged
    assert ir.nodes[0].container == original_node_container
    assert ir.edges[0].src_container == original_edge_src_container

    # Enriched IR should have new values
    assert enriched.nodes[0].container == "billing-api"
    assert enriched.edges[0].src_container == "billing-api"


def test_enricher_exact_root_match():
    """
    Test that exact root path matches (not just prefix).
    """
    contexts = {"ctx": Context(id="ctx")}
    containers = {
        "svc": Container(
            id="svc",
            context="ctx",
            code=CodeMapping(
                roots=("services/billing-api",),
                layers={},
            ),
        ),
    }
    model = ArchitectureModel(
        version=1,
        contexts=contexts,
        containers=containers,
        relations=(),
        metadata={},
    )
    model = DefaultModelResolver().resolve(model)

    # Node at exact root
    node1 = IRNode(
        id=CanonicalId(
            language=Language.PYTHON,
            code_root="test",
            fqname="services.billing_api.__init__",
        ),
        kind=SymbolKind.MODULE,
        path="services/billing-api",
    )

    # Node in subdirectory
    node2 = IRNode(
        id=CanonicalId(
            language=Language.PYTHON,
            code_root="test",
            fqname="services.billing_api.api",
        ),
        kind=SymbolKind.MODULE,
        path="services/billing-api/api",
    )

    # Node with prefix but not subdirectory (should NOT match)
    node3 = IRNode(
        id=CanonicalId(
            language=Language.PYTHON,
            code_root="test",
            fqname="services.billing_api_v2",
        ),
        kind=SymbolKind.MODULE,
        path="services/billing-api-v2/main.py",
    )

    ir = ArchitectureIR(
        schema_version=1,
        produced_by="test",
        repo_root="/test",
        nodes=(node1, node2, node3),
        edges=(),
        metadata={},
    )

    enricher = DefaultArchitectureEnricher()
    enriched = enricher.enrich(ir, model)

    # node1: exact match
    assert enriched.nodes[0].container == "svc"

    # node2: subdirectory match
    assert enriched.nodes[1].container == "svc"

    # node3: prefix but not subdirectory - should NOT match
    assert enriched.nodes[2].container is None


# ----------------------------
# v2: Nested container enrichment
# ----------------------------


def build_v2_test_model() -> ArchitectureModel:
    """Build a v2 model with nested containers for enrichment tests."""
    contexts = {
        "billing": Context(id="billing", name="Billing Context"),
    }
    containers = {
        "billing-service": Container(
            id="billing-service",
            kind=ContainerKind.SERVICE,
            context="billing",
            code=CodeMapping(
                roots=("services/billing",),
                layers={
                    "api": Layer(id="api", patterns=("services/billing/api/**",)),
                    "domain": Layer(id="domain", patterns=("services/billing/domain/**",)),
                },
            ),
            tags=("critical",),
            children={
                "invoice-module": Container(
                    id="invoice-module",
                    kind=ContainerKind.MODULE,
                    code=CodeMapping(
                        roots=("services/billing/domain/invoice",),
                        layers={
                            "model": Layer(id="model", patterns=("services/billing/domain/invoice/model/**",)),
                            "repo": Layer(id="repo", patterns=("services/billing/domain/invoice/repo/**",)),
                        },
                    ),
                ),
            },
        ),
        "shared-utils": Container(
            id="shared-utils",
            kind=ContainerKind.LIBRARY,
            code=CodeMapping(
                roots=("libs/shared",),
                layers={},
            ),
        ),
    }
    model = ArchitectureModel(
        version=2,
        contexts=contexts,
        containers=containers,
        relations=(),
        metadata={},
    )
    return DefaultModelResolver().resolve(model)


def test_enricher_v2_nested_container_deepest_match():
    """Nested container with more specific root wins over parent."""
    model = build_v2_test_model()

    node = IRNode(
        id=CanonicalId(language=Language.PYTHON, code_root="billing", fqname="invoice.model.entity"),
        kind=SymbolKind.MODULE,
        path="services/billing/domain/invoice/model/entity.py",
    )
    ir = ArchitectureIR(
        schema_version=2, produced_by="test", repo_root="/test",
        nodes=(node,), edges=(), metadata={},
    )

    enriched = DefaultArchitectureEnricher().enrich(ir, model)
    n = enriched.nodes[0]

    # Should match the nested container (longer root)
    assert n.container == "billing-service.invoice-module"
    assert n.layer == "model"
    assert n.context == "billing"  # inherited from parent
    assert n.service == "billing-service"
    assert n.container_kind == "module"


def test_enricher_v2_parent_container_match():
    """Node under parent root but not nested child root matches parent."""
    model = build_v2_test_model()

    node = IRNode(
        id=CanonicalId(language=Language.PYTHON, code_root="billing", fqname="billing.api.routes"),
        kind=SymbolKind.MODULE,
        path="services/billing/api/routes.py",
    )
    ir = ArchitectureIR(
        schema_version=2, produced_by="test", repo_root="/test",
        nodes=(node,), edges=(), metadata={},
    )

    enriched = DefaultArchitectureEnricher().enrich(ir, model)
    n = enriched.nodes[0]

    assert n.container == "billing-service"
    assert n.layer == "api"
    assert n.service == "billing-service"
    assert n.container_kind == "service"


def test_enricher_v2_library_container():
    """Library container sets container_kind correctly."""
    model = build_v2_test_model()

    node = IRNode(
        id=CanonicalId(language=Language.PYTHON, code_root="shared", fqname="libs.shared.util"),
        kind=SymbolKind.MODULE,
        path="libs/shared/util.py",
    )
    ir = ArchitectureIR(
        schema_version=2, produced_by="test", repo_root="/test",
        nodes=(node,), edges=(), metadata={},
    )

    enriched = DefaultArchitectureEnricher().enrich(ir, model)
    n = enriched.nodes[0]

    assert n.container == "shared-utils"
    assert n.service == "shared-utils"
    assert n.container_kind == "library"


def test_enricher_v2_edge_service_and_kind():
    """Edges get src/dst service and container_kind from enriched nodes."""
    model = build_v2_test_model()

    src_node = IRNode(
        id=CanonicalId(language=Language.PYTHON, code_root="billing", fqname="billing.api.routes"),
        kind=SymbolKind.MODULE,
        path="services/billing/api/routes.py",
    )
    dst_node = IRNode(
        id=CanonicalId(language=Language.PYTHON, code_root="shared", fqname="libs.shared.util"),
        kind=SymbolKind.MODULE,
        path="libs/shared/util.py",
    )
    edge = IREdge(src=src_node.id, dst=dst_node.id, dep_type=DepType.IMPORT)

    ir = ArchitectureIR(
        schema_version=2, produced_by="test", repo_root="/test",
        nodes=(src_node, dst_node), edges=(edge,), metadata={},
    )

    enriched = DefaultArchitectureEnricher().enrich(ir, model)
    e = enriched.edges[0]

    assert e.src_service == "billing-service"
    assert e.src_container_kind == "service"
    assert e.dst_service == "shared-utils"
    assert e.dst_container_kind == "library"


def test_enricher_v2_unmatched_node_has_no_service():
    """Nodes that don't match any container have None for service/container_kind."""
    model = build_v2_test_model()

    node = IRNode(
        id=CanonicalId(language=Language.PYTHON, code_root="other", fqname="lib.utils"),
        kind=SymbolKind.MODULE,
        path="other/utils.py",
    )
    ir = ArchitectureIR(
        schema_version=2, produced_by="test", repo_root="/test",
        nodes=(node,), edges=(), metadata={},
    )

    enriched = DefaultArchitectureEnricher().enrich(ir, model)
    n = enriched.nodes[0]

    assert n.container is None
    assert n.service is None
    assert n.container_kind is None
