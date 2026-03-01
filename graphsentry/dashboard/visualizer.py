"""
visualizer.py — GraphSentry feature/dashboard-docs
Author: Vidhu (Member 3)
"""

import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

NODE_STYLES = {
    "account": {"color": "#0a84ff", "size": 800},
    "device":  {"color": "#ff9f0a", "size": 700},
    "ip":      {"color": "#30d158", "size": 600},
}
RISK_BORDER = {"high": "#ff453a", "medium": "#ffd60a", "low": "#3a3a3c"}
EDGE_COLORS = {"uses_device": "#2c2c2e", "uses_ip": "#2c2c2e", "transfer": "#ff453a"}


def _build_nx_graph(graph_data: dict) -> nx.DiGraph:
    G = nx.DiGraph()
    for node in graph_data["nodes"]:
        G.add_node(node["id"],
                   node_type=node.get("type", "account"),
                   label=node.get("label", node["id"]),
                   risk=node.get("risk", "low"))
    for edge in graph_data["edges"]:
        G.add_edge(edge["source"], edge["target"],
                   relation=edge.get("relation", "transfer"))
    return G


def visualize_network_static(graph_data: dict):
    G = _build_nx_graph(graph_data)
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor("#000000")
    ax.set_facecolor("#000000")
    pos = nx.spring_layout(G, seed=42, k=2.5)

    for relation, color in EDGE_COLORS.items():
        edge_list = [(u, v) for u, v, d in G.edges(data=True) if d.get("relation") == relation]
        if edge_list:
            nx.draw_networkx_edges(G, pos, edgelist=edge_list, edge_color=color,
                                   arrows=True, arrowsize=15, width=1.2, alpha=0.8,
                                   ax=ax, connectionstyle="arc3,rad=0.08")

    for node_type, style in NODE_STYLES.items():
        node_list = [n for n, d in G.nodes(data=True) if d.get("node_type") == node_type]
        if not node_list:
            continue
        border_colors = [RISK_BORDER.get(G.nodes[n].get("risk", "low"), "#3a3a3c") for n in node_list]
        nx.draw_networkx_nodes(G, pos, nodelist=node_list, node_color=style["color"],
                               node_size=style["size"], edgecolors=border_colors,
                               linewidths=2, alpha=0.95, ax=ax)

    labels = {n: d.get("label", n) for n, d in G.nodes(data=True)}
    nx.draw_networkx_labels(G, pos, labels, font_size=7, font_color="#ebebf0",
                            font_weight="500", ax=ax)

    legend_handles = [
        mpatches.Patch(color="#0a84ff", label="Account"),
        mpatches.Patch(color="#ff9f0a", label="Device"),
        mpatches.Patch(color="#30d158", label="IP"),
        mpatches.Patch(color="#ff453a", label="Transfer"),
        mpatches.Patch(color="#2c2c2e", label="Link"),
    ]
    legend = ax.legend(handles=legend_handles, loc="lower right", fontsize=7,
                       facecolor="#0a0a0a", edgecolor="#1d1d1f", labelcolor="#86868b", framealpha=1)
    ax.set_title("Entity-Nexus Graph", color="#86868b", fontsize=9, pad=12,
                 fontfamily="sans-serif", fontweight="400", loc="left")
    ax.axis("off")
    fig.tight_layout(pad=1.5)
    return fig


def visualize_network_interactive(graph_data: dict, output_path: str = None) -> str:
    import tempfile
    if output_path is None:
        output_path = os.path.join(tempfile.gettempdir(), "gs_graph.html")
    """
    Builds a fully interactive PyVis graph with:
    - Scroll to zoom
    - Click + drag to pan
    - Hover tooltips showing node ID, type, risk
    - Node highlighting on hover
    - Physics toggle
    """
    try:
        from pyvis.network import Network
    except ImportError:
        html = _fallback_html(graph_data)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        return output_path

    net = Network(height="560px", width="100%", bgcolor="#000000",
                  font_color="#ebebf0", directed=True, notebook=False)

    # Physics — Barnes-Hut for large graphs, fast and clean
    net.set_options("""
    {
      "physics": {
        "enabled": true,
        "barnesHut": {
          "gravitationalConstant": -6000,
          "centralGravity": 0.3,
          "springLength": 120,
          "springConstant": 0.04,
          "damping": 0.09
        },
        "stabilization": { "iterations": 200 }
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100,
        "zoomView": true,
        "dragView": true,
        "navigationButtons": false,
        "keyboard": false
      },
      "nodes": {
        "borderWidth": 2,
        "borderWidthSelected": 3,
        "font": { "size": 11, "color": "#ebebf0", "face": "DM Sans, -apple-system, sans-serif" },
        "shadow": false
      },
      "edges": {
        "smooth": { "type": "curvedCW", "roundness": 0.1 },
        "arrows": { "to": { "enabled": true, "scaleFactor": 0.6 } },
        "font": { "size": 9, "color": "#636366", "align": "middle" },
        "shadow": false
      }
    }
    """)

    type_colors  = {"account": "#0a84ff", "device": "#ff9f0a", "ip": "#30d158"}
    risk_borders = {"high": "#ff453a",    "medium": "#ffd60a", "low": "#3a3a3c"}
    type_shapes  = {"account": "dot",     "device": "square",  "ip": "diamond"}
    type_sizes   = {"account": 16,        "device": 14,        "ip": 13}

    for node in graph_data["nodes"]:
        nid   = node["id"]
        ntype = node.get("type", "account")
        risk  = node.get("risk", "low")
        label = node.get("label", nid)

        tooltip = (
            f"<div style='font-family:-apple-system,sans-serif;padding:6px 10px;"
            f"background:#1c1c1e;border-radius:8px;font-size:12px;line-height:1.7'>"
            f"<strong style='color:#f5f5f7'>{label}</strong><br>"
            f"<span style='color:#636366'>type</span> &nbsp;<span style='color:#ebebf0'>{ntype}</span><br>"
            f"<span style='color:#636366'>risk</span> &nbsp;"
            f"<span style='color:{risk_borders.get(risk, '#ebebf0')}'>{risk}</span><br>"
            f"<span style='color:#636366'>id</span> &nbsp;<span style='color:#48484a'>{nid}</span>"
            f"</div>"
        )

        net.add_node(
            nid,
            label=label,
            title=tooltip,
            color={
                "background": type_colors.get(ntype, "#0a84ff"),
                "border":     risk_borders.get(risk, "#3a3a3c"),
                "highlight":  {"background": "#ffffff", "border": risk_borders.get(risk, "#3a3a3c")},
                "hover":      {"background": "#ffffff", "border": risk_borders.get(risk, "#3a3a3c")},
            },
            shape=type_shapes.get(ntype, "dot"),
            size=type_sizes.get(ntype, 16),
        )

    edge_colors  = {"uses_device": "#2c2c2e", "uses_ip": "#2c2c2e", "transfer": "#ff453a"}
    edge_widths  = {"uses_device": 1,         "uses_ip": 1,         "transfer": 2}

    for edge in graph_data["edges"]:
        rel     = edge.get("relation", "transfer")
        channel = edge.get("channel", "")
        ts      = edge.get("timestamp", "")

        edge_tooltip = (
            f"<div style='font-family:-apple-system,sans-serif;padding:6px 10px;"
            f"background:#1c1c1e;border-radius:8px;font-size:12px;line-height:1.7'>"
            f"<span style='color:#636366'>relation</span> &nbsp;<span style='color:#ebebf0'>{rel}</span><br>"
            + (f"<span style='color:#636366'>channel</span> &nbsp;<span style='color:#ebebf0'>{channel}</span><br>" if channel else "")
            + (f"<span style='color:#636366'>time</span> &nbsp;<span style='color:#48484a'>{ts}</span>" if ts else "")
            + "</div>"
        )

        net.add_edge(
            edge["source"], edge["target"],
            color={"color": edge_colors.get(rel, "#2c2c2e"), "highlight": "#ffffff", "hover": "#ffffff"},
            width=edge_widths.get(rel, 1),
            title=edge_tooltip,
            label=channel if channel else "",
        )

    # Inject custom CSS into the saved HTML to match dark theme
    net.save_graph(output_path)

    with open(output_path, "r", encoding="utf-8") as f:
        html = f.read()

    custom_css = """
    <style>
    body, html { background: #000000 !important; margin: 0; padding: 0; }
    #mynetwork {
        background: #000000 !important;
        border: 1px solid #1c1c1e !important;
        border-radius: 12px !important;
    }
    div.vis-tooltip {
        background: #1c1c1e !important;
        border: 1px solid #2c2c2e !important;
        border-radius: 8px !important;
        color: #ebebf0 !important;
        font-family: -apple-system, sans-serif !important;
        font-size: 12px !important;
        padding: 0 !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.6) !important;
    }
    </style>
    """
    html = html.replace("</head>", custom_css + "</head>")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


def _fallback_html(graph_data: dict) -> str:
    return """<!DOCTYPE html>
<html>
<head>
<style>
  body { background:#000; color:#ebebf0; font-family:-apple-system,sans-serif;
         display:flex; align-items:center; justify-content:center; height:100vh; margin:0; }
  p { color:#636366; font-size:0.8rem; }
</style>
</head>
<body>
<div style="text-align:center">
  <h3 style="font-weight:300;color:#f5f5f7;letter-spacing:-0.02em">Entity-Nexus Graph</h3>
  <p>Install <code>pyvis</code> for interactive view</p>
</div>
</body>
</html>"""
