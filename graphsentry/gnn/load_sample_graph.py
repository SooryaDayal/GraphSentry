import json
from pathlib import Path
from build_graph import build_heterogeneous_graph


def main():

    # locate repo root
    repo_root = Path(__file__).resolve().parents[2]

    # path to Member 2's generated graph
    graph_path = repo_root / "graphsentry" / "data" / "nexus_graph_output.json"

    print("Loading Nexus graph from:", graph_path)

    with open(graph_path, "r") as f:
        graph = json.load(f)

    nodes = graph["nodes"]
    edges = graph["edges"]

    # build PyTorch Geometric graph
    data = build_heterogeneous_graph(nodes, edges)

    print("\nGraph successfully converted to PyG HeteroData!\n")

    print("Node types:")
    print(data.node_types)

    print("\nEdge types:")
    print(data.edge_types)

    print("\nNode feature shapes:")
    for ntype in data.node_types:
        print(f"{ntype}: {data[ntype].x.shape}")

    print("\nEdge index shapes:")
    for etype in data.edge_types:
        print(f"{etype}: {data[etype].edge_index.shape}")

    print("\nEdge attribute shapes:")
    for etype in data.edge_types:
        if hasattr(data[etype], "edge_attr"):
            print(f"{etype}: {data[etype].edge_attr.shape}")


if __name__ == "__main__":
    main()