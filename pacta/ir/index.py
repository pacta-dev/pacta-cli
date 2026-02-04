from collections.abc import Mapping
from dataclasses import dataclass

from pacta.ir.types import ArchitectureIR, CanonicalId, DepType, IREdge, IRNode, SymbolKind


@dataclass(frozen=True, slots=True)
class IRIndex:
    """
    Fast lookups over ArchitectureIR.

    Notes:
    - Keys are CanonicalId string forms to keep it JSON/debug friendly.
    - Adjacency lists are tuples to keep immutability and determinism.
    """

    # Nodes
    nodes: tuple[IRNode, ...]
    nodes_by_id: Mapping[str, IRNode]
    nodes_by_kind: Mapping[SymbolKind, tuple[IRNode, ...]]

    # Grouping (enriched fields)
    nodes_by_container: Mapping[str, tuple[IRNode, ...]]
    nodes_by_layer: Mapping[str, tuple[IRNode, ...]]
    nodes_by_context: Mapping[str, tuple[IRNode, ...]]

    # Edges
    edges: tuple[IREdge, ...]
    edges_by_type: Mapping[DepType, tuple[IREdge, ...]]

    # Adjacency
    out_edges_by_src: Mapping[str, tuple[IREdge, ...]]
    in_edges_by_dst: Mapping[str, tuple[IREdge, ...]]

    # Convenience
    def get_node(self, node_id: CanonicalId | str) -> IRNode | None:
        key = node_id if isinstance(node_id, str) else str(node_id)
        return self.nodes_by_id.get(key)

    def out_edges(self, src_id: CanonicalId | str) -> tuple[IREdge, ...]:
        key = src_id if isinstance(src_id, str) else str(src_id)
        return self.out_edges_by_src.get(key, ())

    def in_edges(self, dst_id: CanonicalId | str) -> tuple[IREdge, ...]:
        key = dst_id if isinstance(dst_id, str) else str(dst_id)
        return self.in_edges_by_dst.get(key, ())

    def nodes_in_container(self, container_id: str) -> tuple[IRNode, ...]:
        return self.nodes_by_container.get(container_id, ())

    def nodes_in_layer(self, layer_id: str) -> tuple[IRNode, ...]:
        return self.nodes_by_layer.get(layer_id, ())

    def nodes_in_context(self, context_id: str) -> tuple[IRNode, ...]:
        return self.nodes_by_context.get(context_id, ())


def build_index(ir: ArchitectureIR) -> IRIndex:
    """
    Build an IRIndex from ArchitectureIR.

    Determinism:
    - All groupings and adjacency lists are sorted by a stable key.
    - Returned collections are immutable tuples / mappings.
    """

    # nodes_by_id
    nodes_by_id: dict[str, IRNode] = {}
    for n in ir.nodes:
        nodes_by_id[str(n.id)] = n

    # stable node sorting key
    def node_sort_key(n: IRNode) -> tuple:
        return (
            str(n.kind.value),
            str(n.id),
            n.path or "",
            n.name or "",
        )

    # nodes_by_kind / container / layer / context
    nodes_by_kind: dict[SymbolKind, list[IRNode]] = {}
    nodes_by_container: dict[str, list[IRNode]] = {}
    nodes_by_layer: dict[str, list[IRNode]] = {}
    nodes_by_context: dict[str, list[IRNode]] = {}

    for n in ir.nodes:
        nodes_by_kind.setdefault(n.kind, []).append(n)

        if n.container:
            nodes_by_container.setdefault(n.container, []).append(n)
        if n.layer:
            nodes_by_layer.setdefault(n.layer, []).append(n)
        if n.context:
            nodes_by_context.setdefault(n.context, []).append(n)

    # edges and adjacency
    # stable edge sorting key
    def edge_sort_key(e: IREdge) -> tuple:
        loc = e.loc
        loc_key = ("", 0, 0)
        if loc is not None:
            loc_key = (loc.file, loc.start.line, loc.start.column)
        return (
            e.dep_type.value,
            str(e.src),
            str(e.dst),
            loc_key,
        )

    edges_sorted = tuple(sorted(ir.edges, key=edge_sort_key))

    edges_by_type: dict[DepType, list[IREdge]] = {}
    out_edges_by_src: dict[str, list[IREdge]] = {}
    in_edges_by_dst: dict[str, list[IREdge]] = {}

    for e in edges_sorted:
        edges_by_type.setdefault(e.dep_type, []).append(e)

        src_key = str(e.src)
        dst_key = str(e.dst)
        out_edges_by_src.setdefault(src_key, []).append(e)
        in_edges_by_dst.setdefault(dst_key, []).append(e)

    # freeze (sorted tuples everywhere)
    frozen_nodes_by_kind: dict[SymbolKind, tuple[IRNode, ...]] = {
        k: tuple(sorted(v, key=node_sort_key)) for k, v in nodes_by_kind.items()
    }
    frozen_nodes_by_container: dict[str, tuple[IRNode, ...]] = {
        k: tuple(sorted(v, key=node_sort_key)) for k, v in nodes_by_container.items()
    }
    frozen_nodes_by_layer: dict[str, tuple[IRNode, ...]] = {
        k: tuple(sorted(v, key=node_sort_key)) for k, v in nodes_by_layer.items()
    }
    frozen_nodes_by_context: dict[str, tuple[IRNode, ...]] = {
        k: tuple(sorted(v, key=node_sort_key)) for k, v in nodes_by_context.items()
    }

    frozen_edges_by_type: dict[DepType, tuple[IREdge, ...]] = {k: tuple(v) for k, v in edges_by_type.items()}
    frozen_out: dict[str, tuple[IREdge, ...]] = {k: tuple(v) for k, v in out_edges_by_src.items()}
    frozen_in: dict[str, tuple[IREdge, ...]] = {k: tuple(v) for k, v in in_edges_by_dst.items()}

    return IRIndex(
        nodes=ir.nodes,
        nodes_by_id=nodes_by_id,
        nodes_by_kind=frozen_nodes_by_kind,
        nodes_by_container=frozen_nodes_by_container,
        nodes_by_layer=frozen_nodes_by_layer,
        nodes_by_context=frozen_nodes_by_context,
        edges=edges_sorted,
        edges_by_type=frozen_edges_by_type,
        out_edges_by_src=frozen_out,
        in_edges_by_dst=frozen_in,
    )
