#!/usr/bin/env python3
"""
smartpack_generator.py

Unified file that generates two types of PDFs:
- PDF for companies (company)
- PDF for people (person)

Main functions:
- generate_pdf_company(content, output_pdf): Generates company PDF
- generate_pdf_person(content, output_pdf): Generates person PDF

Requirements:
    pip install reportlab
"""

from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    ListFlowable, ListItem, PageBreak
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from datetime import datetime


# ============================================================================
# STYLES AND CONSTANTS FOR COMPANY PDF
# ============================================================================

def _get_company_styles():
    """Returns the styles for company PDF."""
    base = getSampleStyleSheet()

    return {
        "company_title": ParagraphStyle(
            "company_title", parent=base["Heading1"],
            fontName="Helvetica-Bold", fontSize=14, leading=16,
            alignment=TA_LEFT, spaceAfter=6
        ),
        "section_title": ParagraphStyle(
            "section_title", parent=base["Heading2"],
            fontName="Helvetica-Bold", fontSize=12, leading=14, spaceAfter=6
        ),
        "table_header": ParagraphStyle(
            "table_header", parent=base["BodyText"],
            fontName="Helvetica-Bold", fontSize=10, leading=12,
            textColor=colors.white
        ),
        "table_cell": ParagraphStyle(
            "table_cell", parent=base["BodyText"],
            fontName="Helvetica", fontSize=9, leading=12
        ),
        "kv_key_bold": ParagraphStyle(
            "kv_key_bold", parent=base["BodyText"],
            fontName="Helvetica-Bold", fontSize=9, leading=12
        ),
        "news_title_bold": ParagraphStyle(
            "news_title_bold", parent=base["BodyText"],
            fontName="Helvetica-Bold", fontSize=9, leading=11
        ),
        "normal": ParagraphStyle(
            "normal", parent=base["BodyText"],
            fontName="Helvetica", fontSize=10, leading=13, spaceAfter=6
        ),
        "small": ParagraphStyle(
            "small", parent=base["BodyText"],
            fontName="Helvetica", fontSize=9, leading=11, spaceAfter=4
        ),
    }


def _get_company_page_config():
    """Returns the page configuration for company PDF."""
    PAGE_SIZE = A4
    PAGE_WIDTH, PAGE_HEIGHT = PAGE_SIZE
    LEFT_MARGIN = RIGHT_MARGIN = 18 * mm
    TOP_MARGIN = BOTTOM_MARGIN = 18 * mm
    AVAILABLE_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
    BLUE_BG = colors.HexColor("#eef6ff")

    return {
        "PAGE_SIZE": PAGE_SIZE,
        "PAGE_WIDTH": PAGE_WIDTH,
        "PAGE_HEIGHT": PAGE_HEIGHT,
        "LEFT_MARGIN": LEFT_MARGIN,
        "RIGHT_MARGIN": RIGHT_MARGIN,
        "TOP_MARGIN": TOP_MARGIN,
        "BOTTOM_MARGIN": BOTTOM_MARGIN,
        "AVAILABLE_WIDTH": AVAILABLE_WIDTH,
        "BLUE_BG": BLUE_BG
    }


# ============================================================================
# HELPER FUNCTIONS FOR COMPANY PDF
# ============================================================================

def _make_first_table_company(headers, left_entries, right_entries,
                               available_width, styles, header_bg):
    """Creates the first table for company PDF."""
    left_w = available_width * 0.5
    right_w = available_width * 0.5
    data = []
    data.append([
        Paragraph(headers[0], styles["table_header"]),
        Paragraph(headers[1], styles["table_header"])
    ])

    max_rows = max(len(left_entries), len(right_entries))
    for i in range(max_rows):
        if i < len(left_entries):
            k, v = left_entries[i]
            left_html = f"<b>{k}:</b> {v}"
            left_cell = Paragraph(left_html.replace("\n", "<br/>"), styles["table_cell"])
        else:
            left_cell = Paragraph("", styles["table_cell"])

        if i < len(right_entries):
            rk, rv = right_entries[i]
            right_html = f"<b>{rk}:</b> {rv}"
            right_cell = Paragraph(right_html.replace("\n", "<br/>"), styles["table_cell"])
        else:
            right_cell = Paragraph("", styles["table_cell"])

        data.append([left_cell, right_cell])

    tbl = Table(data, colWidths=[left_w, right_w], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#444444")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#002e5d")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tbl


def _make_kv_table_no_header_company(pairs, available_width, styles, left_ratio=0.30):
    """Creates a key-value table without header for company PDF."""
    left_w = available_width * left_ratio
    right_w = available_width - left_w
    data = []

    for left, right in pairs:
        left_cell = Paragraph(f"<b>{left}</b>", styles["table_cell"])
        right_val = right if (right and str(right).strip()) else f"Reference to {left} data"

        # Process text to apply indentation to bullet lines
        right_text = str(right_val)
        if "•" in right_text:
            lines = right_text.split("\n")
            processed_lines = []
            for line in lines:
                line_stripped = line.strip()
                if line_stripped.startswith("•"):
                    # Apply indentation to bullet lines using HTML spaces
                    processed_lines.append(f'&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{line_stripped}')
                else:
                    # No indentation for first paragraph or lines without bullets
                    processed_lines.append(line_stripped)
            right_text = "<br/>".join(processed_lines)
        else:
            right_text = right_text.replace("\n", "<br/>")

        right_cell = Paragraph(right_text, styles["table_cell"])
        data.append([left_cell, right_cell])

    tbl = Table(data, colWidths=[left_w, right_w], repeatRows=0)
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#444444")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tbl


def _make_news_table_company(header_text, news_items, available_width,
                              styles, left_ratio=0.28):
    """Creates a news table for company PDF."""
    left_w = available_width * left_ratio
    right_w = available_width - left_w
    combined = "<br/><br/>".join([f"<b>{t}</b><br/>{d}" for t, d in news_items])
    data = [[
        Paragraph(f"<b>{header_text}</b>", styles["table_cell"]),
        Paragraph(combined, styles["table_cell"])
    ]]

    tbl = Table(data, colWidths=[left_w, right_w], repeatRows=0)
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#444444")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tbl


def _make_leadership_table_company(rows, available_width, styles, left_ratio=0.22):
    """Creates a leadership table for company PDF."""
    left_w = available_width * left_ratio
    right_w = available_width - left_w
    data = []

    # Add headers
    data.append([
        Paragraph("Name", styles["table_header"]),
        Paragraph("Title", styles["table_header"])
    ])

    for name, (title, desc) in rows:
        left_cell = Paragraph(f"<b>{name}</b>", styles["table_cell"])
        right_html = f"<b>{title}</b><br/>{desc}"
        right_cell = Paragraph(right_html.replace("\n", "<br/>"), styles["table_cell"])
        data.append([left_cell, right_cell])

    tbl = Table(data, colWidths=[left_w, right_w], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#444444")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#002e5d")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tbl


def _make_generic_table_company(headers, rows, available_width, styles,
                                 column_ratios=None):
    """Creates a generic table for company PDF."""
    n = len(headers)
    if column_ratios and len(column_ratios) == n:
        col_widths_abs = [available_width * r for r in column_ratios]
    else:
        col_widths_abs = [available_width / n] * n

    data = [[Paragraph(h, styles["table_header"]) for h in headers]]
    for r in rows:
        row = [str(c) if c is not None else "" for c in r] + [""] * (n - len(r))
        data.append([
            Paragraph(cell.replace("\n", "<br/>"), styles["table_cell"])
            for cell in row[:n]
        ])

    tbl = Table(data, colWidths=col_widths_abs, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#333333")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#002e5d")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tbl


def _draw_header_company(canvas, doc, company_name, page_config):
    """Draws the header on each page of the company PDF."""
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 11)
    x = page_config["LEFT_MARGIN"]
    y = page_config["PAGE_HEIGHT"] - page_config["TOP_MARGIN"] + 6
    canvas.drawString(x, y, company_name)
    canvas.restoreState()


# ============================================================================
# STYLES AND CONSTANTS FOR PERSON PDF
# ============================================================================

def _get_person_styles():
    """Returns the styles for person PDF."""
    base_styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "title", parent=base_styles["Heading1"],
            fontName="Helvetica-Bold", fontSize=14, leading=16, spaceAfter=6
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base_styles["Heading2"],
            fontName="Helvetica-Bold", fontSize=12, leading=14, spaceAfter=6
        ),
        "normal": ParagraphStyle(
            "normal", parent=base_styles["BodyText"],
            fontName="Helvetica", fontSize=10, leading=13, spaceAfter=6
        ),
        "small": ParagraphStyle(
            "small", parent=base_styles["BodyText"],
            fontName="Helvetica", fontSize=9, leading=11, spaceAfter=4
        ),
        "table_header": ParagraphStyle(
            "table_header", parent=base_styles["BodyText"],
            fontName="Helvetica-Bold", fontSize=10, leading=12, alignment=TA_LEFT,
            textColor=colors.white
        ),
        "table_cell": ParagraphStyle(
            "table_cell", parent=base_styles["BodyText"],
            fontName="Helvetica", fontSize=9, leading=12, alignment=TA_LEFT
        ),
        "panel_text": ParagraphStyle(
            "panel_text", parent=base_styles["BodyText"],
            fontName="Helvetica", fontSize=9, leading=12, alignment=TA_LEFT,
            spaceAfter=4
        ),
        "panel_title": ParagraphStyle(
            "panel_title", parent=base_styles["BodyText"],
            fontName="Helvetica-Bold", fontSize=10, leading=12,
            alignment=TA_LEFT, spaceAfter=6
        ),
        "subsection_header": ParagraphStyle(
            "subsection_header", parent=base_styles["BodyText"],
            fontName="Helvetica-Bold", fontSize=9, leading=11, alignment=TA_LEFT,
            spaceBefore=4, spaceAfter=6
        ),
        "highlighted_subtitle": ParagraphStyle(
            "highlighted_subtitle", parent=base_styles["Heading3"],
            fontName="Helvetica-Bold", fontSize=10, leading=12, alignment=TA_LEFT,
            spaceBefore=4, spaceAfter=6
        ),
        "footnote": ParagraphStyle(
            "footnote", parent=base_styles["BodyText"],
            fontName="Helvetica-Oblique", fontSize=8, leading=10, spaceAfter=6
        )
    }


def _get_person_page_config():
    """Returns the page configuration for person PDF."""
    PAGE_SIZE = A4
    PAGE_WIDTH, PAGE_HEIGHT = PAGE_SIZE
    MARGINS = {"left": 18 * mm, "right": 18 * mm, "top": 18 * mm, "bottom": 18 * mm}
    AVAILABLE_WIDTH = PAGE_WIDTH - MARGINS["left"] - MARGINS["right"]

    return {
        "PAGE_SIZE": PAGE_SIZE,
        "PAGE_WIDTH": PAGE_WIDTH,
        "PAGE_HEIGHT": PAGE_HEIGHT,
        "MARGINS": MARGINS,
        "AVAILABLE_WIDTH": AVAILABLE_WIDTH
    }


# ============================================================================
# HELPER FUNCTIONS FOR PERSON PDF
# ============================================================================

def _make_wrapped_table_person(header, rows, available_width, styles,
                                col_widths=None, header_style="table_header",
                                cell_style="table_cell"):
    """Creates a table with wrapped text for person PDF."""
    n = len(header)
    if col_widths is None:
        if n == 5:
            ratios = [0.22, 0.18, 0.18, 0.22, 0.20]
            col_widths = [available_width * r for r in ratios]
        else:
            col_widths = [available_width / n] * n

    data = []
    data.append([Paragraph(str(h), styles[header_style]) for h in header])
    for row in rows:
        r = list(row) + [""] * (n - len(row))
        data.append([
            Paragraph(str(c).replace("\n", "<br/>"), styles[cell_style])
            for c in r
        ])

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#444444")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#002e5d")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tbl


def _panel_box_person(title_paragraph, body_paragraphs, styles,
                      width, padding=8):
    """Creates a panel with border for person PDF."""
    body_text = ""
    for bp in body_paragraphs:
        # Add bullet point symbol to each item
        bullet_text = "• " + str(bp).replace("\n", "<br/>")
        body_text += bullet_text + "<br/>"

    tcell_title = Paragraph(title_paragraph, styles["panel_title"]) \
                  if isinstance(title_paragraph, str) else title_paragraph
    tcell_body = Paragraph(body_text, styles["panel_text"])
    tbl = Table([[tcell_title], [tcell_body]], colWidths=[width])
    tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.45, colors.HexColor("#444444")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
    ]))
    return tbl


def _make_bio_table_person(title, subtitle, bio_bullets, available_width, styles):
    """Creates a bio table with name/title header and bio bullets content."""
    # Create header with title and subtitle on separate lines
    header_text = f"{title}<br/>{subtitle}"
    header_cell = Paragraph(header_text, styles["table_header"])

    # Create bio bullets content
    bio_text = ""
    for bullet in bio_bullets:
        bio_text += "• " + str(bullet).replace("\n", "<br/>") + "<br/>"
    bio_cell = Paragraph(bio_text, styles["table_cell"])

    # Create table with 2 rows, 1 column
    data = [[header_cell], [bio_cell]]
    tbl = Table(data, colWidths=[available_width])
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#444444")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#002e5d")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tbl


def _make_recent_assignments_table_person(rma_data, available_width, styles):
    """Creates a Recent/Marquee Assignments table with header and subsections."""
    # Header row
    header_cell = Paragraph(rma_data["title"], styles["table_header"])
    data = [[header_cell]]

    # Completed - Search section
    search_text = "<b>Completed - Search:</b><br/>"
    for item in rma_data["search_completed"]:
        search_text += "• " + str(item).replace("\n", "<br/>") + "<br/>"
    data.append([Paragraph(search_text, styles["table_cell"])])

    # Pure Consulting (Completed) section
    consulting_text = "<b>Pure Consulting (Completed):</b><br/>"
    for item in rma_data["pure_consulting_completed"]:
        consulting_text += "• " + str(item).replace("\n", "<br/>") + "<br/>"
    data.append([Paragraph(consulting_text, styles["table_cell"])])

    # Open Assignments section
    open_text = "<b>Open Assignments:</b><br/>"
    for k, v in rma_data["open_assignments"].items():
        open_text += f"<b>{k}:</b><br/>"
        if not v or (len(v) == 1 and v[0].lower() == "none"):
            open_text += "• None<br/>"
        else:
            for item in v:
                open_text += "• " + str(item).replace("\n", "<br/>") + "<br/>"
    data.append([Paragraph(open_text, styles["table_cell"])])

    # Create table
    tbl = Table(data, colWidths=[available_width])
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#444444")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#002e5d")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tbl


def _make_firm_relationships_table_person(title, summary_lines, available_width, styles):
    """Creates Firm Relationships table with header and bullets as second row."""
    # Header row
    header_cell = Paragraph(title, styles["table_header"])

    # Bullets row
    bullets_text = ""
    for line in summary_lines:
        bullets_text += "• " + str(line).replace("\n", "<br/>") + "<br/>"
    bullets_cell = Paragraph(bullets_text, styles["table_cell"])

    # Create table with 2 rows, 1 column
    data = [[header_cell], [bullets_cell]]
    tbl = Table(data, colWidths=[available_width])
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#444444")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#002e5d")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tbl


def _make_current_board_table_person(cb_data, available_width, styles):
    """Creates Current Board table with all subsections in a single 1-column table."""
    data = []

    # Header row with title
    header_cell = Paragraph(cb_data["title"], styles["table_header"])
    data.append([header_cell])

    # Board / Leadership Team Analysis subsection
    blt_title = cb_data["board_leadership_team_analysis"]["title"]
    blt_content = "<b>" + blt_title + "</b><br/>"

    # Add table headers and rows as text
    headers = cb_data["board_leadership_team_analysis"]["headers"]
    blt_content += " | ".join(headers) + "<br/>"

    for row in cb_data["board_leadership_team_analysis"]["rows"]:
        row_values = [str(v) if v else "N/A" for v in (row if isinstance(row, (list, tuple)) else [row])]
        blt_content += " | ".join(row_values) + "<br/>"

    if cb_data["board_leadership_team_analysis"].get("footnote"):
        blt_content += "<i>" + cb_data["board_leadership_team_analysis"]["footnote"] + "</i><br/>"

    data.append([Paragraph(blt_content, styles["table_cell"])])

    # Most Recent Executive Hires subsection
    mreh_title = cb_data["most_recent_executive_hires"]["title"]
    mreh_content = "<b>" + mreh_title + "</b><br/>"
    for item in cb_data["most_recent_executive_hires"]["items"]:
        mreh_content += "• " + str(item).replace("\n", "<br/>") + "<br/>"
    data.append([Paragraph(mreh_content, styles["table_cell"])])

    # Recent Company News subsection
    rcn_title = cb_data["recent_company_news"]["title"]
    rcn_content = "<b>" + rcn_title + "</b><br/>"
    for item in cb_data["recent_company_news"]["items"]:
        rcn_content += "• " + str(item).replace("\n", "<br/>") + "<br/>"
    data.append([Paragraph(rcn_content, styles["table_cell"])])

    # Potential Topics / Conversation Starters subsection
    pt_title = cb_data["potential_conversation_topics"]["title"]
    pt_content = "<b>" + pt_title + "</b><br/>"
    for item in cb_data["potential_conversation_topics"]["items"]:
        pt_content += "• " + str(item).replace("\n", "<br/>") + "<br/>"
    data.append([Paragraph(pt_content, styles["table_cell"])])

    # Create table
    tbl = Table(data, colWidths=[available_width])
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#444444")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#002e5d")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tbl


def _draw_header_person(canvas, doc, person_name, generation_date, page_config):
    """Draws the header on each page of the person PDF."""
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 11)

    # Left side: person name
    x_left = page_config["MARGINS"]["left"]
    y = page_config["PAGE_HEIGHT"] - page_config["MARGINS"]["top"] + 6
    canvas.drawString(x_left, y, person_name)

    # Right side: generation date
    x_right = page_config["PAGE_WIDTH"] - page_config["MARGINS"]["right"]
    canvas.drawRightString(x_right, y, generation_date)

    canvas.restoreState()


# ============================================================================
# MAIN FUNCTION: GENERATE COMPANY PDF
# ============================================================================

def generate_pdf_company(content, output_pdf):
    """
    Generates a company PDF based on the provided content.

    Args:
        content (dict): Dictionary with all company information
        output_pdf (str or Path): Path to the output PDF file

    Example of content structure:
        {
            "company": "Nombre de la empresa",
            "first_table": {
                "headers": [...],
                "left_entries": [...],
                "right_entries": [...]
            },
            "about_investment": [...],
            "indicative_portfolio": [...],
            "news": {...},
            "leadership_team": {...},
            "board_directors": {...},
            "sustainability": {...},
            "assignments_rra": {...}
        }
    """
    # Get configurations
    styles = _get_company_styles()
    page_config = _get_company_page_config()

    # Create story
    story = []
    story.append(Spacer(1, 18))
    story.append(Paragraph(content["company"], styles["company_title"]))

    # First table
    story.append(_make_first_table_company(
        content["first_table"]["headers"],
        content["first_table"]["left_entries"],
        content["first_table"]["right_entries"],
        page_config["AVAILABLE_WIDTH"],
        styles,
        page_config["BLUE_BG"]
    ))
    story.append(Spacer(1, 10))

    # About investment
    story.append(_make_kv_table_no_header_company(
        content["about_investment"],
        page_config["AVAILABLE_WIDTH"],
        styles,
        left_ratio=0.30
    ))
    story.append(Spacer(1, 10))

    # Indicative portfolio
    story.append(_make_kv_table_no_header_company(
        content["indicative_portfolio"],
        page_config["AVAILABLE_WIDTH"],
        styles,
        left_ratio=0.30
    ))
    story.append(Spacer(1, 10))

    # News
    story.append(_make_news_table_company(
        content["news"]["header"],
        content["news"]["items"],
        page_config["AVAILABLE_WIDTH"],
        styles,
        left_ratio=0.30
    ))
    story.append(Spacer(1, 10))

    # Leadership team
    story.append(Paragraph(content["leadership_team"]["title"],
                          styles["section_title"]))
    story.append(_make_leadership_table_company(
        content["leadership_team"]["rows"],
        page_config["AVAILABLE_WIDTH"],
        styles,
        left_ratio=0.22
    ))
    story.append(Spacer(1, 10))

    # Board of directors
    story.append(Paragraph(content["board_directors"]["title"],
                          styles["section_title"]))
    story.append(_make_generic_table_company(
        content["board_directors"]["headers"],
        content["board_directors"]["rows"],
        page_config["AVAILABLE_WIDTH"],
        styles,
        column_ratios=[0.5, 0.5]
    ))
    story.append(Spacer(1, 10))

    # Sustainability
    story.append(Paragraph(content["sustainability"]["title"],
                          styles["section_title"]))
    for subsection in content["sustainability"]["subsections"]:
        story.append(Paragraph(subsection["subtitle"], styles["kv_key_bold"]))
        story.append(Paragraph(subsection["content"], styles["normal"]))
    story.append(Spacer(1, 10))

    # Firm Assignment History
    story.append(Paragraph(content["assignments_rra"]["title"],
                          styles["section_title"]))
    story.append(_make_kv_table_no_header_company(
        content["assignments_rra"]["data"],
        page_config["AVAILABLE_WIDTH"],
        styles,
        left_ratio=0.50
    ))

    # Function to draw header
    def on_page(canvas, doc):
        _draw_header_company(canvas, doc, content["company"], page_config)

    # Generate PDF
    doc = SimpleDocTemplate(
        str(output_pdf),
        pagesize=page_config["PAGE_SIZE"],
        leftMargin=page_config["LEFT_MARGIN"],
        rightMargin=page_config["RIGHT_MARGIN"],
        topMargin=page_config["TOP_MARGIN"],
        bottomMargin=page_config["BOTTOM_MARGIN"]
    )
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)

    print(f"Company PDF generated: {Path(output_pdf).resolve()}")


# ============================================================================
# MAIN FUNCTION: GENERATE PERSON PDF
# ============================================================================

def generate_pdf_person(content, output_pdf):
    """
    Generates a person PDF based on the provided content.

    Args:
        content (dict): Dictionary with all person information
        output_pdf (str or Path): Path to the output PDF file

    Example of content structure:
        {
            "title": "Full Name",
            "subtitle": "Position title",
            "bio_bullets": [...],
            "ra_assignments_revenue": {...},
            "rra_relationships": {...},
            "recent_marquee_assignments": {...},
            "current_board_back": {...},
            "executive_directors": {...},
            "supervisory_directors": {...}
        }
    """
    # Get configurations
    styles = _get_person_styles()
    page_config = _get_person_page_config()

    # Get generation date
    generation_date = datetime.now().strftime("%m/%d/%Y")

    # Create story
    story = []

    # Bio bullets table (includes title and subtitle in header)
    story.append(_make_bio_table_person(
        content["title"],
        content["subtitle"],
        content["bio_bullets"],
        page_config["AVAILABLE_WIDTH"],
        styles
    ))
    story.append(Spacer(1, 10))

    # RA # of Assignments/Revenue
    story.append(Paragraph(content["ra_assignments_revenue"]["title"],
                          styles["subtitle"]))
    story.append(_make_wrapped_table_person(
        content["ra_assignments_revenue"]["header"],
        content["ra_assignments_revenue"]["rows"],
        page_config["AVAILABLE_WIDTH"],
        styles
    ))
    story.append(Spacer(1, 10))

    # Firm Relationships - table format
    rra = content["rra_relationships"]
    rra_table = _make_firm_relationships_table_person(
        rra["title"],
        rra["summary_lines"],
        page_config["AVAILABLE_WIDTH"],
        styles
    )
    story.append(rra_table)
    story.append(Spacer(1, 8))

    # Recent / Marquee Assignments table
    story.append(_make_recent_assignments_table_person(
        content["recent_marquee_assignments"],
        page_config["AVAILABLE_WIDTH"],
        styles
    ))
    story.append(Spacer(1, 10))

    # Current Board - single 1-column table with all subsections
    cb = content["current_board_back"]
    cb_table = _make_current_board_table_person(
        cb,
        page_config["AVAILABLE_WIDTH"],
        styles
    )
    story.append(cb_table)
    story.append(Spacer(1, 10))

    # Executive / Supervisory Directors tables
    story.append(Paragraph("Current Board — Executive Directors",
                          styles["subtitle"]))
    story.append(_make_wrapped_table_person(
        content["executive_directors"]["header"],
        content["executive_directors"]["rows"],
        page_config["AVAILABLE_WIDTH"],
        styles
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Current Board — Supervisory Directors",
                          styles["subtitle"]))
    story.append(_make_wrapped_table_person(
        content["supervisory_directors"]["header"],
        content["supervisory_directors"]["rows"],
        page_config["AVAILABLE_WIDTH"],
        styles
    ))
    story.append(Spacer(1, 12))

    # Function to draw header
    def on_page(canvas, doc):
        _draw_header_person(canvas, doc, content["title"], generation_date, page_config)

    # Generate PDF
    doc = SimpleDocTemplate(
        str(output_pdf),
        pagesize=page_config["PAGE_SIZE"],
        leftMargin=page_config["MARGINS"]["left"],
        rightMargin=page_config["MARGINS"]["right"],
        topMargin=page_config["MARGINS"]["top"],
        bottomMargin=page_config["MARGINS"]["bottom"]
    )
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)

    print(f"Person PDF generated: {Path(output_pdf).resolve()}")


# ============================================================================
# USAGE EXAMPLE (OPTIONAL)
# ============================================================================

if __name__ == "__main__":
    print("This module exposes two functions:")
    content = {
        "company": "[Sample Company Name]",
        "first_table": {
            "headers": ["Key Information", "Financial snapshot (Source: CapIQ / Annual Report, etc.)"],
            "left_entries": [
                ("Entity Type", "Public Company"),
                ("No of Employees", "~[employee_count]"),
                ("Industry", "Investment Fund"),
                ("Year Founded", "[year_founded]"),
                ("Active Portfolio", "[portfolio_count]")
            ],
            "right_entries": [
                ("AUM", "US$[aum_value] billion"),
                ("Headquarter", "[street_address]\n[city], [state] [zip]\n[country]"),
                ("Dry Powder", "US$[dry_powder_value] billion"),
                ("Website", "www.[company_domain].com")
            ]
        },
        "about_investment": [
            ("About the company",
            "Founded in [year_founded], [Sample Company Name] is a private equity firm based in [city], [country]. The firm prefers to invest in b2b, b2c, energy, financial services, semiconductors, infrastructure, healthcare, industrials, software, information technology, media, telecommunications, materials, resources, SaaS, manufacturing, life sciences, oncology, cybersecurity, internet of things, and technology sectors. This firm is a Registered Investment Adviser (RIA)."),
            ("Investment Strategy",
            """[Sample Company Name] is a leading global investment firm. The investment strategy is generally characterized by a few key pillars:
        • Private Equity Focus: The firm is best known for its private equity investments, often acquiring controlling stakes in companies with the aim of driving operational improvements and growth. They focus on a range of industries, including healthcare, industrials, technology, consumer, and financial services.
        • Broad Asset Classes: Beyond private equity, the firm invests across multiple asset classes, such as real estate, credit, infrastructure, energy, and growth equity.
        • Global Reach, Local Expertise: The firm operates globally, with investment teams in North America, Europe, and Asia-Pacific. They leverage local expertise to identify and execute deals, as well as to add value post-investment.
        • Active Ownership Model: The firm is known for its hands-on approach, working closely with portfolio companies to drive operational improvements, strategic repositioning, and growth initiatives.
        • Long-term Value Creation: The firm seeks to create sustainable, long-term value rather than focusing solely on short-term gains. ESG considerations are increasingly integrated into their investment process.
        • Flexible Capital: The firm has the ability to deploy a variety of capital structures (equity, debt, hybrid), allowing for flexibility in deal-making.
        • Thematic Investing: The firm often invests behind long-term secular trends (e.g., digital transformation, healthcare innovation, energy transition).
        • Co-Investment and Partnerships: The firm frequently partners with other investors, including institutional clients, sovereign wealth funds, and family offices, to co-invest in deals.""")
        ],
        "indicative_portfolio": [
            ("Indicative Portfolio (Current)", "Reference to Indicative Portfolio"),
            ("Financials", "Reference to Financials"),
            ("Segmental Financials", "Reference to Segmental Financials"),
            ("Competitors", "Top competitors: [Competitor A]; [Competitor B]; [Competitor C]; [Competitor D]; etc."),
            ("Analyst Reports", "[Bank Name]_Analyst Report (reference)")
        ],
        "news": {
            "header": "News (Recent)",
            "items": [
                ("[Sample Company] forms Exclusive Strategic Partnership — [date]",
                "[Sample Company] will collaborate to develop and provide alternative investment solutions for institutional and private wealth clients across private market asset classes."),
                ("[Sample Company] Acquires [Target Company] — [date]",
                "[Sample Company] announced the signing of definitive agreements to acquire [Target Company], one of the largest businesses in its sector."),
                ("[Sample Company] Launches New Platform — [date]",
                "[Sample Company] launched a new financial services platform and entered definitive agreements to acquire an inaugural member firm."),
                ("[Sample Company] Acquires [Energy Company] — [date]",
                "[Sample Company] signed definitive agreements to acquire [Energy Company] from a consortium; management retains a minority stake."),
                ("[Sample Company] Provides $[amount]M Financing to [Group Name] — [date]",
                "[Sample Company] and [Group Name] announced a $[amount]-million financing arranged by [Sample Company] Capital Markets."),
                ("[Partner Company] and [Sample Company] Launch Public-Private Investment Solutions — [date]",
                "[Partner Company] and [Sample Company] launched two interval funds focused on credit strategies and plan to expand their strategic partnership.")
            ]
        },
        "leadership_team": {
            "title": "1. Leadership Team",
            "rows": [
                ("[Executive Name A]",
                ("Co-Founder and Co-Executive Chairman",
                "[Executive Name A] co-founded [Sample Company] and serves as its Co-Executive Chairman. Prior to this position, they served as Co-Chief Executive Officer. They are actively involved in managing the firm and serve on each of the regional Private Equity Investment Committees.")),
                ("[Executive Name B]",
                ("Co-Founder and Co-Executive Chairman",
                "[Executive Name B] co-founded [Sample Company] and serves as its Co-Executive Chairman. They have served on regional Private Equity Investment and Portfolio Management Committees and various non-profit boards.")),
                ("[Executive Name C]",
                ("Co-Chief Executive Officer",
                "[Executive Name C] joined [Sample Company] and is its Co-Chief Executive Officer. They led the firm's expansion in Asia and have held numerous leadership roles, including Co-President and Co-Chief Operating Officer.")),
                ("[Executive Name D]",
                ("Partner, Chief Legal Officer and General Counsel",
                "[Executive Name D] joined [Sample Company] and previously served as a partner with a leading law firm. They serve as the firm's General Counsel and Secretary.")),
                ("[Executive Name E]",
                ("Chief Financial Officer",
                "[Executive Name E] joined [Sample Company] and is the Chief Financial Officer. They have held roles co-leading credit and capital markets businesses.")),
                ("[Executive Name F]",
                ("Chief Operating Officer",
                "[Executive Name F] joined [Sample Company] as Chief Operating Officer, responsible for global operations, technology, enterprise risk and corporate services.")),
                ("[Executive Name G]",
                ("Chief Administrative Officer",
                "[Executive Name G] joined [Sample Company] as Chief Administrative Officer. Previously served on the firm's Board and held senior roles at a major financial institution."))
            ]
        },
        "board_directors": {
            "title": "2. Board of Directors",
            "headers": ["Name", "Title"],
            "rows": [
                ["[Director Name A]", "Co-Executive Chairman"],
                ["[Director Name B]", "Co-Executive Chairman"],
                ["[Director Name C]", "Co-Chief Executive Officer"],
                ["[Director Name D]", "Co-Chief Executive Officer"],
                ["[Director Name E]", "Independent Director"],
                ["[Director Name F]", "Independent Director"],
                ["[Director Name G]", "Independent Director"],
                ["[Director Name H]", "Independent Director"],
                ["[Director Name I]", "Independent Director"],
                ["[Director Name J]", "Independent Director"],
                ["[Director Name K]", "Independent Director"],
                ["[Director Name L]", "Independent Director"],
                ["[Director Name M]", "Independent Director"],
                ["[Director Name N]", "Independent Director"]
            ]
        },
        "sustainability": {
            "title": "3. Sustainability",
            "subsections": [
                {
                    "subtitle": "3.1. Sustainability ranking",
                    "content": "reference to resource or data for 3.1. Sustainability ranking"
                },
                {
                    "subtitle": "3.2. Sustainability Report",
                    "content": "reference to resource or data for 3.2. Sustainability Report"
                }
            ]
        },
        "assignments_rra": {
            "title": "4. Firm Assignments History",
            "data": ("Firm Assignment History – Assignments and PNBs in last 3 years", "Reference to firm assignment history data")
        }
    }
    print("  - generate_pdf_company(content, output_pdf)")
    generate_pdf_company(content, "output_pdf.pdf")
    print("  - generate_pdf_person(content, output_pdf)")
    print("\nImport this module and use the functions as needed.")
