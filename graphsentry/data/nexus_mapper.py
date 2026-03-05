"""
nexus_mapper.py  —  GraphSentry Data Enrichment Layer
------------------------------------------------------
Reads IBM AMLSim CSVs (accounts, transactions, alerts) and enriches
with synthetic-but-realistic behavioral fields:
  • channel      — Indian payment channel (UPI / Mobile App / Web Banking / ATM / RTGS / IMPS)
  • device_id    — IMEI-style device; fraud rings share devices across accounts
  • ip_address   — fraud rings share IPs; normal accounts get small personal pools

Output:
  • enriched_transactions.csv   — transactions + synthetic fields
  • nexus_graph_output.json     — graph nodes + edges for graph_builder.py
  • graphsentry_dataset.csv     — FINAL unified CSV (all sources merged)
"""

import pandas as pd
import numpy as np
import json
import hashlib
import random
from pathlib import Path

# ── reproducibility ──────────────────────────────────────────────────────────
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# ── paths ────────────────────────────────────────────────────────────────────
DATA_DIR         = Path(r"D:\GraphSentry\graphsentry\data")
ACCOUNTS_CSV     = DATA_DIR / "accounts.csv"
TRANSACTIONS_CSV = DATA_DIR / "transactions.csv"
ALERTS_CSV       = DATA_DIR / "alerts.csv"
OUT_CSV          = DATA_DIR / "enriched_transactions.csv"
OUT_JSON         = DATA_DIR / "nexus_graph_output.json"
OUT_FINAL        = DATA_DIR / "graphsentry_dataset.csv"

# ─────────────────────────────────────────────────────────────────────────────
# 1.  LOAD IBM DATA
# ─────────────────────────────────────────────────────────────────────────────
print("Loading IBM AMLSim CSVs …")
accounts     = pd.read_csv(ACCOUNTS_CSV)
transactions = pd.read_csv(TRANSACTIONS_CSV)
alerts       = pd.read_csv(ALERTS_CSV)

# Normalise column names (strip whitespace)
accounts.columns     = accounts.columns.str.strip()
transactions.columns = transactions.columns.str.strip()
alerts.columns       = alerts.columns.str.strip()

print(f"  accounts     : {len(accounts):,} rows")
print(f"  transactions : {len(transactions):,} rows")
print(f"  alerts       : {len(alerts):,} rows")

# ─────────────────────────────────────────────────────────────────────────────
# 2.  BUILD FRAUD-RING LOOKUP  (ALERT_ID → set of account IDs)
# ─────────────────────────────────────────────────────────────────────────────
alert_to_accounts: dict[str, set] = {}
for _, row in alerts[alerts["IS_FRAUD"] == 1].iterrows():
    aid = str(row["ALERT_ID"])
    alert_to_accounts.setdefault(aid, set())
    alert_to_accounts[aid].add(str(row["SENDER_ACCOUNT_ID"]))
    alert_to_accounts[aid].add(str(row["RECEIVER_ACCOUNT_ID"]))

# Reverse: account → alert_id (first fraud alert it belongs to)
account_to_alert: dict[str, str] = {}
for alert_id, accs in alert_to_accounts.items():
    for acc in accs:
        account_to_alert.setdefault(acc, alert_id)

fraud_accounts = set(account_to_alert.keys())
print(f"  fraud accounts in alerts: {len(fraud_accounts):,}")

# ─────────────────────────────────────────────────────────────────────────────
# 3.  CHANNEL  — rule-based + weighted random
# ─────────────────────────────────────────────────────────────────────────────
CHANNEL_BY_TXTYPE = {
    "CASH_OUT" : ("ATM", 1.0),
    "CASH_IN"  : ("ATM", 1.0),
    "DEBIT"    : ("ATM", 0.7),
}

CHANNEL_WEIGHTS_LARGE = {   # TX_AMOUNT >= 50,000
    "RTGS"        : 0.45,
    "IMPS"        : 0.25,
    "Web Banking" : 0.20,
    "Mobile App"  : 0.10,
}

CHANNEL_WEIGHTS_SMALL = {   # TX_AMOUNT < 50,000
    "UPI"         : 0.50,
    "Mobile App"  : 0.25,
    "Web Banking" : 0.20,
    "ATM"         : 0.05,
}

def assign_channel(tx_type: str, amount: float) -> str:
    tx_type = str(tx_type).upper()
    if tx_type in CHANNEL_BY_TXTYPE:
        fixed_ch, prob = CHANNEL_BY_TXTYPE[tx_type]
        if random.random() < prob:
            return fixed_ch
    weights = CHANNEL_WEIGHTS_LARGE if amount >= 50_000 else CHANNEL_WEIGHTS_SMALL
    return random.choices(list(weights.keys()), weights=list(weights.values()))[0]

# ─────────────────────────────────────────────────────────────────────────────
# 4.  DEVICE_ID  — 1–2 per normal account; fraud rings share devices
# ─────────────────────────────────────────────────────────────────────────────
def _imei_hash(seed_str: str, suffix: int = 0) -> str:
    """Deterministic fake IMEI from a string seed."""
    raw = hashlib.md5(f"{seed_str}{suffix}".encode()).hexdigest()
    return f"IMEI_{int(raw[:10], 16) % 10**9:09d}"

account_devices: dict[str, list[str]] = {}
all_accounts = accounts["ACCOUNT_ID"].astype(str).tolist()

# Normal accounts
for acc in all_accounts:
    if acc in fraud_accounts:
        continue
    n_devices = random.choices([1, 2], weights=[0.75, 0.25])[0]
    account_devices[acc] = [_imei_hash(acc, i) for i in range(n_devices)]

# Fraud ring accounts — share devices within the ring
for alert_id, accs in alert_to_accounts.items():
    n_shared = random.choices([1, 2], weights=[0.6, 0.4])[0]
    shared_devs = [f"IMEI_ALERT_{alert_id}_{i}" for i in range(n_shared)]
    for acc in accs:
        if random.random() < 0.70:
            account_devices[acc] = shared_devs
        else:
            account_devices[acc] = [_imei_hash(acc, 0)] + shared_devs

def pick_device(account_id: str) -> str:
    devs = account_devices.get(str(account_id), [_imei_hash(str(account_id))])
    return random.choice(devs)

# ─────────────────────────────────────────────────────────────────────────────
# 5.  IP_ADDRESS  — private pool per account; fraud rings share IPs
# ─────────────────────────────────────────────────────────────────────────────
def _rand_ip() -> str:
    """Random RFC-1918 private IP."""
    prefix = random.choice(["192.168", "10.0", "172.16"])
    return f"{prefix}.{random.randint(0, 255)}.{random.randint(1, 254)}"

account_ips: dict[str, list[str]] = {}

# Normal accounts
for acc in all_accounts:
    if acc in fraud_accounts:
        continue
    n_ips = random.choices([1, 2, 3], weights=[0.5, 0.35, 0.15])[0]
    account_ips[acc] = [_rand_ip() for _ in range(n_ips)]

# Fraud rings share a small IP pool
for alert_id, accs in alert_to_accounts.items():
    shared_ips = [_rand_ip() for _ in range(random.randint(1, 2))]
    for acc in accs:
        personal_ips = [_rand_ip() for _ in range(random.randint(0, 1))]
        if random.random() < 0.80:
            account_ips[acc] = shared_ips + personal_ips
        else:
            account_ips[acc] = [_rand_ip() for _ in range(2)]

def pick_ip(account_id: str) -> str:
    pool = account_ips.get(str(account_id), [_rand_ip()])
    return random.choice(pool)

# ─────────────────────────────────────────────────────────────────────────────
# 6.  ENRICH TRANSACTIONS
# ─────────────────────────────────────────────────────────────────────────────
print("\nEnriching transactions …")

transactions["channel"] = transactions.apply(
    lambda r: assign_channel(r["TX_TYPE"], r["TX_AMOUNT"]), axis=1
)
transactions["device_id"] = transactions["SENDER_ACCOUNT_ID"].apply(
    lambda a: pick_device(str(a))
)
transactions["ip_address"] = transactions["SENDER_ACCOUNT_ID"].apply(
    lambda a: pick_ip(str(a))
)

# Rename to match GraphSentry schema
transactions.rename(columns={
    "TX_ID"               : "transaction_id",
    "SENDER_ACCOUNT_ID"   : "sender_account_id",
    "RECEIVER_ACCOUNT_ID" : "receiver_account_id",
    "TX_TYPE"             : "transaction_type",
    "TX_AMOUNT"           : "amount_inr",
    "TIMESTAMP"           : "timestamp",
    "IS_FRAUD"            : "is_fraud_flag",
    "ALERT_ID"            : "alert_id",
}, inplace=True)

transactions.to_csv(OUT_CSV, index=False)
print(f"  ✓ enriched_transactions.csv  →  {OUT_CSV}  ({len(transactions):,} rows)")

# ─────────────────────────────────────────────────────────────────────────────
# 7.  BUILD NEXUS GRAPH JSON  (for graph_builder.py)
# ─────────────────────────────────────────────────────────────────────────────
print("\nBuilding Nexus Graph JSON …")

nodes = []
edges = []
seen_nodes: set[str] = set()

def add_node(node_id: str, node_type: str, **props):
    if node_id not in seen_nodes:
        seen_nodes.add(node_id)
        nodes.append({"id": node_id, "type": node_type, **props})

# Account nodes (with fraud flag from accounts.csv)
acc_fraud_map = dict(zip(
    accounts["ACCOUNT_ID"].astype(str),
    accounts["IS_FRAUD"].astype(int)
))
for acc_id, is_fraud in acc_fraud_map.items():
    add_node(acc_id, "account", is_fraud=is_fraud)

# Transaction edges + Device / IP nodes
for _, row in transactions.iterrows():
    sender   = str(row["sender_account_id"])
    receiver = str(row["receiver_account_id"])
    dev_id   = str(row["device_id"])
    ip_id    = str(row["ip_address"])

    add_node(sender,   "account")
    add_node(receiver, "account")
    add_node(dev_id,   "device")
    add_node(ip_id,    "ip")

    edges.append({
        "source"           : sender,
        "target"           : receiver,
        "relation"         : "transfers_to",
        "transaction_id"   : str(row["transaction_id"]),
        "timestamp"        : str(row["timestamp"]),
        "amount_inr"       : float(row["amount_inr"]),
        "transaction_type" : str(row["transaction_type"]),
        "channel"          : str(row["channel"]),
        "is_fraud_flag"    : int(row["is_fraud_flag"]),
        "alert_id"         : str(row.get("alert_id", "")),
    })
    edges.append({"source": sender, "target": dev_id, "relation": "uses_device"})
    edges.append({"source": sender, "target": ip_id,  "relation": "accesses_from_ip"})

with open(OUT_JSON, "w") as f:
    json.dump({"nodes": nodes, "edges": edges}, f, indent=2)

print(f"  ✓ nexus_graph_output.json   →  {OUT_JSON}")
print(f"     nodes : {len(nodes):,}   edges : {len(edges):,}")

# ─────────────────────────────────────────────────────────────────────────────
# 8.  MERGE EVERYTHING INTO SINGLE CSV  (graphsentry_dataset.csv)
# ─────────────────────────────────────────────────────────────────────────────
print("\nBuilding final merged dataset …")

df = pd.read_csv(OUT_CSV)

# Sender account metadata
sender_meta = accounts[[
    "ACCOUNT_ID", "CUSTOMER_ID", "COUNTRY",
    "ACCOUNT_TYPE", "INIT_BALANCE", "TX_BEHAVIOR_ID"
]].rename(columns={
    "ACCOUNT_ID"    : "sender_account_id",
    "CUSTOMER_ID"   : "sender_customer_id",
    "COUNTRY"       : "sender_country",
    "ACCOUNT_TYPE"  : "sender_account_type",
    "INIT_BALANCE"  : "sender_init_balance",
    "TX_BEHAVIOR_ID": "sender_tx_behavior_id",
})
df = df.merge(sender_meta, on="sender_account_id", how="left")

# Receiver account metadata
receiver_meta = accounts[[
    "ACCOUNT_ID", "COUNTRY", "ACCOUNT_TYPE"
]].rename(columns={
    "ACCOUNT_ID"  : "receiver_account_id",
    "COUNTRY"     : "receiver_country",
    "ACCOUNT_TYPE": "receiver_account_type",
})
df = df.merge(receiver_meta, on="receiver_account_id", how="left")

# Alert type
alert_meta = alerts[["ALERT_ID", "ALERT_TYPE"]].drop_duplicates("ALERT_ID").rename(
    columns={"ALERT_ID": "alert_id"}
)
df = df.merge(alert_meta, on="alert_id", how="left")

# Final column order
final_cols = [
    "transaction_id", "timestamp",
    "sender_account_id", "sender_customer_id", "sender_country",
    "sender_account_type", "sender_init_balance", "sender_tx_behavior_id",
    "receiver_account_id", "receiver_country", "receiver_account_type",
    "transaction_type", "amount_inr",
    "channel", "device_id", "ip_address",
    "alert_id", "ALERT_TYPE", "is_fraud_flag",
]
df = df[[c for c in final_cols if c in df.columns]]

df.to_csv(OUT_FINAL, index=False)
print(f"  ✓ graphsentry_dataset.csv   →  {OUT_FINAL}  ({len(df):,} rows × {len(df.columns)} cols)")

# ─────────────────────────────────────────────────────────────────────────────
# 9.  SANITY CHECK
# ─────────────────────────────────────────────────────────────────────────────
print("\n── Enrichment Summary ──────────────────────────────────────────────")
print(transactions["channel"].value_counts().to_string())
print(f"\nFraud transactions    : {transactions['is_fraud_flag'].sum():,}")
print(f"Device IDs assigned   : {transactions['device_id'].nunique():,}")
print(f"IP addresses assigned : {transactions['ip_address'].nunique():,}")

fraud_txns       = transactions[transactions["is_fraud_flag"] == 1]
normal_txns      = transactions[transactions["is_fraud_flag"] == 0]
fraud_dev_reuse  = fraud_txns["device_id"].value_counts()
normal_dev_reuse = normal_txns["device_id"].value_counts()
print(f"\nFraud  — max accounts sharing one device : {fraud_dev_reuse.max() if len(fraud_dev_reuse) else 0}")
print(f"Normal — max accounts sharing one device : {normal_dev_reuse.max() if len(normal_dev_reuse) else 0}")
print("────────────────────────────────────────────────────────────────────")
print("\nDone. ✓")
print("\nFiles written:")
print(f"  {OUT_CSV}")
print(f"  {OUT_JSON}")
print(f"  {OUT_FINAL}")