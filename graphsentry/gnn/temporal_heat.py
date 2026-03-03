import json
from pathlib import Path
from datetime import datetime


def _to_seconds(ts) -> float:
    """
    Accept either:
    - "YYYY-MM-DD HH:MM:SS"
    - numeric (int/float)
    - numeric string
    """
    if ts is None:
        return 0.0
    if isinstance(ts, (int, float)):
        return float(ts)

    s = str(ts).strip()

    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").timestamp()
    except Exception:
        try:
            return float(s)
        except Exception:
            return 0.0


def apply_temporal_heat(graph_data: dict, window_seconds: int = 180) -> dict:
    """
    Temporal Dynamics (Week 2):
    Treat any inbound transfer to an account as a "deposit event".
    If that account sends money out within 180 seconds of receiving it,
    increase its risk score.

    Returns:
      risk_scores: dict {account_id: float}
    """
    edges = graph_data.get("edges", [])

    # We only apply this to account->account transfers if present.
    # In your current Week1 data you may not have transfers_to yet.
    transfers = [
        e for e in edges
        if str(e.get("relation", "")).lower() in {"transfers_to", "transfer", "transaction"}
    ]

    inbound = {}   # account -> list[(t_in, amount_in)]
    outbound = {}  # account -> list[(t_out, amount_out)]

    for e in transfers:
        src = str(e["source"])
        dst = str(e["target"])
        t = _to_seconds(e.get("timestamp"))
        amt = float(e.get("amount", 0.0))

        outbound.setdefault(src, []).append((t, amt))
        inbound.setdefault(dst, []).append((t, amt))

    # Sort by time
    for acc in inbound:
        inbound[acc].sort(key=lambda x: x[0])
    for acc in outbound:
        outbound[acc].sort(key=lambda x: x[0])

    risk_scores = {}

    # Score: count pass-through events within the time window
    for acc, in_events in inbound.items():
        out_events = outbound.get(acc, [])
        if not out_events:
            continue

        score = 0.0
        j = 0

        for (t_in, amt_in) in in_events:
            # Move pointer to first outbound >= inbound time
            while j < len(out_events) and out_events[j][0] < t_in:
                j += 1

            if j < len(out_events):
                t_out, amt_out = out_events[j]
                dt = t_out - t_in
                if 0 <= dt <= window_seconds:
                    score += 1.0

        if score > 0:
            risk_scores[acc] = score

    return risk_scores


def main():
    repo_root = Path(__file__).resolve().parents[2]
    graph_path = repo_root / "graphsentry" / "data" / "nexus_graph_output.json"

    with open(graph_path, "r") as f:
        graph_data = json.load(f)

    scores = apply_temporal_heat(graph_data, window_seconds=180)

    if not scores:
        print("\n⚠️ No 'transfers_to' edges found in this JSON yet.")
        print("This Week2 logic needs account→account transfers (AMLSim will provide that).")
        return

    top10 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]
    print("\n✅ Temporal Heat Risk Scores (Top 10)")
    for acc, sc in top10:
        print(f"{acc} -> {sc}")


if __name__ == "__main__":
    main()