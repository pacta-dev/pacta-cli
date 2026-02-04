"""
Tests for v2 schema 'kind' and 'within' fields in rule evaluation.

These tests verify that rules using from.kind/to.kind and from.within/to.within
work correctly with nested containers (service -> module hierarchy).

Field semantics:
- `kind` = immediate container's kind (module, service, library)
- `within` = top-level container's kind (for nested containers)

Example: code in billing-service.invoice-module has:
- kind = 'module' (immediate container)
- within = 'service' (top-level container)
"""

from pacta.ir.types import (
    ArchitectureIR,
    CanonicalId,
    DepType,
    IREdge,
    IRNode,
    Language,
    SourceLoc,
    SourcePos,
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
from pacta.rules.compiler import RulesCompiler
from pacta.rules.evaluator import DefaultRuleEvaluator
from pacta.rules.parser import DslRulesParserV0


def build_microservices_model() -> ArchitectureModel:
    """
    Build a realistic v2 model mimicking microservices-platform example:
    - billing-service (kind: service) with nested invoice-module (kind: module)
    - shared-utils (kind: library)
    """
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
            children={
                "invoice-module": Container(
                    id="invoice-module",
                    kind=ContainerKind.MODULE,
                    code=CodeMapping(
                        roots=("services/billing/domain/invoice",),
                        layers={
                            "model": Layer(id="model", patterns=("services/billing/domain/invoice/model/**",)),
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


def cid(fqname: str, code_root: str = "test") -> CanonicalId:
    return CanonicalId(language=Language.PYTHON, code_root=code_root, fqname=fqname)


def make_node(fqname: str, path: str) -> IRNode:
    return IRNode(
        id=cid(fqname),
        kind=SymbolKind.MODULE,
        name=fqname.split(".")[-1],
        path=path,
    )


def make_edge(src_node: IRNode, dst_node: IRNode, loc_file: str) -> IREdge:
    return IREdge(
        src=src_node.id,
        dst=dst_node.id,
        dep_type=DepType.IMPORT,
        loc=SourceLoc(file=loc_file, start=SourcePos(line=1, column=1)),
    )


def compile_and_evaluate(ir: ArchitectureIR, rules_yaml: str) -> list:
    """Parse rules, compile, and evaluate against IR.

    NOTE: Parser expects 'rule:' block format, not 'rules:' list format!
    """
    parser = DslRulesParserV0()
    compiler = RulesCompiler()
    evaluator = DefaultRuleEvaluator()

    ast = parser.parse_text(rules_yaml, filename="test_rules.yml")
    ruleset = compiler.compile(ast)
    return list(evaluator.evaluate(ir, ruleset))


def test_library_to_service_via_nested_module_using_within():
    model = build_microservices_model()

    # Library file
    library_node = make_node("libs.shared.money", "libs/shared/money.py")
    # Service file (inside nested module)
    service_node = make_node(
        "services.billing.domain.invoice.model.invoice",
        "services/billing/domain/invoice/model/invoice.py",
    )
    # Edge: library -> service code
    edge = make_edge(library_node, service_node, "libs/shared/money.py")

    ir = ArchitectureIR(
        schema_version=2,
        produced_by="test",
        repo_root="/test",
        nodes=(library_node, service_node),
        edges=(edge,),
    )

    enriched_ir = DefaultArchitectureEnricher().enrich(ir, model)

    # Verify enrichment: kind is immediate, within is top-level
    enriched_edge = enriched_ir.edges[0]
    assert enriched_edge.src_container_kind == "library", "Source kind should be library"
    assert enriched_edge.dst_container_kind == "module", "Dest kind should be module (immediate)"
    assert enriched_edge.src_within == "library", "Source within should be library"
    assert enriched_edge.dst_within == "service", "Dest within should be service (top-level)"

    rules_yaml = """
rule:
  id: library-no-service-deps
  name: Libraries must not depend on services
  severity: error
  target: dependency
  action: forbid
  when:
    all:
      - from.within == library
      - to.within == service
  message: Library must not import service code
"""

    violations = compile_and_evaluate(enriched_ir, rules_yaml)

    # Using 'within' correctly catches the violation
    assert len(violations) == 1, (
        f"Expected 1 violation for library->service dependency, got {len(violations)}. "
        f"Edge: src_within={enriched_edge.src_within}, dst_within={enriched_edge.dst_within}"
    )


def test_package_import_without_path_has_no_within():
    model = build_microservices_model()

    library_node = make_node("libs.shared.money", "libs/shared/money.py")
    # Package import - no specific file path
    service_package_node = IRNode(
        id=cid("services.billing"),
        kind=SymbolKind.PACKAGE,
        name="billing",
        path=None,  # Package imports don't have a specific file
    )
    edge = make_edge(library_node, service_package_node, "libs/shared/money.py")

    ir = ArchitectureIR(
        schema_version=2,
        produced_by="test",
        repo_root="/test",
        nodes=(library_node, service_package_node),
        edges=(edge,),
    )

    enriched_ir = DefaultArchitectureEnricher().enrich(ir, model)
    enriched_edge = enriched_ir.edges[0]

    # No path means no container matching - both kind and within are None
    assert enriched_edge.dst_container_kind is None, "Package imports have no container_kind"
    assert enriched_edge.dst_within is None, "Package imports have no within"

    # Source is still enriched correctly
    assert enriched_edge.src_container_kind == "library"
    assert enriched_edge.src_within == "library"


def test_kind_vs_within_difference():
    """
    Demonstrate the difference between 'kind' and 'within':
    - kind = immediate container's kind
    - within = top-level container's kind
    """
    model = build_microservices_model()

    library_node = make_node("libs.shared.money", "libs/shared/money.py")
    service_node = make_node(
        "services.billing.domain.invoice.model.invoice",
        "services/billing/domain/invoice/model/invoice.py",
    )
    edge = make_edge(library_node, service_node, "libs/shared/money.py")

    ir = ArchitectureIR(
        schema_version=2,
        produced_by="test",
        repo_root="/test",
        nodes=(library_node, service_node),
        edges=(edge,),
    )

    enriched_ir = DefaultArchitectureEnricher().enrich(ir, model)
    enriched_edge = enriched_ir.edges[0]

    # For library (top-level container): kind == within
    assert enriched_edge.src_container_kind == "library"
    assert enriched_edge.src_within == "library"

    # For nested module: kind != within
    assert enriched_edge.dst_container_kind == "module"  # immediate
    assert enriched_edge.dst_within == "service"  # top-level


def test_node_enrichment_nested_module_has_kind_and_within():
    """
    Verify that nodes inside nested containers have both kind and within set correctly.
    """
    model = build_microservices_model()

    service_node = make_node(
        "services.billing.domain.invoice.model.invoice",
        "services/billing/domain/invoice/model/invoice.py",
    )

    ir = ArchitectureIR(
        schema_version=2,
        produced_by="test",
        repo_root="/test",
        nodes=(service_node,),
        edges=(),
    )

    enriched_ir = DefaultArchitectureEnricher().enrich(ir, model)
    node = enriched_ir.nodes[0]

    # Container hierarchy
    assert node.container == "billing-service.invoice-module"
    assert node.service == "billing-service"

    # kind = immediate container's kind
    assert node.container_kind == "module"

    # within = top-level container's kind
    assert node.within == "service"


def test_kind_rule_does_not_match_nested_module():
    """
    Demonstrate that `to.kind == service` does NOT match nested modules.

    Use `to.within == service` instead if you want to match any code
    inside a service hierarchy.
    """
    model = build_microservices_model()

    library_node = make_node("libs.shared.money", "libs/shared/money.py")
    nested_module_node = make_node(
        "services.billing.domain.invoice.model.invoice",
        "services/billing/domain/invoice/model/invoice.py",
    )
    edge = make_edge(library_node, nested_module_node, "libs/shared/money.py")

    ir = ArchitectureIR(
        schema_version=2,
        produced_by="test",
        repo_root="/test",
        nodes=(library_node, nested_module_node),
        edges=(edge,),
    )

    enriched_ir = DefaultArchitectureEnricher().enrich(ir, model)
    enriched_edge = enriched_ir.edges[0]

    # to.kind is 'module' (immediate container)
    assert enriched_edge.dst_container_kind == "module"

    # Rule with to.kind == service will NOT match (by design)
    rules_yaml = """
rule:
  id: library-no-service-deps
  name: Test
  severity: error
  target: dependency
  action: forbid
  when:
    all:
      - from.kind == library
      - to.kind == service
"""
    violations = compile_and_evaluate(enriched_ir, rules_yaml)
    assert len(violations) == 0, "to.kind == service does not match nested modules"

    # But to.within == service DOES match
    rules_yaml_within = """
rule:
  id: library-no-service-deps-within
  name: Test with within
  severity: error
  target: dependency
  action: forbid
  when:
    all:
      - from.within == library
      - to.within == service
"""
    violations_within = compile_and_evaluate(enriched_ir, rules_yaml_within)
    assert len(violations_within) == 1, "to.within == service matches nested modules"


def test_direct_service_import_kind_equals_within():
    """
    For direct service-level code (not nested), kind == within.
    """
    model = build_microservices_model()

    library_node = make_node("libs.shared.money", "libs/shared/money.py")
    # Import from service api layer (not nested module)
    service_api_node = make_node(
        "services.billing.api.routes",
        "services/billing/api/routes.py",
    )
    edge = make_edge(library_node, service_api_node, "libs/shared/money.py")

    ir = ArchitectureIR(
        schema_version=2,
        produced_by="test",
        repo_root="/test",
        nodes=(library_node, service_api_node),
        edges=(edge,),
    )

    enriched_ir = DefaultArchitectureEnricher().enrich(ir, model)
    enriched_edge = enriched_ir.edges[0]

    # Direct service import: kind == within == 'service'
    assert enriched_edge.dst_container_kind == "service"
    assert enriched_edge.dst_within == "service"

    # Both rules work for direct service imports
    rules_yaml_kind = """
rule:
  id: library-no-service-deps-kind
  name: Test with kind
  severity: error
  target: dependency
  action: forbid
  when:
    all:
      - from.kind == library
      - to.kind == service
"""
    violations_kind = compile_and_evaluate(enriched_ir, rules_yaml_kind)
    assert len(violations_kind) == 1, "to.kind == service matches direct service code"

    rules_yaml_within = """
rule:
  id: library-no-service-deps-within
  name: Test with within
  severity: error
  target: dependency
  action: forbid
  when:
    all:
      - from.within == library
      - to.within == service
"""
    violations_within = compile_and_evaluate(enriched_ir, rules_yaml_within)
    assert len(violations_within) == 1, "to.within == service also matches direct service code"
