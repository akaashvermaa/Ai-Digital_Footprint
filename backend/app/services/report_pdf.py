"""Builds a downloadable PDF report from an analysis result (ReportLab)."""
from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas import AnalyzeResponse

LEVEL_COLORS = {"Low": colors.HexColor("#16a34a"), "Medium": colors.HexColor("#d97706"),
                "High": colors.HexColor("#dc2626")}
PRIORITY_COLORS = {"urgent": "#dc2626", "important": "#d97706", "good practice": "#16a34a"}
HEADER_BG = colors.HexColor("#1e293b")
STATUS_TEXT = {"ok": "Checked", "partial": "Partly checked", "not_checked": "Not checked",
               "unavailable": "Could not check"}


def _table(rows, widths):
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def build_pdf(result: AnalyzeResponse) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title="Digital Footprint Risk Report")
    styles = getSampleStyleSheet()
    cell = ParagraphStyle("cell", parent=styles["BodyText"], fontSize=8.5, leading=10.5)
    small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=9, leading=11.5)
    h2 = styles["Heading2"]
    p = lambda text, style=cell: Paragraph(escape(str(text)), style)

    story = [
        Paragraph("Digital Footprint Risk Report", styles["Title"]),
        Paragraph(f"Generated on {datetime.now():%d %b %Y, %I:%M %p}", styles["Normal"]),
        Spacer(1, 8),
        Paragraph(
            f'<font size="16">Overall risk score: <b>{result.score}/100</b> &nbsp; '
            f'<font color="{LEVEL_COLORS[result.level].hexval()}"><b>{result.level} risk</b></font></font>',
            styles["Normal"]),
    ]

    if result.summary:
        story += [Spacer(1, 10), Paragraph("What we discovered", h2)]
        story += [Paragraph(f"&bull; {escape(line)}", small) for line in result.summary]

    story += [Spacer(1, 10), Paragraph("Score breakdown", h2)]
    rows = [["Category", "Score", "Weight", "Status"]]
    for c in result.categories:
        rows.append([c.label, f"{c.score}/100" if c.checked else "-",
                     f"{c.weight:.0%}" if c.checked else "-", STATUS_TEXT.get(c.status, c.status)])
    story.append(_table(rows, [70 * mm, 30 * mm, 30 * mm, 44 * mm]))

    working = [c for c in result.categories if c.contributions]
    if working:
        story += [Spacer(1, 6), Paragraph("How each score was built", styles["Heading3"])]
        for c in working:
            parts = "; ".join(f"{escape(x.label)} <b>+{x.points}</b>" for x in c.contributions)
            story.append(Paragraph(f"<b>{escape(c.label)}:</b> {parts}", small))

    if result.findings:
        story += [Spacer(1, 10), Paragraph("What we found in the text", h2)]
        rows = [["Severity", "Finding", "Why it is risky", "What to do"]]
        for f in result.findings:
            extra = f" (x{f.occurrences})" if f.occurrences > 1 else ""
            rows.append([f.severity.upper(),
                         p(f"{f.type}{extra}: {f.value}  [{f.confidence:.0%} sure, {f.source}]"),
                         p(f.explanation), p(f.fix)])
        story.append(_table(rows, [18 * mm, 56 * mm, 52 * mm, 48 * mm]))

    if result.breach_check_status != "not_checked":
        story += [Spacer(1, 10), Paragraph(f"Data breaches ({len(result.breaches)})", h2)]
        if result.breach_check_status == "unavailable":
            story.append(Paragraph("The breach service could not be reached, so breaches are unknown, not zero.",
                                   styles["Normal"]))
        elif not result.breaches:
            story.append(Paragraph("No known breaches found for this email.", styles["Normal"]))
        else:
            rows = [["Breach", "Year", "Data exposed"]]
            for b in result.breaches[:40]:
                rows.append([p(b.name), b.year or "-", p(", ".join(b.data_exposed))])
            story.append(_table(rows, [50 * mm, 18 * mm, 106 * mm]))
            if len(result.breaches) > 40:
                story.append(Paragraph(f"...and {len(result.breaches) - 40} more.", styles["Normal"]))

    if result.inputs.get("username"):
        story += [Spacer(1, 10), Paragraph(
            f"Accounts found ({len(result.sites_found)} of {result.sites_checked} sites checked)", h2)]
        if result.sites_found:
            rows = [["Site", "Category", "Profile URL"]]
            for s in result.sites_found:
                rows.append([s.site, s.category, p(s.url)])
            story.append(_table(rows, [35 * mm, 30 * mm, 109 * mm]))
        elif result.username_check_status == "unavailable":
            story.append(Paragraph("No site could be checked, so the result is unknown.", styles["Normal"]))
        else:
            story.append(Paragraph("Username not found on any checked site.", styles["Normal"]))
        if result.sites_unknown:
            story.append(Paragraph(f"{result.sites_unknown} sites could not be checked (blocked or timed out).",
                                   styles["Normal"]))

    story += [Spacer(1, 10), Paragraph("Recommendations", h2)]
    for i, r in enumerate(result.recommendations, 1):
        color = PRIORITY_COLORS[r.priority]
        story.append(Paragraph(f'{i}. <font color="{color}"><b>[{r.priority.upper()}]</b></font> {escape(r.text)}',
                               styles["BodyText"]))

    if result.limitations:
        story.append(KeepTogether([Spacer(1, 10), Paragraph("Limitations of this report", h2)] +
                                  [Paragraph(f"&bull; {escape(n)}", small) for n in result.limitations]))

    story += [Spacer(1, 14), Paragraph(
        "This report is generated automatically from public information and AI analysis. "
        "No data entered was stored.", ParagraphStyle("note", parent=styles["Italic"], fontSize=8))]

    doc.build(story)
    return buf.getvalue()
