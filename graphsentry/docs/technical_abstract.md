"""
abstract.py — GraphSentry Technical Abstract
For display on the dashboard and submission
"""

TECHNICAL_ABSTRACT = """
<strong>GraphSentry: Real-Time Money Mule Detection via Temporal-Relational Graph Neural Networks</strong>
<br><br>
Money muling — the use of third-party accounts to launder fraudulently obtained funds — 
represents one of the most sophisticated and rapidly evolving threats facing modern financial 
institutions. Traditional fraud detection systems rely on static, rule-based, flat-file analysis 
that fails to capture the complex, multi-channel behavioral patterns exhibited by coordinated 
mule networks.
<br><br>
GraphSentry addresses this gap by constructing a dynamic <strong>Heterogeneous Multigraph 
(Entity-Nexus)</strong> that integrates transaction logs across Mobile Banking, Web Banking, 
ATMs, and Payment Systems (RTGS/IMPS/UPI) into a unified relational structure. Each bank 
account, device identifier (IMEI/UUID/Browser Fingerprint), and IP address is modeled as a 
typed node, with their interactions forming a directed multigraph of behavioral evidence.
<br><br>
The system's intelligence layer — the <strong>Sentinel GNN Core</strong> — employs a 
Relational Graph Attention Network (RGAT) to assign risk-weighted attention across heterogeneous 
edge types. Temporal dynamics are encoded by flagging fund transfers occurring within a 180-second 
deposit window. Value-Taint Persistence tracks stolen fund paths even through delayed layering 
operations, while the Louvain Community Detection algorithm automatically surfaces Star Patterns 
indicative of hub-and-spoke mule ring topology.
<br><br>
Pre-fraud signals — including dormant account reactivation, beneficiary addition spikes, 
micro-transaction probing (₹1/₹10), SIM-Swap correlation, and new-payee bypass behavior — are 
integrated as graph-level features to detect mule ring preparation before any significant funds 
move.
<br><br>
The <strong>Real-Time Reflex Engine</strong> performs local sub-graph extraction and in-memory 
inference using PyTorch Geometric, achieving end-to-end response times under 100 milliseconds 
at scale. Detected fraud triggers Pre-Emptive Cluster-Blocking, freezing all accounts within 
the identified mule ring simultaneously.
<br><br>
GraphSentry is architecturally compliant with Reserve Bank of India (RBI) guidelines through 
a <strong>Federated Learning</strong> framework that enables cross-institutional model 
improvement without exposing raw customer data. Explainable AI (XAI) dashboards provide 
investigators with fund-flow reasoning, and automated Suspicious Activity Reports (SARs) 
are generated in compliance with the Prevention of Money Laundering Act (PMLA).
<br><br>
GraphSentry represents a paradigm shift from reactive, transaction-level fraud detection to 
proactive, network-level disruption of the entire money muling lifecycle.
"""
