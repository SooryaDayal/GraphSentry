import torch
from torch_geometric.data import HeteroData
from datetime import datetime


def _parse_timestamp(ts: str) -> float:
    # Handles format: "YYYY-MM-DD HH:MM:%S"
    try:
        return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").timestamp()
    except Exception:
        return 0.0


def build_heterogeneous_graph(nodes, edges, feature_dim: int = 16) -> HeteroData:
    """
    Converts Member 2 Nexus output into PyTorch Geometric HeteroData.
    """
    data = HeteroData()

    # -------------------------
    # Build node maps
    # -------------------------
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

    # -------------------------
    # Placeholder node features (Week 1)
    # -------------------------
    for ntype, count in counts.items():
        data[ntype].x = torch.randn((count, feature_dim), dtype=torch.float32)

    # -------------------------
    # Edge grouping + edge attributes
    # -------------------------
    grouped = {}      # {(src_type, rel, dst_type): [(src_idx, dst_idx), ...]}
    edge_attrs = {}   # {(src_type, rel, dst_type): [[ts, ch], ...]}

    channel_map = {
        "Mobile App": 0,
        "Web Banking": 1,
        "ATM": 2,
        "UPI": 3,
        "RTGS": 4
    }

    for e in edges:
        src_id = str(e["source"])
        dst_id = str(e["target"])
        rel = str(e["relation"])

        src_type = next((t for t, m in node_maps.items() if src_id in m), None)
        dst_type = next((t for t, m in node_maps.items() if dst_id in m), None)
        if src_type is None or dst_type is None:
            continue

        key = (src_type, rel, dst_type)

        # Edge index pair
        grouped.setdefault(key, []).append(
            (node_maps[src_type][src_id], node_maps[dst_type][dst_id])
        )

        # Edge attributes: [timestamp_seconds, channel_code]
        ts_val = _parse_timestamp(str(e.get("timestamp", "")))
        ch_val = channel_map.get(str(e.get("channel", "")), -1)
        edge_attrs.setdefault(key, []).append([ts_val, float(ch_val)])

    # -------------------------
    # Write to HeteroData
    # -------------------------
    for (src_type, rel, dst_type), pairs in grouped.items():
        src_idx = torch.tensor([p[0] for p in pairs], dtype=torch.long)
        dst_idx = torch.tensor([p[1] for p in pairs], dtype=torch.long)

        data[(src_type, rel, dst_type)].edge_index = torch.stack([src_idx, dst_idx], dim=0)

        # Add edge_attr if present
        if (src_type, rel, dst_type) in edge_attrs:
            data[(src_type, rel, dst_type)].edge_attr = torch.tensor(
                edge_attrs[(src_type, rel, dst_type)],
                dtype=torch.float32
            )

    return data