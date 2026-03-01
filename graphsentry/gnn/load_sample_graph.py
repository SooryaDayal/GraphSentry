import json
from pathlib import Path
from build_graph import build_heterogeneous_graph


def main():

    # locate the repo root
    repo_root = Path(__file__).resolve().parents[2]

    # Member 2's generated Nexus graph
    graph_path = repo_root / "graphsentry" / "data" / "nexus_graph_output.json"

    print("Loading Nexus graph from:", graph_path)

    with open(graph_path, "r") as f:
        graph = json.load(f)

    nodes = graph["nodes"]
    edges = graph["edges"]

    # Build PyTorch Geometric graph
    data = build_heterogeneous_graph(nodes, edges)

    print("\nGraph successfully converted to PyG HeteroData!\n")

    print("Node types:")
    print(data.node_types)

    print("\nEdge types:")
    print(data.edge_types)

    print("\nNode feature shapes:")
    for ntype in data.node_types:
        print(f"{ntype}:", data[ntype].x.shape)

    print("\nEdge index shapes:")
    for etype in data.edge_types:
        print(f"{etype}:", data[etype].edge_index.shape)


if __name__ == "__main__":
    main()