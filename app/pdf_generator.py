# -*- coding: utf-8 -*-
"""
PDF Report Generator for Real Estate Document OCR & Intelligence.
Produces clean, professional, publication-ready PDF reports with Tamil font support.
Specialized EC Extracted Report matching the authoritative TNREGINET standard (10-column precision grid).
"""

import io
import os
import re
import datetime
from typing import Dict, Any, List

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


def _get_registered_fonts():
    """Register and return Unicode Tamil and English fonts."""
    font_name = 'Helvetica'
    font_bold = 'Helvetica-Bold'
    
    font_candidates = [
        (r"C:\Windows\Fonts\latha.ttf", r"C:\Windows\Fonts\lathab.ttf", "Latha", "Latha-Bold"),
        (r"C:\Windows\Fonts\vijaya.ttf", r"C:\Windows\Fonts\vijayab.ttf", "Vijaya", "Vijaya-Bold"),
    ]

    for reg_path, bold_path, f_reg, f_bld in font_candidates:
        if os.path.exists(reg_path):
            try:
                pdfmetrics.registerFont(TTFont(f_reg, reg_path))
                font_name = f_reg
                if os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont(f_bld, bold_path))
                    font_bold = f_bld
                else:
                    font_bold = f_reg
                break
            except Exception:
                continue

    return font_name, font_bold


class _NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for exact total page numbering and running headers/footers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count):
        self.saveState()
        font_name, _ = _get_registered_fonts()
        self.setFont(font_name, 8)
        self.setFillColor(colors.HexColor('#64748b'))
        
        # Header line & label
        self.setStrokeColor(colors.HexColor('#e2e8f0'))
        self.setLineWidth(0.5)
        self.line(36, 805, 559, 805)
        self.drawString(36, 810, "PlotChoice Legal OCR & Document Intelligence Report")
        self.drawRightString(559, 810, datetime.datetime.now().strftime("%d-%b-%Y %I:%M %p"))

        # Footer line & label
        self.line(36, 45, 559, 45)
        self.drawString(36, 32, "Confidential • Automatically Extracted via GPU OCR & Document Intelligence Engine")
        self.drawRightString(559, 32, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


class _ECNumberedCanvas(canvas.Canvas):
    """Clean landscape canvas for publication-style EC Extracted Reports."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_footer(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor('#64748b'))
        if self._pageNumber > 1:
            self.drawRightString(805, 18, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


from app.translator import transliterate_tamil_text


def _sanitize_text_for_pdf(text: Any, default: str = "-") -> str:
    """Sanitize and transliterate strings to ensure 100% clean, complete ASCII / Latin-1 for ReportLab."""
    if text is None:
        return default
    s = str(text).strip()
    if not s or s == "" or s.lower() in ["none", "null"]:
        return default
    if s == "-":
        return "-"
    
    # Transliterate Tamil text dynamically to English rather than deleting it
    if any('\u0b80' <= c <= '\u0bff' for c in s):
        s = transliterate_tamil_text(s)

    replacements = {
        '“': '"', '”': '"', '’': "'", '‘': "'", '`': "'", '´': "'",
        '—': ' - ', '–': ' - ', '…': '...', '\u00a0': ' ',
        '•': '*', '₹': 'Rs. ', '™': '', '®': '', '©': '(c)',
        '\u200b': '', '\u200c': '', '\u200d': '', '\ufeff': '',
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    
    # Keep Latin-1 printable characters
    s = "".join(ch for ch in s if ord(ch) <= 255)
    # Clean up empty parens
    s = re.sub(r'\(\s*\)', '', s)
    s = re.sub(r'\(\s*[.,;:\-]+\s*\)', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s if s else default


def generate_ec_extracted_report_pdf(ec_data: dict) -> bytes:
    """
    Generate authoritative, publication-ready Encumbrance Certificate Extracted Report
    in Landscape A4 with full 10-column precision table matching authoritative TNREGINET standards.
    """
    buffer = io.BytesIO()
    
    # Landscape A4 margins 28pt (width 841.89pt - 56pt = 785.89pt printable)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=28,
        rightMargin=28,
        topMargin=28,
        bottomMargin=28
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'ECTitle',
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=2
    )

    subtitle_style = ParagraphStyle(
        'ECSubtitle',
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#475569'),
        spaceAfter=5
    )

    sec_header_style = ParagraphStyle(
        'ECSecHeader',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=6,
        spaceAfter=4
    )

    sec_sub_style = ParagraphStyle(
        'ECSecSub',
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#475569'),
        spaceAfter=5
    )

    meta_label = ParagraphStyle(
        'ECMetaLabel',
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#0f172a')
    )

    meta_val = ParagraphStyle(
        'ECMetaVal',
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#1e293b')
    )

    callout_style = ParagraphStyle(
        'ECCallout',
        fontName='Helvetica',
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor('#991b1b')
    )

    flag_body = ParagraphStyle(
        'ECFlagBody',
        fontName='Helvetica',
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=3
    )

    th_style = ParagraphStyle(
        'ECTableH',
        fontName='Helvetica-Bold',
        fontSize=6.8,
        leading=8.5,
        textColor=colors.HexColor('#0f172a')
    )

    td_style = ParagraphStyle(
        'ECTableD',
        fontName='Helvetica',
        fontSize=6.8,
        leading=8.5,
        textColor=colors.HexColor('#0f172a')
    )

    td_bold = ParagraphStyle(
        'ECTableDBold',
        fontName='Helvetica-Bold',
        fontSize=6.8,
        leading=8.5,
        textColor=colors.HexColor('#0f172a')
    )

    td_note = ParagraphStyle(
        'ECTableDNote',
        fontName='Helvetica-Oblique',
        fontSize=6.0,
        leading=7.5,
        textColor=colors.HexColor('#475569')
    )

    caveat_p = ParagraphStyle(
        'ECCaveatP',
        fontName='Helvetica',
        fontSize=7.5,
        leading=11,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=5
    )

    footer_p = ParagraphStyle(
        'ECFooterP',
        fontName='Helvetica',
        fontSize=7.0,
        leading=9.5,
        textColor=colors.HexColor('#64748b'),
        spaceBefore=10
    )

    elements = []

    # ── PAGE 1: HEADER & SECTIONS 1 & 2 ──────────────────────────────────
    elements.append(Paragraph("Encumbrance Certificate — Extracted Report", title_style))
    elements.append(Paragraph("Government of Tamil Nadu, Registration Department (TNREGINET) — source document parsed field-by-field", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0f172a'), spaceAfter=6, spaceBefore=0))

    # Section 1: Property & Search Identification
    elements.append(Paragraph("1. Property & Search Identification", sec_header_style))

    # 4-column Table across 785pt
    col_w = [185, 207, 185, 208]
    prop_data = [
        [
            Paragraph("<b>Sub-Registrar Office (SRO)</b>", meta_label),
            Paragraph(_sanitize_text_for_pdf(ec_data.get("sro", "-")), meta_val),
            Paragraph("<b>Certificate Issue Date</b>", meta_label),
            Paragraph(_sanitize_text_for_pdf(ec_data.get("issue_date", "-")), meta_val),
        ],
        [
            Paragraph("<b>Village</b>", meta_label),
            Paragraph(_sanitize_text_for_pdf(ec_data.get("village", "-")), meta_val),
            Paragraph("<b>Survey Number(s) Searched</b>", meta_label),
            Paragraph(_sanitize_text_for_pdf(str(ec_data.get("survey_searched", "-"))), meta_val),
        ],
        [
            Paragraph("<b>Zone</b>", meta_label),
            Paragraph(_sanitize_text_for_pdf(ec_data.get("zone", "-")), meta_val),
            Paragraph("<b>District</b>", meta_label),
            Paragraph(_sanitize_text_for_pdf(ec_data.get("district", "-")), meta_val),
        ],
        [
            Paragraph("<b>Search Period Requested</b>", meta_label),
            Paragraph(_sanitize_text_for_pdf(ec_data.get("search_period", "-")), meta_val),
            Paragraph("<b>SRO Data Available From</b>", meta_label),
            Paragraph(_sanitize_text_for_pdf(ec_data.get("sro_available_from", "-")), meta_val),
        ],
        [
            Paragraph("<b>Form Type</b>", meta_label),
            Paragraph(_sanitize_text_for_pdf(ec_data.get("form_type", "Form 15")), meta_val),
            Paragraph("<b>Total Entries Found</b>", meta_label),
            Paragraph(_sanitize_text_for_pdf(str(ec_data.get("total_entries", "0"))), meta_val),
        ],
    ]

    prop_table = Table(prop_data, colWidths=col_w)
    prop_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(prop_table)
    elements.append(Spacer(1, 4))

    # Search window advisory note
    search_period_str = _sanitize_text_for_pdf(ec_data.get("search_period", "-"))
    is_below_30 = ec_data.get("below_30yr_standard", True)
    if is_below_30:
        callout_data = [[
            Paragraph(f"<b>Search-window note:</b> Tamil Nadu title-verification practice generally recommends a minimum 30-year EC search window. This certificate's data-available range ({search_period_str}) is shorter than that standard, so ownership history before this window is not covered by this document and should be verified through a separate, earlier-period EC or parent title deeds.", callout_style)
        ]]
        callout_table = Table(callout_data, colWidths=[785])
        callout_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fff1f2')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#fecdd3')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(callout_table)
        elements.append(Spacer(1, 6))

    # Section 2: Key Verification Flags
    elements.append(Paragraph("2. Key Verification Flags", sec_header_style))
    elements.append(Paragraph("<b>Live / unreleased mortgages (Deposit of Title Deeds) found in this window:</b>", flag_body))

    mortgage_flags = ec_data.get("mortgages_flags", [])
    if not mortgage_flags:
        mortgage_flags = ["No registered mortgage or charge instruments found in this search window."]

    for mf in mortgage_flags:
        san_mf = _sanitize_text_for_pdf(mf)
        if san_mf.startswith("[CLOSED]"):
            mf_html = san_mf.replace("[CLOSED]", "<font color='#059669'><b>[CLOSED]</b></font>")
        elif san_mf.startswith("[OPEN / UNRELEASED]"):
            mf_html = san_mf.replace("[OPEN / UNRELEASED]", "<font color='#dc2626'><b>[OPEN / UNRELEASED]</b></font>")
        else:
            mf_html = san_mf
        elements.append(Paragraph(mf_html, flag_body))

    elements.append(Spacer(1, 2))
    court_text = _sanitize_text_for_pdf(ec_data.get("court_attachments_text") or "No court attachments, decrees, or lis-pendens entries appear among the registered documents in this search window.")
    elements.append(Paragraph(court_text, flag_body))
    elements.append(Spacer(1, 2))
    lease_text = _sanitize_text_for_pdf(ec_data.get("lease_text") or "No active registered lease agreements recorded in this search window.")
    elements.append(Paragraph(lease_text, flag_body))
    elements.append(Spacer(1, 2))
    rect_text = _sanitize_text_for_pdf(ec_data.get("rectification_text") or "No rectification instruments present in this search window.")
    elements.append(Paragraph(rect_text, flag_body))

    sr_gaps_text = _sanitize_text_for_pdf(ec_data.get("sr_gaps_text") or "")
    if sr_gaps_text and "GAP DETECTED" in sr_gaps_text:
        elements.append(Spacer(1, 2))
        elements.append(Paragraph(f"<font color='#dc2626'><b>[Source Certificate Anomaly]</b></font> {sr_gaps_text}", flag_body))

    # ── PAGES 2 & 3: REGISTERED ENTRIES TABLE (10 COLUMNS) ─────────────────
    elements.append(PageBreak())

    elements.append(Paragraph("3. Registered Entries (Form 15) — Full Detail Table", sec_header_style))
    elements.append(Paragraph(f"All {ec_data.get('total_entries', 0)} entries returned for the search period {_sanitize_text_for_pdf(ec_data.get('search_period', '-'))}, SRO {_sanitize_text_for_pdf(ec_data.get('sro', '-'))}, Village {_sanitize_text_for_pdf(ec_data.get('village', '-'))}, Survey {_sanitize_text_for_pdf(ec_data.get('survey_searched', '-'))}.", sec_sub_style))

    # 10 Columns total width: 786pt
    # [Sr(22), Doc(54), Date(58), Nature(85), Execs(125), Claims(115), Cons(72), Mkt(72), PR(53), Schedule(130)]
    t_widths = [22, 54, 58, 85, 125, 115, 72, 72, 53, 130]
    
    t_rows = [[
        Paragraph("<b>Sr.</b>", th_style),
        Paragraph("<b>Doc No/Year</b>", th_style),
        Paragraph("<b>Date</b>", th_style),
        Paragraph("<b>Nature</b>", th_style),
        Paragraph("<b>Executant(s)</b>", th_style),
        Paragraph("<b>Claimant(s)</b>", th_style),
        Paragraph("<b>Consideration Value</b>", th_style),
        Paragraph("<b>Market Value</b>", th_style),
        Paragraph("<b>PR Number</b>", th_style),
        Paragraph("<b>Remarks / Schedule</b>", th_style),
    ]]

    entries = ec_data.get("transactions", [])
    if entries:
        for idx, row in enumerate(entries):
            # 1. Sr
            sr_num = row.get("sr") or (idx + 1)
            
            # 2. Doc No
            doc_no_val = _sanitize_text_for_pdf(row.get("doc_no") or "-")
            
            # 3. Date
            date_val = _sanitize_text_for_pdf(row.get("date") or "-").replace("\n", "<br/>")
            
            # 4. Nature & Note
            nature_val = _sanitize_text_for_pdf(row.get("nature") or "Conveyance").replace("\n", "<br/>")
            nature_cell = [Paragraph(nature_val, td_style)]
            note_str = _sanitize_text_for_pdf(row.get("nature_note") or "")
            if note_str and note_str != "-":
                nature_cell.append(Spacer(1, 1.5))
                nature_cell.append(Paragraph(f"<i>{note_str}</i>", td_note))

            # 5. Executants
            execs_val = _sanitize_text_for_pdf(row.get("executants") or row.get("parties") or "-").replace("\n", "<br/>")
            
            # 6. Claimants
            claims_val = _sanitize_text_for_pdf(row.get("claimants") or "-").replace("\n", "<br/>")
            
            # 7. Consideration Value (Architecture: 1-by-1 explicit mapping)
            raw_cons = row.get("consideration")
            if not raw_cons or str(raw_cons).strip() in ["-", "0", "None", "null", ""]:
                cons_norm = row.get("consideration_norm")
                if isinstance(cons_norm, dict) and cons_norm.get("amount_inr", 0) > 0:
                    raw_cons = cons_norm.get("formatted", "-")
                else:
                    raw_cons = "-"
            cons_val = _sanitize_text_for_pdf(raw_cons)

            # 8. Market Value (Architecture: 1-by-1 explicit mapping)
            raw_mkt = row.get("market_value")
            if not raw_mkt or str(raw_mkt).strip() in ["-", "0", "None", "null", ""]:
                mkt_norm = row.get("market_value_norm")
                if isinstance(mkt_norm, dict) and mkt_norm.get("amount_inr", 0) > 0:
                    raw_mkt = mkt_norm.get("formatted", "-")
                else:
                    raw_mkt = "-"
            mkt_val = _sanitize_text_for_pdf(raw_mkt)

            # 9. PR Number (Architecture: 1-by-1 explicit mapping with currency guard)
            raw_pr = str(row.get("pr_number") or "-").strip()
            if bool(re.search(r'Rs\.?|₹|\bINR\b', raw_pr, re.I)) or (bool(re.search(r'^\s*[\d,]+\s*$', raw_pr)) and '/' not in raw_pr):
                raw_pr = "-"
            pr_val = _sanitize_text_for_pdf(raw_pr)

            # 10. Remarks / Schedule Details
            sch_list = row.get("schedules", [])
            rem_str = row.get("remarks") or row.get("document_remarks") or ""
            sch_parts = []
            if rem_str and rem_str != "-":
                sch_parts.append(rem_str)
            if sch_list and isinstance(sch_list, list) and len(sch_list) > 0:
                s0 = sch_list[0]
                if s0.get("extent") and s0.get("extent") != "-": sch_parts.append(s0["extent"])
                if s0.get("survey_no") and s0.get("survey_no") != "-": sch_parts.append(f"Sy:{s0['survey_no']}")
                if s0.get("plot_no") and s0.get("plot_no") != "-": sch_parts.append(f"Plot:{s0['plot_no']}")
            sch_val = _sanitize_text_for_pdf(" | ".join(sch_parts) if sch_parts else "-")

            t_rows.append([
                Paragraph(str(sr_num), td_style),
                Paragraph(doc_no_val, td_bold),
                Paragraph(date_val, td_style),
                nature_cell,
                Paragraph(execs_val, td_style),
                Paragraph(claims_val, td_style),
                Paragraph(cons_val, td_style),
                Paragraph(mkt_val, td_style),
                Paragraph(pr_val, td_style),
                Paragraph(sch_val, td_style),
            ])

        entries_table = Table(t_rows, colWidths=t_widths, repeatRows=1)
        entries_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eef2f6')),
            ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ]))
        elements.append(entries_table)
    else:
        elements.append(Paragraph("<b>Nil Encumbrance Certificate (Form 16)</b> — No registered transactions found in the search window.", flag_body))

    # ── PAGE 4: CAVEATS ──────────────────────────────────────────────────
    elements.append(PageBreak())

    elements.append(Paragraph("4. Caveats — What This EC Does NOT Cover", sec_header_style))
    elements.append(Spacer(1, 4))

    sro_name = _sanitize_text_for_pdf(ec_data.get("sro", "-"))
    caveats = [
        f"* <b>This certificate reflects only registered documents</b> presented at the {sro_name} SRO within the stated search window. It is not proof of current, unencumbered ownership on its own.",
        "* <b>Unregistered agreements</b> (e.g. unregistered sale agreements, unregistered leases below the registration threshold, informal family arrangements) will not appear here.",
        "* <b>Court orders / decrees not yet registered with the SRO</b> - including injunctions, attachments, or succession orders pending registration - are invisible to this search.",
        "* <b>Property tax dues, utility dues, or statutory charges</b> (e.g. municipal tax arrears) are not tracked by the Registration Department and require a separate check with the local body.",
        "* <b>Physical possession disputes or adverse possession claims</b> are not recorded in registration data and require a physical inspection and local enquiry.",
        f"* <b>The search window ({search_period_str}) does not cover the full recommended 30-year history</b>; earlier encumbrances, mortgages, or litigation before this period will not surface in this document.",
        "* <b>Entries dated after the end of this search window</b> are not included - a fresh EC should be pulled through the present date to confirm no later mortgages, sales, or attachments exist."
    ]

    for c in caveats:
        elements.append(Paragraph(c, caveat_p))

    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        f"Source: Government of Tamil Nadu Registration Department, Certificate of Encumbrance on Property, SRO {sro_name}, issued {_sanitize_text_for_pdf(ec_data.get('issue_date', '-'))}.<br/>"
        "Extracted and structured for review purposes; refer to the original certificate for the authoritative record and digital signature validity.",
        footer_p
    ))

    doc.build(elements, canvasmaker=_ECNumberedCanvas)
    return buffer.getvalue()


def _prepare_ec_report_data(data: dict, fields: dict, ext: dict) -> dict:
    """Helper to extract and format EC fields for the report generator."""
    def _val(k, default=""):
        f = fields.get(k)
        if isinstance(f, dict):
            return str(f.get("raw_value") or f.get("value") or default).strip()
        elif f is not None:
            return str(f).strip()
        return default

    def _en_only(s):
        m = re.match(r'^([^\(]+)', str(s))
        return m.group(1).strip() if m else str(s).strip()

    sro = _en_only(_val("sro_office", "-"))
    issue_date = _val("certificate_date", "-")
    village = _en_only(_val("village", "-"))
    survey_searched = _val("survey_searched", "-")
    zone = _en_only(_val("zone", "-"))
    district = _en_only(_val("district", "-"))
    search_period = _val("search_period", "-")
    sro_available = _val("sro_available_from", search_period)
    
    form_type = _en_only(_val("form_type", "Form 15"))
    
    tx_list = fields.get("transactions_table", {}).get("value", [])
    if not isinstance(tx_list, list):
        tx_list = []
    total_entries = _val("total_entries", str(len(tx_list)))

    verif = ext.get("verification_flags") or fields.get("verification_flags") or {}
    mortgage_flags = verif.get("mortgages_flags") or []
    court_text = verif.get("court_attachments_text") or _val("court_attachments", f"No court attachments, decrees, or lis-pendens entries appear among the {total_entries} registered documents in this search window.")
    lease_text = verif.get("lease_text") or _val("lease_status", "No active registered lease agreements recorded in this search window.")
    rect_text = verif.get("rectification_text") or _val("rectification_deeds", "No rectification instruments present in this search window.")
    sr_gaps_text = verif.get("sr_gaps_text") or _val("sr_no_gaps", "")

    below_30yr = ext.get("below_30yr_standard") if "below_30yr_standard" in ext else fields.get("below_30yr_standard", True)
    search_years = ext.get("search_window_years") or fields.get("search_window_years", 0)

    return {
        "sro": sro,
        "issue_date": issue_date,
        "village": village,
        "survey_searched": survey_searched,
        "zone": zone,
        "district": district,
        "search_period": search_period,
        "sro_available_from": sro_available,
        "below_30yr_standard": below_30yr,
        "search_window_years": search_years,
        "form_type": form_type,
        "total_entries": total_entries,
        "mortgages_flags": mortgage_flags,
        "court_attachments_text": court_text,
        "lease_text": lease_text,
        "rectification_text": rect_text,
        "sr_gaps_text": sr_gaps_text,
        "transactions": tx_list
    }


def generate_ocr_pdf_report(data: Dict[str, Any]) -> bytes:
    """
    Generate a full-fidelity PDF report of the OCR extraction results.
    If the document is an Encumbrance Certificate (EC), routes to the specialized 10-column landscape report.
    Returns bytes of the compiled PDF.
    """
    ext = data.get("extraction", {})
    fields = ext.get("fields", {}) or data.get("fields", {})
    doc_type = data.get("doc_type") or ext.get("document_type_id")

    # Detect Encumbrance Certificate
    if doc_type == "ec" or "form_type" in fields or "encumbrance_status" in fields or "transactions_table" in fields:
        ec_data = _prepare_ec_report_data(data, fields, ext)
        return generate_ec_extracted_report_pdf(ec_data)

    # Generic report for other 9 document types (Sale Deed, Patta, Parent Deed, etc.)
    buffer = io.BytesIO()
    font_name, font_bold = _get_registered_fonts()

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName=font_bold,
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=2
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569'),
        spaceAfter=12
    )

    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName=font_bold,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1e40af'),
        spaceBefore=10,
        spaceAfter=6
    )

    meta_label_style = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName=font_bold,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )

    meta_val_style = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0f172a')
    )

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=54,
        bottomMargin=54
    )

    elements = []

    # Title & Metadata
    title_text = data.get("filename", "Document Extraction Report")
    elements.append(Paragraph(title_text, title_style))
    elements.append(Paragraph(f"Category: <b>{doc_type.upper()}</b> • Processed: {datetime.datetime.now().strftime('%d-%b-%Y %I:%M %p')}", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=10))

    # Extracted Key Fields Table
    elements.append(Paragraph("1. Extracted Key Entities & Values", section_header_style))
    
    rows = [[
        Paragraph("<b>Field Name</b>", meta_label_style),
        Paragraph("<b>Extracted Value</b>", meta_label_style),
        Paragraph("<b>Confidence</b>", meta_label_style)
    ]]

    for k, v in fields.items():
        if k in ["transactions_table", "checklist", "verification_flags", "confidence_summary"]:
            continue
        
        label_str = k.replace("_", " ").title()
        val_str = ""
        conf_str = "0.95"
        
        if isinstance(v, dict):
            val_str = str(v.get("value") or v.get("raw_value") or "-")
            conf_str = f"{v.get('confidence', 0.95):.2f}"
        else:
            val_str = str(v)
            
        rows.append([
            Paragraph(_sanitize_text_for_pdf(label_str), meta_label_style),
            Paragraph(_sanitize_text_for_pdf(val_str), meta_val_style),
            Paragraph(conf_str, meta_val_style)
        ])

    table = Table(rows, colWidths=[160, 310, 53])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')])
    ]))
    elements.append(table)
    elements.append(Spacer(1, 14))

    # Checklist Section
    checklist = ext.get("checklist") or []
    if checklist:
        elements.append(Paragraph("2. Legal Compliance & Risk Checklist", section_header_style))
        chk_rows = [[
            Paragraph("<b>Rule / Requirement</b>", meta_label_style),
            Paragraph("<b>Status</b>", meta_label_style),
            Paragraph("<b>Remarks</b>", meta_label_style)
        ]]
        for item in checklist:
            status_color = "#16a34a" if item.get("status") == "PASS" else ("#dc2626" if item.get("status") == "FAIL" else "#ea580c")
            status_html = f"<font color='{status_color}'><b>{item.get('status', 'REVIEW')}</b></font>"
            chk_rows.append([
                Paragraph(_sanitize_text_for_pdf(item.get("rule_name", "")), meta_label_style),
                Paragraph(status_html, meta_val_style),
                Paragraph(_sanitize_text_for_pdf(item.get("remarks", "")), meta_val_style)
            ])
        
        chk_table = Table(chk_rows, colWidths=[180, 70, 273])
        chk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')])
        ]))
        elements.append(chk_table)

    doc.build(elements, canvasmaker=_NumberedCanvas)
    return buffer.getvalue()
