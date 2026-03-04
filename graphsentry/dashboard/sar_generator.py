"""
sar_generator.py — GraphSentry feature/sar-automation
Core Week-2 deliverable: generate_pmla_sar(frozen_cluster_data)
Author: Vidhu (Member 3)

Generates a PMLA-compliant Suspicious Activity Report PDF using ReportLab.
"""

import os
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


# ── Colours ───────────────────────────────────────────────────────────────────
BLACK    = colors.HexColor("#000000")
WHITE    = colors.HexColor("#FFFFFF")
GREY_100 = colors.HexColor("#F5F5F5")
GREY_300 = colors.HexColor("#D1D1D6")
GREY_500 = colors.HexColor("#8E8E93")
GREY_800 = colors.HexColor("#1C1C1E")
RED      = colors.HexColor("#FF3B30")
BLUE     = colors.HexColor("#0A84FF")


def _styles() -> dict:
    return {
        "cover_tag": ParagraphStyle("cover_tag", fontName="Helvetica-Bold",
            fontSize=7, textColor=WHITE, leading=10),
        "cover_title": ParagraphStyle("cover_title", fontName="Helvetica-Bold",
            fontSize=22, textColor=BLACK, leading=28, spaceAfter=4),
        "cover_sub": ParagraphStyle("cover_sub", fontName="Helvetica",
            fontSize=10, textColor=GREY_500, leading=15, spaceAfter=2),
        "cover_meta": ParagraphStyle("cover_meta", fontName="Helvetica",
            fontSize=8, textColor=GREY_500, leading=13),
        "section_heading": ParagraphStyle("section_heading", fontName="Helvetica-Bold",
            fontSize=8, textColor=GREY_500, leading=12, spaceBefore=16, spaceAfter=5),
        "body": ParagraphStyle("body", fontName="Helvetica",
            fontSize=9, textColor=GREY_800, leading=14, spaceAfter=4),
        "body_bold": ParagraphStyle("body_bold", fontName="Helvetica-Bold",
            fontSize=9, textColor=BLACK, leading=14, spaceAfter=4),
        "small": ParagraphStyle("small", fontName="Helvetica",
            fontSize=7.5, textColor=GREY_500, leading=11),
        "th": ParagraphStyle("th", fontName="Helvetica-Bold",
            fontSize=8, textColor=WHITE, leading=11),
        "td": ParagraphStyle("td", fontName="Helvetica",
            fontSize=8, textColor=GREY_800, leading=11),
        "td_red": ParagraphStyle("td_red", fontName="Helvetica-Bold",
            fontSize=8, textColor=RED, leading=11),
        "disclaimer": ParagraphStyle("disclaimer", fontName="Helvetica",
            fontSize=7.5, textColor=GREY_500, leading=12, alignment=TA_CENTER),
    }


def _rule():
    return HRFlowable(width="100%", thickness=0.5, color=GREY_300,
                      spaceAfter=6, spaceBefore=2)


def _section(title: str, S: dict):
    return [Paragraph(title.upper(), S["section_heading"]), _rule()]


def _kv(rows: list, S: dict, col1=45, col2=115) -> Table:
    data = [[Paragraph(k, S["small"]), Paragraph(v, S["body_bold"])] for k, v in rows]
    t = Table(data, colWidths=[col1*mm, col2*mm])
    t.setStyle(TableStyle([
        ("VALIGN",        (0,0),(-1,-1),"TOP"),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
        ("TOPPADDING",    (0,0),(-1,-1), 3),
        ("LINEBELOW",     (0,0),(-1,-1), 0.3, GREY_300),
    ]))
    return t


# ── Core deliverable ──────────────────────────────────────────────────────────
def generate_pmla_sar(frozen_cluster_data: dict, output_path: str = None) -> str:
    """
    Week-2 core deliverable function.

    Takes a frozen mule cluster dict and generates a
    PMLA-compliant Suspicious Activity Report PDF.

    Args:
        frozen_cluster_data (dict):
            cluster_id       (str)   — unique ring identifier
            detected_at      (str)   — ISO timestamp of detection
            accounts         (list)  — [{id, type, risk, label}]
            edges            (list)  — [{source, target, relation, channel, timestamp}]
            trigger_reason   (str)   — reason for freeze
            total_nodes      (int)
            high_risk_nodes  (int)
            shared_devices   (list)  — device IDs linked to 3+ accounts
            transfer_chain   (list)  — ordered account IDs in chain
            channels_used    (list)  — e.g. ["RTGS","IMPS","UPI"]
            estimated_amount (str)   — e.g. "INR 4,72,000"

    Returns:
        str: Path to the generated PDF file.
    """
    if output_path is None:
        cid = frozen_cluster_data.get("cluster_id", "UNKNOWN")
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(tempfile.gettempdir(), f"SAR_{cid}_{ts}.pdf")

    S = _styles()
    W, H = A4
    M = 20 * mm
    story = []

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=M, rightMargin=M, topMargin=M, bottomMargin=20*mm,
        title=f"SAR — {frozen_cluster_data.get('cluster_id','')}",
        author="GraphSentry Compliance Engine",
        subject="PMLA Suspicious Activity Report",
    )

    # ── Safe data extraction ──────────────────────────────────────────────────
    cluster_id       = frozen_cluster_data.get("cluster_id",       "GS-RING-UNKNOWN")
    detected_at      = frozen_cluster_data.get("detected_at",      datetime.now().isoformat())
    trigger_reason   = frozen_cluster_data.get("trigger_reason",   "Automated GNN cluster detection")
    total_nodes      = frozen_cluster_data.get("total_nodes",      0)
    high_risk_nodes  = frozen_cluster_data.get("high_risk_nodes",  0)
    estimated_amount = frozen_cluster_data.get("estimated_amount", "Undetermined")
    accounts         = frozen_cluster_data.get("accounts",         [])
    edges            = frozen_cluster_data.get("edges",            [])
    shared_devices   = frozen_cluster_data.get("shared_devices",   [])
    transfer_chain   = frozen_cluster_data.get("transfer_chain",   [])
    channels_used    = frozen_cluster_data.get("channels_used",    [])

    try:
        dt       = datetime.fromisoformat(detected_at)
        date_str = dt.strftime("%d %B %Y")
        time_str = dt.strftime("%H:%M:%S IST")
    except Exception:
        dt       = datetime.now()
        date_str = detected_at
        time_str = ""

    report_id  = f"SAR/GS/{dt.strftime('%Y%m%d')}/{cluster_id[-4:].upper()}"
    filed_date = datetime.now().strftime("%d %B %Y")
    cw         = W - 2*M   # content width

    # ══════════════════════════════════════════════════════════════════════════
    # COVER
    # ══════════════════════════════════════════════════════════════════════════

    # Black header bar
    hdr = Table([[
        Paragraph("GRAPHSENTRY  ·  COMPLIANCE ENGINE", S["cover_tag"]),
        Paragraph("CONFIDENTIAL  ·  PMLA 2002",        S["cover_tag"]),
    ]], colWidths=[cw * 0.6, cw * 0.4])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), BLACK),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(0, 0),  10),
        ("RIGHTPADDING",  (1,0),(1, 0),  10),
        ("ALIGN",         (1,0),(1, 0),  "RIGHT"),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 12*mm))

    story.append(Paragraph("Suspicious Activity Report", S["cover_title"]))
    story.append(Paragraph(
        "Prevention of Money Laundering Act, 2002  ·  Rule 2(1)(g)", S["cover_sub"]))
    story.append(Spacer(1, 5*mm))

    # Metadata row
    meta = Table([[
        Paragraph(f"Report ID<br/><b>{report_id}</b>",  S["cover_meta"]),
        Paragraph(f"Cluster ID<br/><b>{cluster_id}</b>", S["cover_meta"]),
        Paragraph(f"Detected<br/><b>{date_str}</b>",    S["cover_meta"]),
        Paragraph(f"Filed<br/><b>{filed_date}</b>",     S["cover_meta"]),
        Paragraph("Status<br/><b>FROZEN</b>",           S["cover_meta"]),
    ]], colWidths=[cw/5]*5)
    meta.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), GREY_100),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("LINEAFTER",     (0,0),(-2,-1), 0.5, GREY_300),
    ]))
    story.append(meta)
    story.append(Spacer(1, 3*mm))
    story.append(_rule())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — EXECUTIVE SUMMARY
    # ══════════════════════════════════════════════════════════════════════════
    story += _section("1.  Executive Summary", S)

    story.append(Paragraph(
        f"GraphSentry's Sentinel GNN Core identified and froze a suspected Money Mule Ring "
        f"comprising <b>{total_nodes} nodes</b> ({high_risk_nodes} flagged high-risk) "
        f"on <b>{date_str}</b> at <b>{time_str}</b>. "
        f"The ring was detected through anomalous graph topology — shared device fingerprints, "
        f"rapid fund layering, and high-velocity transfers across "
        f"{', '.join(channels_used) if channels_used else 'multiple'} channels. "
        f"Estimated exposure: <b>{estimated_amount}</b>. "
        f"All accounts in the cluster have been pre-emptively frozen pending investigation.",
        S["body"]
    ))
    story.append(Spacer(1, 3*mm))
    story.append(_kv([
        ("Trigger Reason",    trigger_reason),
        ("Channels Involved", ", ".join(channels_used) if channels_used else "N/A"),
        ("Estimated Amount",  estimated_amount),
        ("Detection Engine",  "Sentinel GNN Core  ·  RGAT + Louvain Community Detection"),
        ("Response",          "Pre-Emptive Cluster-Blocking — all accounts frozen"),
    ], S))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — SUBJECT ACCOUNTS
    # ══════════════════════════════════════════════════════════════════════════
    story += _section("2.  Subject Accounts", S)

    rows = [[
        Paragraph("Account ID", S["th"]),
        Paragraph("Type",       S["th"]),
        Paragraph("Risk",       S["th"]),
        Paragraph("Label",      S["th"]),
    ]]
    for a in accounts[:30]:
        risk = a.get("risk", "low")
        rows.append([
            Paragraph(a.get("id",    "—"), S["td"]),
            Paragraph(a.get("type",  "—"), S["td"]),
            Paragraph(risk.upper(), S["td_red"] if risk == "high" else S["td"]),
            Paragraph(a.get("label", "—"), S["td"]),
        ])
    if len(accounts) > 30:
        rows.append([Paragraph(f"... and {len(accounts)-30} more", S["small"]),
                     Paragraph("",""), Paragraph("",""), Paragraph("","")])

    t = Table(rows, colWidths=[cw*0.32, cw*0.18, cw*0.18, cw*0.32])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1, 0), BLACK),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, GREY_100]),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("GRID",          (0,0),(-1,-1), 0.3, GREY_300),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(t)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — SUSPICIOUS TRANSACTION PATTERN
    # ══════════════════════════════════════════════════════════════════════════
    story += _section("3.  Suspicious Transaction Pattern", S)

    if transfer_chain:
        story.append(Paragraph("Detected Layering Chain:", S["body_bold"]))
        story.append(Paragraph("  ->  ".join(transfer_chain), S["body"]))
        story.append(Spacer(1, 3*mm))

    if shared_devices:
        story.append(Paragraph("Shared Device Fingerprints (Mule Ring Indicator):", S["body_bold"]))
        for dev in shared_devices:
            linked = [e["source"] for e in edges if e.get("target") == dev]
            story.append(Paragraph(
                f"<b>{dev}</b> — linked to {len(linked)} accounts: "
                f"{', '.join(linked[:5])}{'...' if len(linked)>5 else ''}",
                S["body"]
            ))
        story.append(Spacer(1, 3*mm))

    if edges:
        story.append(Paragraph("Transaction Log (sample — up to 20 rows):", S["body_bold"]))
        story.append(Spacer(1, 2*mm))
        tx = [[
            Paragraph("Source",    S["th"]),
            Paragraph("Target",    S["th"]),
            Paragraph("Relation",  S["th"]),
            Paragraph("Channel",   S["th"]),
            Paragraph("Timestamp", S["th"]),
        ]]
        for e in edges[:20]:
            rel = e.get("relation", "—")
            tx.append([
                Paragraph(str(e.get("source",    "—"))[:18], S["td"]),
                Paragraph(str(e.get("target",    "—"))[:18], S["td"]),
                Paragraph(rel, S["td_red"] if rel == "transfer" else S["td"]),
                Paragraph(str(e.get("channel",   "—")),      S["td"]),
                Paragraph(str(e.get("timestamp", "—"))[:16], S["td"]),
            ])
        if len(edges) > 20:
            tx.append([Paragraph(f"... and {len(edges)-20} more", S["small"]),
                       Paragraph("",""), Paragraph("",""),
                       Paragraph("",""), Paragraph("","")])

        tt = Table(tx, colWidths=[cw*0.22, cw*0.22, cw*0.16, cw*0.14, cw*0.26])
        tt.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1, 0), BLACK),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, GREY_100]),
            ("TOPPADDING",    (0,0),(-1,-1), 4),
            ("BOTTOMPADDING", (0,0),(-1,-1), 4),
            ("LEFTPADDING",   (0,0),(-1,-1), 5),
            ("GRID",          (0,0),(-1,-1), 0.3, GREY_300),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ]))
        story.append(tt)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4 — PMLA COMPLIANCE DECLARATION
    # ══════════════════════════════════════════════════════════════════════════
    story += _section("4.  PMLA Compliance Declaration", S)

    story.append(_kv([
        ("Reporting Entity",    "Reporting Bank / Financial Institution"),
        ("Principal Officer",   "[Designated Principal Officer — to be signed]"),
        ("PMLA Section",        "Section 12 — Obligation to furnish information"),
        ("Rule Reference",      "Rule 2(1)(g) — PML (Maintenance of Records) Rules, 2005"),
        ("FIU-IND Reference",   "Filed with Financial Intelligence Unit — India"),
        ("RBI Circular",        "RBI/2014-15/627 — KYC/AML guidelines"),
        ("Generated By",        "GraphSentry Automated Compliance Engine v1.0"),
        ("Generation Time",     datetime.now().strftime("%d %B %Y  %H:%M:%S IST")),
    ], S))

    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        "This report has been automatically generated by GraphSentry's compliance engine "
        "following detection and cluster-blocking of a suspected money mule ring. "
        "The reporting institution is obligated under Section 12 of the Prevention of Money Laundering Act, 2002 "
        "to furnish this information to FIU-IND within the prescribed timeline.",
        S["body"]
    ))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 5 — AUTHORISATION
    # ══════════════════════════════════════════════════════════════════════════
    story += _section("5.  Authorisation", S)

    sig = Table([[
        Paragraph("Principal Officer\n\n\n\n___________________________\nSignature &amp; Stamp", S["body"]),
        Paragraph("Compliance Head\n\n\n\n___________________________\nSignature &amp; Stamp",  S["body"]),
        Paragraph("Date of Filing\n\n\n\n___________________________\nDD / MM / YYYY",          S["body"]),
    ]], colWidths=[cw/3]*3)
    sig.setStyle(TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("LINEAFTER",     (0,0),(-2,-1), 0.5, GREY_300),
        ("BACKGROUND",    (0,0),(-1,-1), GREY_100),
    ]))
    story.append(sig)
    story.append(Spacer(1, 8*mm))
    story.append(_rule())
    story.append(Paragraph(
        "CONFIDENTIAL — This document contains sensitive financial intelligence intended solely for "
        "the designated compliance officer and FIU-IND. Unauthorised disclosure is an offence under "
        "the Prevention of Money Laundering Act, 2002. Generated by GraphSentry v1.0.",
        S["disclaimer"]
    ))

    doc.build(story)
    return output_path
    