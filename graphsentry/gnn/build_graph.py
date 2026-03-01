import torch
from torch_geometric.data import HeteroData


def build_heterogeneous_graph(nodes, edges, feature_dim: int = 16) -> HeteroData:
    """
    Converts Member 2 Nexus output into PyTorch Geometric HeteroData.
    """

    data = HeteroData()

    node_maps = {}
    counts = {}

    for n in nodes:
        ntype = str(n["type"])
        nid = str(n["id"])

        if ntype not in node_maps:
            node_maps[ntype] = {}
            counts[ntype] = 0

        if nid not in node_maps[ntype]:
            node_maps[ntype][nid] = counts[ntype]
            counts[ntype] += 1

    for ntype, count in counts.items():
        data[ntype].x = torch.randn((count, feature_dim))

    grouped = {}

    for e in edges:
        src_id = str(e["source"])
        dst_id = str(e["target"])
        rel = str(e["relation"])

        src_type = next((t for t, m in node_maps.items() if src_id in m), None)
        dst_type = next((t for t, m in node_maps.items() if dst_id in m), None)

        if src_type is None or dst_type is None:
            continue

        key = (src_type, rel, dst_type)

        grouped.setdefault(key, []).append(
            (node_maps[src_type][src_id], node_maps[dst_type][dst_id])
        )

    for (src_type, rel, dst_type), pairs in grouped.items():
        src_idx = torch.tensor([p[0] for p in pairs], dtype=torch.long)
        dst_idx = torch.tensor([p[1] for p in pairs], dtype=torch.long)

        data[(src_type, rel, dst_type)].edge_index = torch.stack([src_idx, dst_idx], dim=0)

    return data