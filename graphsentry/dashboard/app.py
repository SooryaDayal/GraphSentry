"""
GraphSentry Dashboard - feature/sar-automation (Week 2)
Member 3: Vidhu
New: generate_pmla_sar() — SAR PDF download from flagged mule ring
"""

import streamlit as st
import os
import json
import random
import tempfile
from datetime import datetime
from visualizer import visualize_network_static, visualize_network_interactive
from sar_generator import generate_pmla_sar

# ── Load Abstract ─────────────────────────────────────────────────────────────
def load_abstract() -> str:
    path = os.path.join(os.path.dirname(__file__), "../docs/technical_abstract.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Abstract file not found. Ensure `docs/technical_abstract.md` exists."

# ── Schema normalizer (Soorya's format → dashboard format) ───────────────────
def normalize_graph_data(raw: dict) -> dict:
    edges = raw.get("edges", [])

    degree = {}
    for e in edges:
        degree[e["source"]] = degree.get(e["source"], 0) + 1
        degree[e["target"]] = degree.get(e["target"], 0) + 1

    high_risk_channels = {"RTGS", "IMPS"}
    high_risk_nodes = set()
    for e in edges:
        if e.get("channel") in high_risk_channels:
            high_risk_nodes.add(e["source"])
            high_risk_nodes.add(e["target"])

    device_connections = {}
    for e in edges:
        if e.get("relation") == "uses_device":
            tgt = e["target"]
            device_connections[tgt] = device_connections.get(tgt, 0) + 1

    shared_devices = {d for d, cnt in device_connections.items() if cnt >= 3}

    def derive_risk(nid, ntype):
        if nid in shared_devices:      return "high"
        if nid in high_risk_nodes:     return "high"
        d = degree.get(nid, 0)
        if d >= 5:  return "high"
        if d >= 2:  return "medium"
        return "low"

    def derive_label(nid, ntype):
        if ntype == "account": return nid.replace("ACT_", "Acct-")
        if ntype == "device":  return nid.replace("IMEI_", "IMEI-").replace("UUID_", "UUID-")
        if ntype == "ip":
            parts  = nid.replace("IP_", "").replace("_", ".")
            octets = parts.split(".")
            return ".".join(octets[:3]) + ".x" if len(octets) == 4 else nid
        return nid

    nodes = []
    for n in raw.get("nodes", []):
        nid, ntype = n["id"], n.get("type", "account")
        nodes.append({"id": nid, "type": ntype,
                      "label": derive_label(nid, ntype),
                      "risk":  derive_risk(nid, ntype)})
    return {"nodes": nodes, "edges": edges}

# ── Load graph data ───────────────────────────────────────────────────────────
def get_fallback_data() -> dict:
    return {
        "nodes": [
            {"id":"ACC_001","type":"account","label":"Acct-001","risk":"high"},
            {"id":"ACC_002","type":"account","label":"Acct-002","risk":"medium"},
            {"id":"ACC_003","type":"account","label":"Acct-003","risk":"high"},
            {"id":"ACC_004","type":"account","label":"Acct-004","risk":"low"},
            {"id":"ACC_005","type":"account","label":"Acct-005","risk":"high"},
            {"id":"DEV_IMEI_AAA","type":"device","label":"IMEI-AAA","risk":"high"},
            {"id":"DEV_IMEI_BBB","type":"device","label":"IMEI-BBB","risk":"low"},
            {"id":"IP_192.168.1.1","type":"ip","label":"IP-192.168.x","risk":"high"},
            {"id":"IP_10.0.0.5","type":"ip","label":"IP-10.0.0.x","risk":"medium"},
        ],
        "edges": [
            {"source":"ACC_001","target":"DEV_IMEI_AAA","relation":"uses_device","timestamp":"2026-02-21 10:00:00","channel":"RTGS"},
            {"source":"ACC_002","target":"DEV_IMEI_AAA","relation":"uses_device","timestamp":"2026-02-21 10:05:00","channel":"UPI"},
            {"source":"ACC_003","target":"DEV_IMEI_AAA","relation":"uses_device","timestamp":"2026-02-21 10:10:00","channel":"IMPS"},
            {"source":"ACC_001","target":"IP_192.168.1.1","relation":"uses_ip","timestamp":"2026-02-21 10:00:00","channel":""},
            {"source":"ACC_002","target":"IP_192.168.1.1","relation":"uses_ip","timestamp":"2026-02-21 10:05:00","channel":""},
            {"source":"ACC_004","target":"DEV_IMEI_BBB","relation":"uses_device","timestamp":"2026-02-21 11:00:00","channel":"ATM"},
            {"source":"ACC_004","target":"IP_10.0.0.5","relation":"uses_ip","timestamp":"2026-02-21 11:00:00","channel":""},
            {"source":"ACC_001","target":"ACC_003","relation":"transfer","timestamp":"2026-02-21 10:15:00","channel":"RTGS"},
            {"source":"ACC_003","target":"ACC_005","relation":"transfer","timestamp":"2026-02-21 10:17:00","channel":"IMPS"},
            {"source":"ACC_001","target":"ACC_005","relation":"transfer","timestamp":"2026-02-21 10:20:00","channel":"UPI"},
        ]
    }

def load_graph_data() -> tuple:
    path = os.path.join(os.path.dirname(__file__), "../data/nexus_graph_output.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return normalize_graph_data(raw), True
    except FileNotFoundError:
        return get_fallback_data(), False

# ── Build frozen cluster dict from graph data ─────────────────────────────────
def build_frozen_cluster(graph_data: dict, cluster_id: str = None) -> dict:
    """
    Packages graph data into the frozen_cluster_data format
    expected by generate_pmla_sar().
    """
    nodes  = graph_data.get("nodes", [])
    edges  = graph_data.get("edges", [])

    device_connections = {}
    for e in edges:
        if e.get("relation") == "uses_device":
            tgt = e["target"]
            device_connections[tgt] = device_connections.get(tgt, 0) + 1
    shared_devices = [d for d, cnt in device_connections.items() if cnt >= 3]

    transfer_edges  = [e for e in edges if e.get("relation") == "transfer"]
    transfer_chain  = []
    if transfer_edges:
        transfer_chain = [transfer_edges[0]["source"]] + [e["target"] for e in transfer_edges[:5]]

    channels_used   = list(set(e.get("channel", "") for e in edges if e.get("channel")))
    high_risk_nodes = [n for n in nodes if n.get("risk") == "high"]

    return {
        "cluster_id":       cluster_id or f"GS-RING-{datetime.now().strftime('%H%M%S')}",
        "detected_at":      datetime.now().isoformat(),
        "trigger_reason":   "Shared device fingerprint across 3+ accounts + rapid transfer chain detected",
        "total_nodes":      len(nodes),
        "high_risk_nodes":  len(high_risk_nodes),
        "estimated_amount": "Undetermined — pending investigation",
        "accounts":         nodes,
        "edges":            edges,
        "shared_devices":   shared_devices,
        "transfer_chain":   transfer_chain,
        "channels_used":    channels_used,
    }

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
section.main { margin-left: 0 !important; }
[data-testid="stSidebar"][aria-expanded="false"] { margin-left: -200px !important; }
#MainMenu, footer, header { visibility: hidden !important; }
.stDeployButton, [data-testid="stToolbar"] { display: none !important; }
[data-testid="collapsedControl"] { color: #3a3a3c !important; }

[data-testid="stSidebar"] {
    background-color: #000000 !important;
    border-right: 1px solid #1c1c1e !important;
    min-width: 200px !important;
    max-width: 200px !important;
}
[data-testid="stSidebar"] > div { padding: 2rem 1.25rem !important; }
[data-testid="stSidebarNav"] { display: none !important; }

.stRadio > label { display: none !important; }
.stRadio > div { display: flex !important; flex-direction: column !important; gap: 0 !important; }
.stRadio label[data-baseweb="radio"] {
    display: flex !important; align-items: center !important;
    padding: 0.45rem 0.6rem !important; border-radius: 6px !important;
}
.stRadio label[data-baseweb="radio"] > div:first-child { display: none !important; }
.stRadio label[data-baseweb="radio"] p {
    font-size: 0.82rem !important; font-weight: 400 !important; color: #636366 !important;
}
.stRadio label[aria-checked="true"][data-baseweb="radio"] { background: #1c1c1e !important; }
.stRadio label[aria-checked="true"][data-baseweb="radio"] p {
    color: #f5f5f7 !important; font-weight: 500 !important;
}

/* SAR button — distinct red */
.sar-btn > div > button {
    background: #1c1c1e !important;
    color: #ff453a !important;
    border: 1px solid #3a1a1a !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    font-family: 'DM Sans', sans-serif !important;
    padding: 0.55rem 1.4rem !important;
    letter-spacing: 0.02em !important;
    width: 100% !important;
}
.sar-btn > div > button:hover { background: #2c1a1a !important; border-color: #ff453a !important; }

/* Download button */
.stDownloadButton button {
    background: #1c1c1e !important; color: #f5f5f7 !important;
    border: none !important; border-radius: 8px !important;
    font-size: 0.8rem !important; font-weight: 500 !important;
    font-family: 'DM Sans', sans-serif !important; padding: 0.5rem 1.2rem !important;
}
.stDownloadButton button:hover { background: #2c2c2e !important; }

.streamlit-expanderHeader {
    background: #0a0a0a !important; border: 1px solid #1c1c1e !important;
    border-radius: 8px !important; color: #636366 !important; font-size: 0.78rem !important;
}
.streamlit-expanderContent {
    background: #0a0a0a !important; border: 1px solid #1c1c1e !important;
    border-top: none !important; border-radius: 0 0 8px 8px !important;
}
</style>
""", unsafe_allow_html=True)

# ── Load ──────────────────────────────────────────────────────────────────────
graph_data, is_live   = load_graph_data()
TECHNICAL_ABSTRACT    = load_abstract()

nodes  = graph_data.get("nodes", [])
edges  = graph_data.get("edges", [])
total_nodes = len(nodes)
total_edges = len(edges)
high_risk   = sum(1 for n in nodes if n.get("risk") == "high")

device_connections = {}
for e in edges:
    if e.get("relation") == "uses_device":
        tgt = e["target"]
        device_connections[tgt] = device_connections.get(tgt, 0) + 1
shared_devs    = sum(1 for cnt in device_connections.values() if cnt >= 3)
shared_dev_ids = [d for d, cnt in device_connections.items() if cnt >= 3]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="font-size:0.65rem;font-weight:600;letter-spacing:0.2em;
                color:#3a3a3c;text-transform:uppercase;margin-bottom:1.75rem">
        GraphSentry
    </div>
    """, unsafe_allow_html=True)
    page = st.radio("", ["Dashboard", "SAR Generator", "Graph", "Abstract", "About"])
    st.markdown("""
    <div style="margin-top:3rem;font-size:0.65rem;color:#3a3a3c;
                font-family:'DM Mono',monospace;line-height:1.8">
        feature/sar-automation<br>Member 3 · Vidhu<br>Sprint 2
    </div>
    """, unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def page_header(sub, bold):
    st.markdown(f"""
    <div style="font-size:0.65rem;font-weight:600;letter-spacing:0.2em;
                color:#636366;text-transform:uppercase;margin-bottom:0.4rem">
        GraphSentry
    </div>
    <div style="font-size:1.75rem;font-weight:300;color:#f5f5f7;
                letter-spacing:-0.03em;margin-bottom:1.75rem">
        {sub} <span style="font-weight:600">{bold}</span>
    </div>
    """, unsafe_allow_html=True)

def section_label(text):
    st.markdown(f"""
    <div style="font-size:0.65rem;font-weight:600;letter-spacing:0.12em;
                color:#636366;text-transform:uppercase;margin-bottom:0.75rem">
        {text}
    </div>
    """, unsafe_allow_html=True)

def metric_card(col, value, label, sub):
    with col:
        st.markdown(f"""
        <div style="background:#0a0a0a;border:1px solid #1c1c1e;border-radius:12px;
                    padding:1.25rem 1.4rem">
            <div style="font-size:0.65rem;font-weight:600;color:#636366;
                        letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.5rem">{label}</div>
            <div style="font-size:2rem;font-weight:300;color:#f5f5f7;
                        letter-spacing:-0.04em;line-height:1">{value}</div>
            <div style="font-size:0.68rem;color:#3a3a3c;margin-top:0.35rem;
                        font-family:'DM Mono',monospace">{sub}</div>
        </div>
        """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
if page == "Dashboard":
    data_color  = "#30d158" if is_live else "#ff9f0a"
    data_label  = "Live" if is_live else "Fallback"
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

    c1, c2, c3, c4 = st.columns(4, gap="small")
    metric_card(c1, total_nodes, "Nodes",         "accounts · devices · ips")
    metric_card(c2, total_edges, "Edges",         "active links")
    metric_card(c3, high_risk,   "High Risk",     "nodes flagged")
    metric_card(c4, shared_devs, "Shared Device", "multi-account device")

    st.markdown('<div style="height:2rem"></div>', unsafe_allow_html=True)

    col_graph, col_right = st.columns([3, 2], gap="large")

    with col_graph:
        section_label("Entity-Nexus Graph")
        sample_size = 300
        if len(nodes) > sample_size:
            sampled_ids  = set(n["id"] for n in random.sample(nodes, sample_size))
            display_data = {
                "nodes": [n for n in nodes if n["id"] in sampled_ids],
                "edges": [e for e in edges if e["source"] in sampled_ids and e["target"] in sampled_ids],
            }
            st.markdown(f"""
            <div style="font-size:0.68rem;color:#3a3a3c;font-family:'DM Mono',monospace;
                        margin-bottom:0.5rem">rendering {sample_size} of {len(nodes)} nodes</div>
            """, unsafe_allow_html=True)
        else:
            display_data = graph_data

        html_path = visualize_network_interactive(display_data)
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        st.components.v1.html(html_content, height=520, scrolling=False)
        st.markdown(f"""
        <div style="font-size:0.65rem;color:#3a3a3c;font-family:'DM Mono',monospace;margin-top:0.4rem">
            source: {data_source} · scroll to zoom · hover for details
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        section_label("Alerts")

        transfer_edges = [e for e in edges if e.get("relation") == "transfer"]
        rtgs_edges     = [e for e in edges if e.get("channel") == "RTGS"]

        alerts = []
        for d in shared_dev_ids[:2]:
            cnt = device_connections[d]
            alerts.append(("#ff453a","HIGH",f"{d} linked to {cnt} accounts","Mule Ring pattern"))
        if transfer_edges:
            e0 = transfer_edges[0]
            alerts.append(("#ff453a","HIGH",f"{e0['source']} → {e0['target']}",f"Transfer · {e0.get('channel','')}"))
        if rtgs_edges:
            alerts.append(("#ffd60a","MED",f"{len(rtgs_edges)} RTGS transactions flagged","High-value channel"))
        if high_risk:
            alerts.append(("#ffd60a","MED",f"{high_risk} high-risk nodes active","Risk threshold exceeded"))
        low_nodes = [n for n in nodes if n.get("risk") == "low"]
        if low_nodes:
            alerts.append(("#30d158","LOW",f"{len(low_nodes)} nodes — normal activity","No anomalies"))

        st.markdown('<div style="background:#0a0a0a;border:1px solid #1c1c1e;'
                    'border-radius:12px;padding:0.25rem 1.25rem">', unsafe_allow_html=True)
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
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # ── SAR Button ────────────────────────────────────────────────────────
        st.markdown('<div style="height:1.25rem"></div>', unsafe_allow_html=True)
        section_label("Compliance")

        st.markdown('<div style="background:#0a0a0a;border:1px solid #1c1c1e;'
                    'border-radius:12px;padding:1rem 1.25rem">', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:0.8rem;color:#ebebf0;margin-bottom:0.3rem;font-weight:500">
            Generate SAR Report
        </div>
        <div style="font-size:0.72rem;color:#48484a;font-family:'DM Mono',monospace;
                    margin-bottom:1rem">
            PMLA 2002 · Section 12 · FIU-IND
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="sar-btn">', unsafe_allow_html=True)
        if st.button("⬡  Generate SAR PDF", key="sar_dashboard"):
            with st.spinner("Generating PMLA-compliant SAR..."):
                cluster_data = build_frozen_cluster(graph_data, cluster_id="GS-RING-DASH-001")
                pdf_path     = generate_pmla_sar(cluster_data)
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
            fname = f"SAR_{cluster_data['cluster_id']}_{datetime.now().strftime('%Y%m%d')}.pdf"
            st.download_button(
                label="⬇  Download SAR PDF",
                data=pdf_bytes,
                file_name=fname,
                mime="application/pdf",
                key="dl_sar_dashboard"
            )
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div style="height:1.25rem"></div>', unsafe_allow_html=True)
        section_label("Legend")
        st.markdown('<div style="background:#0a0a0a;border:1px solid #1c1c1e;border-radius:12px;padding:0.75rem 1.25rem">', unsafe_allow_html=True)
        for color, label in [("#0a84ff","Account"),("#ff9f0a","Device (IMEI/UUID)"),
                              ("#30d158","IP Address"),("#ff453a","Transfer edge")]:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:0.6rem;padding:0.35rem 0;
                        font-size:0.8rem;color:#ebebf0">
                <div style="width:7px;height:7px;border-radius:50%;background:{color};flex-shrink:0"></div>
                {label}
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SAR GENERATOR PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "SAR Generator":
    page_header("SAR", "Generator")

    st.markdown("""
    <div style="background:#0a0a0a;border:1px solid #1c1c1e;border-radius:8px;
                padding:0.65rem 1rem;font-size:0.72rem;color:#636366;
                font-family:'DM Mono',monospace;margin-bottom:1.75rem">
        generate_pmla_sar(frozen_cluster_data) — Week 2 core deliverable
    </div>
    """, unsafe_allow_html=True)

    col_form, col_preview = st.columns([1, 1], gap="large")

    with col_form:
        section_label("Configure Report")
        st.markdown('<div style="background:#0a0a0a;border:1px solid #1c1c1e;'
                    'border-radius:12px;padding:1.5rem">', unsafe_allow_html=True)

        cluster_id_input = st.text_input(
            "Cluster ID", value="GS-RING-001",
            help="Unique identifier for this mule ring",
            label_visibility="visible"
        )
        estimated_amount = st.text_input(
            "Estimated Amount", value="INR 4,72,000",
            label_visibility="visible"
        )
        trigger_reason = st.text_area(
            "Trigger Reason",
            value="Shared device IMEI_67329 linked to 3 accounts. "
                  "Rapid transfer chain detected within 180 seconds of deposit. "
                  "RTGS high-value channel flagged.",
            height=80,
            label_visibility="visible"
        )

        st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)

        # Node type breakdown
        acct_nodes   = [n for n in nodes if n.get("type") == "account"]
        device_nodes = [n for n in nodes if n.get("type") == "device"]
        ip_nodes     = [n for n in nodes if n.get("type") == "ip"]

        st.markdown(f"""
        <div style="font-size:0.68rem;color:#3a3a3c;font-family:'DM Mono',monospace;
                    line-height:2;margin-top:0.5rem">
            Cluster: {total_nodes} nodes
            ({len(acct_nodes)} accounts · {len(device_nodes)} devices · {len(ip_nodes)} IPs)<br>
            Edges: {total_edges} · High risk: {high_risk} · Shared devices: {shared_devs}
        </div>
        """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)

        st.markdown('<div class="sar-btn">', unsafe_allow_html=True)
        generate_clicked = st.button("⬡  Generate PMLA SAR PDF", key="sar_page")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_preview:
        section_label("Report Preview")
        st.markdown(f"""
        <div style="background:#0a0a0a;border:1px solid #1c1c1e;border-radius:12px;
                    padding:1.5rem;font-family:'DM Mono',monospace;font-size:0.75rem;
                    color:#636366;line-height:2">
            <div style="color:#f5f5f7;font-size:0.85rem;font-weight:500;
                        margin-bottom:1rem;font-family:'DM Sans',sans-serif">
                SAR / {cluster_id_input}
            </div>
            <div><span style="color:#3a3a3c">report_id</span> &nbsp;&nbsp;&nbsp;
                 SAR/GS/{datetime.now().strftime('%Y%m%d')}/{cluster_id_input[-4:].upper()}</div>
            <div><span style="color:#3a3a3c">cluster_id</span> &nbsp;&nbsp;{cluster_id_input}</div>
            <div><span style="color:#3a3a3c">detected</span> &nbsp;&nbsp;&nbsp;
                 {datetime.now().strftime('%d %B %Y  %H:%M IST')}</div>
            <div><span style="color:#3a3a3c">nodes</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{total_nodes}</div>
            <div><span style="color:#3a3a3c">high_risk</span> &nbsp;&nbsp;{high_risk}</div>
            <div><span style="color:#3a3a3c">amount</span> &nbsp;&nbsp;&nbsp;&nbsp;{estimated_amount}</div>
            <div><span style="color:#3a3a3c">channels</span> &nbsp;&nbsp;&nbsp;
                 {', '.join(list(set(e.get('channel','') for e in edges if e.get('channel'))))}</div>
            <div><span style="color:#3a3a3c">status</span> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                 <span style="color:#ff453a">FROZEN</span></div>
            <div style="margin-top:1rem;padding-top:1rem;border-top:1px solid #1c1c1e;
                        font-size:0.68rem;color:#3a3a3c">
                PMLA 2002 · Section 12 · FIU-IND<br>
                GraphSentry Compliance Engine v1.0
            </div>
        </div>
        """, unsafe_allow_html=True)

    if generate_clicked:
        with st.spinner("Generating PMLA-compliant SAR PDF..."):
            cluster_data = build_frozen_cluster(graph_data, cluster_id=cluster_id_input)
            cluster_data["estimated_amount"] = estimated_amount
            cluster_data["trigger_reason"]   = trigger_reason
            pdf_path = generate_pmla_sar(cluster_data)
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

        st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
        fname = f"SAR_{cluster_id_input}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        st.success("SAR generated successfully.")
        st.download_button(
            label="⬇  Download SAR PDF",
            data=pdf_bytes,
            file_name=fname,
            mime="application/pdf",
            key="dl_sar_page"
        )

# ═══════════════════════════════════════════════════════════════════════════════
# GRAPH
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "Graph":
    page_header("Graph", "Explorer")
    st.markdown("""
    <div style="background:#0a0a0a;border:1px solid #1c1c1e;border-radius:8px;
                padding:0.65rem 1rem;font-size:0.72rem;color:#636366;
                font-family:'DM Mono',monospace;margin-bottom:1.25rem">
        visualize_network_static(graph_data) — Week 1 · visualize_network_interactive(graph_data) — Week 1
    </div>
    """, unsafe_allow_html=True)

    view_mode = st.radio("", ["Static", "Interactive"], horizontal=True)
    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)

    sample_size = 300
    if len(nodes) > sample_size:
        sampled_ids  = set(n["id"] for n in random.sample(nodes, sample_size))
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
        st.json({"nodes": nodes[:5], "edges": edges[:5],
                 "note": f"showing 5 of {len(nodes)} nodes, {len(edges)} edges"})

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
            feature/sar-automation · Member 3 · Vidhu · Sprint 2
        </div>
        <div style="font-size:0.65rem;color:#636366;letter-spacing:0.1em;
                    text-transform:uppercase;margin-bottom:0.6rem">Week 2 Deliverables</div>
        <div style="font-size:0.83rem;color:#ebebf0;line-height:2.1;font-weight:300;margin-bottom:1.75rem">
            ✓ &nbsp;<span style="font-family:'DM Mono',monospace;font-size:0.78rem;color:#636366">generate_pmla_sar(frozen_cluster_data)</span><br>
            ✓ &nbsp;SAR Generator page — configurable cluster ID, amount, trigger reason<br>
            ✓ &nbsp;One-click PDF download from Dashboard alerts panel<br>
            ✓ &nbsp;PMLA Section 12 compliant structure<br>
            ✓ &nbsp;FIU-IND report format — 5 sections, signature block
        </div>
        <div style="font-size:0.65rem;color:#636366;letter-spacing:0.1em;
                    text-transform:uppercase;margin-bottom:0.6rem">SAR Input Schema</div>
        <div style="font-family:'DM Mono',monospace;font-size:0.75rem;color:#636366;
                    line-height:1.9;margin-bottom:1.75rem">
            cluster_id, detected_at, trigger_reason<br>
            total_nodes, high_risk_nodes, estimated_amount<br>
            accounts[], edges[], shared_devices[]<br>
            transfer_chain[], channels_used[]
        </div>
        <div style="font-size:0.65rem;color:#3a3a3c;font-family:'DM Mono',monospace">
            Streamlit · ReportLab · NetworkX · PyVis · Python 3.10+
        </div>
    </div>
    """, unsafe_allow_html=True)
    