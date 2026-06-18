"""documents.py — build PDF files from case data.

PDF is the universal output: opens in any browser, on any device, no Office
needed, identical everywhere. Each builder takes the case name, a `bundle` of
the case's data (all forms + metadata, handed over by the seam), and a path to
write to. Adding a document type = one builder + one line in TEMPLATES.

We avoid table shading colours that some viewers render as black boxes, and use
a clean bordered grid instead.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app import schemas

ACCENT = colors.HexColor("#6d28d9")     # app purple
SUBHEAD = colors.HexColor("#3b5bdb")    # section blue
GRID = colors.HexColor("#cccccc")
TINT = colors.HexColor("#f3f0fb")       # pale purple for the label column


def _rt(value) -> str:
    """User text -> safe reportlab markup, keeping line breaks; empty -> em dash."""
    return escape(str(value or "\u2014")).replace("\n", "<br/>")


def _styles() -> dict:
    s = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("LCTitle", parent=s["Title"], textColor=ACCENT,
                                alignment=TA_LEFT, fontSize=24, spaceAfter=4),
        "h1": ParagraphStyle("LCH1", parent=s["Heading1"], textColor=ACCENT, fontSize=14),
        "h2": ParagraphStyle("LCH2", parent=s["Heading2"], textColor=SUBHEAD, fontSize=12),
        "body": s["BodyText"],
    }


def _intro(story: list, st: dict, title: str, case_name: str) -> None:
    story.append(Paragraph(title, st["title"]))
    story.append(Paragraph(f"<b>Case:</b> {escape(case_name)}", st["body"]))
    story.append(Paragraph(f"Generated: {date.today().strftime('%B %d, %Y')}", st["body"]))
    story.append(Spacer(1, 14))


def _kv_table(st: dict, rows: list[tuple[str, object]]) -> Table:
    data = [[Paragraph(f"<b>{escape(label)}</b>", st["body"]), Paragraph(_rt(val), st["body"])]
            for label, val in rows]
    table = Table(data, colWidths=[2.2 * inch, 4.0 * inch])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ("BACKGROUND", (0, 0), (0, -1), TINT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _build(story: list, out_path: Path, title: str) -> Path:
    doc = SimpleDocTemplate(str(out_path), pagesize=LETTER,
                            topMargin=1 * inch, bottomMargin=1 * inch,
                            leftMargin=1 * inch, rightMargin=1 * inch, title=title)
    doc.build(story)
    return out_path


# ---- the document builders -------------------------------------------------
def build_client_intake(case_name: str, bundle: dict, out_path: Path) -> Path:
    st, story = _styles(), []
    client = bundle["client"]
    _intro(story, st, "Client Intake Summary", case_name)

    story.append(Paragraph("Client Details", st["h1"]))
    rows = [(label, client.get(key)) for key, label, kind in schemas.FIELD_SPECS["client"] if kind == "line"]
    story += [_kv_table(st, rows), Spacer(1, 14)]

    for key, label, kind in schemas.FIELD_SPECS["client"]:
        if kind != "text":
            continue
        story += [Paragraph(escape(label), st["h2"]), Paragraph(_rt(client.get(key)), st["body"]), Spacer(1, 8)]
    return _build(story, out_path, "Client Intake Summary")


def build_defendant_sheet(case_name: str, bundle: dict, out_path: Path) -> Path:
    st, story = _styles(), []
    d = bundle["defendant"]
    _intro(story, st, "Defendant Information Sheet", case_name)
    story.append(Paragraph("Defendant Details", st["h1"]))
    rows = [(label, d.get(key)) for key, label, kind in schemas.FIELD_SPECS["defendant"]]
    story.append(_kv_table(st, rows))
    return _build(story, out_path, "Defendant Information Sheet")


def build_case_summary(case_name: str, bundle: dict, out_path: Path) -> Path:
    st, story = _styles(), []
    meta, client, d = bundle["meta"], bundle["client"], bundle["defendant"]
    _intro(story, st, "Case Summary", case_name)

    story.append(Paragraph("Case", st["h1"]))
    story += [_kv_table(st, [("Status", meta.get("status")), ("Opened", meta.get("createdDate"))]), Spacer(1, 12)]

    story.append(Paragraph("Parties", st["h1"]))
    story += [_kv_table(st, [
        ("Client", client.get("name")),
        ("Client contact date", client.get("dateOfContact")),
        ("Defendant", d.get("name")),
        ("Defendant address", d.get("address")),
    ]), Spacer(1, 12)]

    story.append(Paragraph("Statement of Incident", st["h2"]))
    story.append(Paragraph(_rt(client.get("statementOfIncident")), st["body"]))
    return _build(story, out_path, "Case Summary")


# template id -> (builder, filename stem, human label for the picker)
TEMPLATES = {
    "client_intake": (build_client_intake, "client-intake-summary", "Client Intake Summary"),
    "defendant_sheet": (build_defendant_sheet, "defendant-information-sheet", "Defendant Information Sheet"),
    "case_summary": (build_case_summary, "case-summary", "Case Summary"),
}
