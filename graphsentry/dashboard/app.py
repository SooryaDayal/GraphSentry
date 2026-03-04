"""
GraphSentry Dashboard - feature/dashboard-docs
Member 3: Vidhu
"""

import streamlit as st
import os
import json
from visualizer import visualize_network_static, visualize_network_interactive

# ── Load Abstract ─────────────────────────────────────────────────────────────
def load_abstract() -> str:
    path = os.path.join(os.path.dirname(__file__), "../docs/technical_abstract.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Abstract file not found. Ensure `docs/technical_abstract.md` exists."

# ── Normalize Soorya's schema → dashboard schema ──────────────────────────────
def normalize_graph_data(raw: dict) -> dict:
    """
    Soorya's output has: {id, type} for nodes, {source, target, relation, timestamp, channel}
    Dashboard needs:     {id, type, label, risk} for nodes
    This function derives label and risk from the available data.
    """
    edges = raw.get("edges", [])

    # Count how many edges each node is involved in (degree = proxy for risk)
    degree = {}
    for e in edges:
        degree[e["source"]] = degree.get(e["source"], 0) + 1
        degree[e["target"]] = degree.get(e["target"], 0) + 1

    # Flag high-risk channels
    high_risk_channels = {"RTGS", "IMPS"}
    high_risk_nodes = set()
    for e in edges:
        if e.get("channel") in high_risk_channels:
            high_risk_nodes.add(e["source"])
            high_risk_nodes.add(e["target"])

    # Shared device detection — devices linked to 3+ accounts = high risk
    device_connections = {}
    for e in edges:
        if e.get("relation") == "uses_device":
            tgt = e["target"]
            device_connections[tgt] = device_connections.get(tgt, 0) + 1

    shared_devices = {d for d, cnt in device_connections.items() if cnt >= 3}

    def derive_risk(node_id: str, node_type: str) -> str:
        if node_id in shared_devices:
            return "high"
        if node_id in high_risk_nodes:
            return "high"
        d = degree.get(node_id, 0)
        if d >= 5:
            return "high"
        if d >= 2:
            return "medium"
        return "low"

    def derive_label(node_id: str, node_type: str) -> str:
        # Shorten long IDs for display: ACT_3942 → Acct-3942, IMEI_67329 → IMEI-67329
        if node_type == "account":
            return node_id.replace("ACT_", "Acct-")
        if node_type == "device":
            return node_id.replace("IMEI_", "IMEI-").replace("UUID_", "UUID-")
        if node_type == "ip":
            parts = node_id.replace("IP_", "").replace("_", ".")
            # Show only first 3 octets for readability
            octets = parts.split(".")
            return ".".join(octets[:3]) + ".x" if len(octets) == 4 else node_id
        return node_id

    nodes = []
    for n in raw.get("nodes", []):
        nid   = n["id"]
        ntype = n.get("type", "account")
        nodes.append({
            "id":    nid,
            "type":  ntype,
            "label": derive_label(nid, ntype),
            "risk":  derive_risk(nid, ntype),
        })

    return {"nodes": nodes, "edges": edges}

# ── Load Real Graph Data ──────────────────────────────────────────────────────
def get_fallback_data() -> dict:
    return {
        "nodes": [
            {"id": "ACC_001", "type": "account", "label": "Acct-001", "risk": "high"},
            {"id": "ACC_002", "type": "account", "label": "Acct-002", "risk": "medium"},
            {"id": "ACC_003", "type": "account", "label": "Acct-003", "risk": "high"},
            {"id": "ACC_004", "type": "account", "label": "Acct-004", "risk": "low"},
            {"id": "ACC_005", "type": "account", "label": "Acct-005", "risk": "high"},
            {"id": "DEV_IMEI_AAA", "type": "device", "label": "IMEI-AAA", "risk": "high"},
            {"id": "DEV_IMEI_BBB", "type": "device", "label": "IMEI-BBB", "risk": "low"},
            {"id": "IP_192.168.1.1", "type": "ip", "label": "IP-192.168.x", "risk": "high"},
            {"id": "IP_10.0.0.5",    "type": "ip", "label": "IP-10.0.0.x",  "risk": "medium"},
        ],
        "edges": [
            {"source": "ACC_001", "target": "DEV_IMEI_AAA", "relation": "uses_device", "timestamp": "", "channel": "RTGS"},
            {"source": "ACC_002", "target": "DEV_IMEI_AAA", "relation": "uses_device", "timestamp": "", "channel": "UPI"},
            {"source": "ACC_003", "target": "DEV_IMEI_AAA", "relation": "uses_device", "timestamp": "", "channel": "IMPS"},
            {"source": "ACC_001", "target": "IP_192.168.1.1", "relation": "uses_ip", "timestamp": "", "channel": ""},
            {"source": "ACC_002", "target": "IP_192.168.1.1", "relation": "uses_ip", "timestamp": "", "channel": ""},
            {"source": "ACC_004", "target": "DEV_IMEI_BBB",   "relation": "uses_device", "timestamp": "", "channel": "ATM"},
            {"source": "ACC_004", "target": "IP_10.0.0.5",    "relation": "uses_ip", "timestamp": "", "channel": ""},
            {"source": "ACC_001", "target": "ACC_003", "relation": "transfer", "timestamp": "", "channel": "RTGS"},
            {"source": "ACC_003", "target": "ACC_005", "relation": "transfer", "timestamp": "", "channel": "IMPS"},
            {"source": "ACC_001", "target": "ACC_005", "relation": "transfer", "timestamp": "", "channel": "UPI"},
        ]
    }

def load_graph_data() -> tuple[dict, bool]:
    path = os.path.join(os.path.dirname(__file__), "../data/nexus_graph_output.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return normalize_graph_data(raw), True
    except FileNotFoundError:
        return get_fallback_data(), False

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GraphSentry",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&family=DM+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [data-testid="stAppViewContainer"], .stApp {
    background-color: #000000 !important;
    color: #f5f5f7 !important;
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

.main .block-container {
    padding: 2.5rem 3rem 3rem 3rem !important;
    max-width: 1300px !important;
    margin: 0 !important;
}

/* Remove ghost left gap */
section.main { margin-left: 0 !important; }
[data-testid="stSidebar"][aria-expanded="false"] { margin-left: -200px !important; }

/* Hide chrome */
#MainMenu, footer, header { visibility: hidden !important; }
.stDeployButton, [data-testid="stToolbar"] { display: none !important; }
[data-testid="collapsedControl"] { color: #3a3a3c !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #000000 !important;
    border-right: 1px solid #1c1c1e !important;
    min-width: 200px !important;
    max-width: 200px !important;
}
[data-testid="stSidebar"] > div { padding: 2rem 1.25rem !important; }
[data-testid="stSidebarNav"] { display: none !important; }

/* Radio nav */
.stRadio > label { display: none !important; }
.stRadio > div { display: flex !important; flex-direction: column !important; gap: 0 !important; }
.stRadio label[data-baseweb="radio"] {
    display: flex !important;
    align-items: center !important;
    padding: 0.45rem 0.6rem !important;
    border-radius: 6px !important;
    cursor: pointer !important;
}
.stRadio label[data-baseweb="radio"] > div:first-child { display: none !important; }
.stRadio label[data-baseweb="radio"] p {
    font-size: 0.82rem !important;
    font-weight: 400 !important;
    color: #636366 !important;
}
.stRadio label[aria-checked="true"][data-baseweb="radio"] { background: #1c1c1e !important; }
.stRadio label[aria-checked="true"][data-baseweb="radio"] p {
    color: #f5f5f7 !important;
    font-weight: 500 !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: #0a0a0a !important;
    border: 1px solid #1c1c1e !important;
    border-radius: 8px !important;
    color: #636366 !important;
    font-size: 0.78rem !important;
}
.streamlit-expanderContent {
    background: #0a0a0a !important;
    border: 1px solid #1c1c1e !important;
    border-top: none !important;
    border-radius: 0 0 8px 8px !important;
}

/* Buttons */
.stDownloadButton button, .stButton button {
    background: #1c1c1e !important;
    color: #f5f5f7 !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    font-family: 'DM Sans', sans-serif !important;
    padding: 0.5rem 1.2rem !important;
}
.stDownloadButton button:hover, .stButton button:hover { background: #2c2c2e !important; }
</style>
""", unsafe_allow_html=True)

# ── Load ──────────────────────────────────────────────────────────────────────
graph_data, is_live = load_graph_data()
TECHNICAL_ABSTRACT  = load_abstract()

# Stats — computed from normalized data
nodes     = graph_data.get("nodes", [])
edges     = graph_data.get("edges", [])
total_nodes = len(nodes)
total_edges = len(edges)
high_risk   = sum(1 for n in nodes if n.get("risk") == "high")

device_connections = {}
for e in edges:
    if e.get("relation") == "uses_device":
        tgt = e["target"]
        device_connections[tgt] = device_connections.get(tgt, 0) + 1
shared_devs = sum(1 for cnt in device_connections.values() if cnt >= 3)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="font-size:0.65rem;font-weight:600;letter-spacing:0.2em;
                color:#3a3a3c;text-transform:uppercase;margin-bottom:1.75rem">
        GraphSentry
    </div>
    """, unsafe_allow_html=True)

    page = st.radio("", ["Dashboard", "Graph", "Abstract", "About"])

    st.markdown("""
    <div style="margin-top:3rem;font-size:0.65rem;color:#3a3a3c;
                font-family:'DM Mono',monospace;line-height:1.8">
        feature/dashboard-docs<br>Member 3 · Vidhu<br>Sprint 1
    </div>
    """, unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def page_header(subtitle: str, bold: str):
    st.markdown(f"""
    <div style="font-size:0.65rem;font-weight:600;letter-spacing:0.2em;
                color:#636366;text-transform:uppercase;margin-bottom:0.4rem">
        GraphSentry
    </div>
    <div style="font-size:1.75rem;font-weight:300;color:#f5f5f7;
                letter-spacing:-0.03em;margin-bottom:1.75rem">
        {subtitle} <span style="font-weight:600">{bold}</span>
    </div>
    """, unsafe_allow_html=True)

def section_label(text: str):
    st.markdown(f"""
    <div style="font-size:0.65rem;font-weight:600;letter-spacing:0.12em;
                color:#636366;text-transform:uppercase;margin-bottom:0.75rem">
        {text}
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
if page == "Dashboard":

    data_color = "#30d158" if is_live else "#ff9f0a"
    data_label = "Live" if is_live else "Fallback"
    data_source = "nexus_graph_output.json" if is_live else "sample data"

    col_title, col_status = st.columns([5, 1])
    with col_title:
        page_header("Entity-Nexus", "Monitor")
    with col_status:
        st.markdown(f"""
        <div style="display:flex;justify-content:flex-end;padding-top:0.3rem">
            <div style="display:inline-flex;align-items:center;gap:0.4rem;
                        background:#1c1c1e;border-radius:20px;padding:0.3rem 0.75rem">
                <div style="width:6px;height:6px;border-radius:50%;background:{data_color}"></div>
                <span style="font-size:0.68rem;font-weight:500;color:#636366;
                             letter-spacing:0.05em">{data_label}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div style="height:1.5rem"></div>', unsafe_allow_html=True)

    # Metrics
    c1, c2, c3, c4 = st.columns(4, gap="small")
    def metric_card(col, value, label, sub):
        with col:
            st.markdown(f"""
            <div style="background:#0a0a0a;border:1px solid #1c1c1e;border-radius:12px;
                        padding:1.25rem 1.4rem">
                <div style="font-size:0.65rem;font-weight:600;color:#636366;
                            letter-spacing:0.1em;text-transform:uppercase;
                            margin-bottom:0.5rem">{label}</div>
                <div style="font-size:2rem;font-weight:300;color:#f5f5f7;
                            letter-spacing:-0.04em;line-height:1">{value}</div>
                <div style="font-size:0.68rem;color:#3a3a3c;margin-top:0.35rem;
                            font-family:'DM Mono',monospace">{sub}</div>
            </div>
            """, unsafe_allow_html=True)

    metric_card(c1, total_nodes, "Nodes",         "accounts · devices · ips")
    metric_card(c2, total_edges, "Edges",         "active links")
    metric_card(c3, high_risk,   "High Risk",     "nodes flagged")
    metric_card(c4, shared_devs, "Shared Device", "multi-account device")

    st.markdown('<div style="height:2rem"></div>', unsafe_allow_html=True)

    col_graph, col_right = st.columns([3, 2], gap="large")

    with col_graph:
        section_label("Entity-Nexus Graph")
        # Sample 300 nodes max for clean rendering
        import random
        sample_size = 300
        if len(nodes) > sample_size:
            sampled_ids = set(n["id"] for n in random.sample(nodes, sample_size))
            display_data = {
                "nodes": [n for n in nodes if n["id"] in sampled_ids],
                "edges": [e for e in edges if e["source"] in sampled_ids and e["target"] in sampled_ids],
            }
            st.markdown(f"""
            <div style="font-size:0.68rem;color:#3a3a3c;font-family:'DM Mono',monospace;
                        margin-bottom:0.5rem">
                rendering {sample_size} of {len(nodes)} nodes for performance
            </div>
            """, unsafe_allow_html=True)
        else:
            display_data = graph_data

        html_path = visualize_network_interactive(display_data)
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        st.components.v1.html(html_content, height=520, scrolling=False)
        st.markdown(f"""
        <div style="font-size:0.65rem;color:#3a3a3c;font-family:'DM Mono',monospace;
                    margin-top:0.4rem">
            source: {data_source} · scroll to zoom · drag to pan · hover for details
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        section_label("Alerts")

        # Build dynamic alerts
        shared_device_ids = [d for d, cnt in device_connections.items() if cnt >= 3]
        transfer_edges    = [e for e in edges if e.get("relation") == "transfer"]
        rtgs_edges        = [e for e in edges if e.get("channel") == "RTGS"]

        alerts = []
        for d in shared_device_ids[:2]:
            cnt = device_connections[d]
            alerts.append(("#ff453a", "HIGH", f"{d} linked to {cnt} accounts", "Mule Ring pattern"))
        if len(transfer_edges) > 0:
            e0 = transfer_edges[0]
            alerts.append(("#ff453a", "HIGH", f"{e0['source']} → {e0['target']}", f"Transfer · {e0.get('channel','')}"))
        if len(rtgs_edges) > 0:
            alerts.append(("#ffd60a", "MED", f"{len(rtgs_edges)} RTGS transactions flagged", "High-value channel"))
        if high_risk > 0:
            alerts.append(("#ffd60a", "MED", f"{high_risk} high-risk nodes active", "Risk threshold exceeded"))

        low_nodes = [n for n in nodes if n.get("risk") == "low"]
        if low_nodes:
            alerts.append(("#30d158", "LOW", f"{len(low_nodes)} nodes — normal activity", "No anomalies"))

        st.markdown('<div style="background:#0a0a0a;border:1px solid #1c1c1e;border-radius:12px;padding:0.25rem 1.25rem">', unsafe_allow_html=True)
        for color, level, title, detail in alerts[:6]:
            st.markdown(f"""
            <div style="display:flex;align-items:flex-start;gap:0.75rem;
                        padding:0.75rem 0;border-bottom:1px solid #1c1c1e">
                <div style="width:6px;height:6px;border-radius:50%;background:{color};
                            margin-top:0.35rem;flex-shrink:0"></div>
                <div>
                    <div style="font-size:0.8rem;color:#ebebf0;line-height:1.4">{title}</div>
                    <div style="font-size:0.68rem;color:#48484a;font-family:'DM Mono',monospace;
                                margin-top:0.15rem">{level} · {detail}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div style="height:1.25rem"></div>', unsafe_allow_html=True)
        section_label("Legend")
        st.markdown('<div style="background:#0a0a0a;border:1px solid #1c1c1e;border-radius:12px;padding:0.75rem 1.25rem">', unsafe_allow_html=True)
        for color, label in [("#0a84ff","Account"), ("#ff9f0a","Device (IMEI/UUID)"), ("#30d158","IP Address"), ("#ff453a","Transfer edge")]:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:0.6rem;padding:0.35rem 0;
                        font-size:0.8rem;color:#ebebf0">
                <div style="width:7px;height:7px;border-radius:50%;background:{color};flex-shrink:0"></div>
                {label}
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# GRAPH
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Graph":
    page_header("Graph", "Explorer")

    st.markdown("""
    <div style="background:#0a0a0a;border:1px solid #1c1c1e;border-radius:8px;
                padding:0.65rem 1rem;font-size:0.72rem;color:#636366;
                font-family:'DM Mono',monospace;margin-bottom:1.25rem">
        visualize_network_static(graph_data) — Week 1 core deliverable
    </div>
    """, unsafe_allow_html=True)

    view_mode = st.radio("", ["Static", "Interactive"], horizontal=True)
    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)

    import random
    sample_size = 300
    if len(nodes) > sample_size:
        sampled_ids = set(n["id"] for n in random.sample(nodes, sample_size))
        display_data = {
            "nodes": [n for n in nodes if n["id"] in sampled_ids],
            "edges": [e for e in edges if e["source"] in sampled_ids and e["target"] in sampled_ids],
        }
    else:
        display_data = graph_data

    if view_mode == "Static":
        fig = visualize_network_static(display_data)
        st.pyplot(fig, use_container_width=True)
    else:
        html_path = visualize_network_interactive(display_data)
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        st.components.v1.html(html_content, height=520, scrolling=False)

    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
    with st.expander("Raw graph_data — normalized schema"):
        st.json({"nodes": nodes[:5], "edges": edges[:5], "note": f"showing 5 of {len(nodes)} nodes, {len(edges)} edges"})

# ═══════════════════════════════════════════════════════════════════════════════
# ABSTRACT
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Abstract":
    page_header("Technical", "Abstract")
    st.markdown(f"""
    <div style="background:#0a0a0a;border:1px solid #1c1c1e;border-radius:12px;
                padding:2rem;font-size:0.88rem;line-height:1.9;
                color:#ebebf0;font-weight:300;white-space:pre-wrap">
{TECHNICAL_ABSTRACT}
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
    st.download_button("Download ↓", data=TECHNICAL_ABSTRACT,
                       file_name="GraphSentry_Abstract.md", mime="text/markdown")

# ═══════════════════════════════════════════════════════════════════════════════
# ABOUT
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "About":
    page_header("Branch", "Info")
    st.markdown("""
    <div style="background:#0a0a0a;border:1px solid #1c1c1e;border-radius:12px;padding:2rem">
        <div style="font-size:0.65rem;color:#636366;letter-spacing:0.12em;
                    text-transform:uppercase;margin-bottom:1.25rem">
            feature/dashboard-docs · Member 3 · Vidhu
        </div>
        <div style="font-size:0.65rem;color:#636366;letter-spacing:0.1em;
                    text-transform:uppercase;margin-bottom:0.6rem">Deliverables</div>
        <div style="font-size:0.83rem;color:#ebebf0;line-height:2.1;font-weight:300;margin-bottom:1.75rem">
            ✓ &nbsp;Streamlit dashboard — minimal black UI<br>
            ✓ &nbsp;<span style="font-family:'DM Mono',monospace;font-size:0.78rem;color:#636366">visualize_network_static(graph_data)</span><br>
            ✓ &nbsp;<span style="font-family:'DM Mono',monospace;font-size:0.78rem;color:#636366">visualize_network_interactive(graph_data)</span><br>
            ✓ &nbsp;Abstract from <span style="font-family:'DM Mono',monospace;font-size:0.78rem;color:#636366">docs/technical_abstract.md</span><br>
            ✓ &nbsp;Live data from <span style="font-family:'DM Mono',monospace;font-size:0.78rem;color:#636366">data/nexus_graph_output.json</span>
        </div>
        <div style="font-size:0.65rem;color:#636366;letter-spacing:0.1em;
                    text-transform:uppercase;margin-bottom:0.6rem">Soorya's Schema (normalized)</div>
        <div style="font-family:'DM Mono',monospace;font-size:0.75rem;color:#636366;
                    line-height:1.9;margin-bottom:1.75rem">
            nodes: { id, type }<br>
            edges: { source, target, relation, timestamp, channel }<br>
            → normalized to: { id, type, label, risk }
        </div>
        <div style="font-size:0.65rem;color:#3a3a3c;font-family:'DM Mono',monospace">
            Streamlit · NetworkX · PyVis · Matplotlib · Python 3.10+
        </div>
    </div>
    """, unsafe_allow_html=True)
    