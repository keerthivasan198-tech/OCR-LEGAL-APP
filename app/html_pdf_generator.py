import os
import io
import datetime
from typing import Dict, Any
from playwright.async_api import async_playwright

async def generate_html_pdf_report(data: Dict[str, Any]) -> bytes:
    """
    Generates a PDF using Playwright Chromium to natively support complex Tamil layout.
    """
    ext = data.get("extraction", {})
    fields = ext.get("fields", {}) or data.get("fields", {})
    doc_type = data.get("doc_type", "document")
    checklist = data.get("checklist") if "checklist" in data else ext.get("checklist", [])
    full_text = ext.get("full_text") or data.get("full_text") or data.get("raw_text") or ""
    
    # Extract transactions table if it exists
    tx_table_data = fields.get("filtered_transactions_table", fields.get("transactions_table", {})).get("value", [])
    
    now_str = datetime.datetime.now().strftime('%b %d %Y, %H:%M')
    
    # ---------------------------------------------------------
    # Build HTML String
    # ---------------------------------------------------------
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>OCR Legal Report</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Catamaran:wght@400;600;700&display=swap');
            
            body {{
                font-family: 'Catamaran', 'Nirmala UI', 'Arial Unicode MS', sans-serif;
                margin: 0;
                padding: 0;
                color: #0f172a;
                font-size: 11pt;
                line-height: 1.5;
                background: #ffffff;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 2px solid #e2e8f0;
                padding-bottom: 15px;
                margin-bottom: 20px;
            }}
            .header-title {{
                font-size: 18pt;
                font-weight: 700;
                color: #1e293b;
                margin: 0;
            }}
            .header-subtitle {{
                font-size: 10pt;
                color: #64748b;
                margin: 0;
            }}
            .section-title {{
                font-size: 14pt;
                font-weight: 700;
                color: #0f172a;
                margin-top: 30px;
                margin-bottom: 10px;
                padding-bottom: 5px;
                border-bottom: 1px solid #cbd5e1;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
                page-break-inside: auto;
            }}
            tr {{ page-break-inside: avoid; page-break-after: auto; }}
            th, td {{
                border: 1px solid #cbd5e1;
                padding: 10px;
                text-align: left;
                vertical-align: top;
            }}
            th {{
                background-color: #f1f5f9;
                font-weight: 600;
                color: #1e293b;
                font-size: 10pt;
            }}
            td {{
                font-size: 10pt;
                color: #334155;
            }}
            .conf-high {{ color: #059669; font-weight: bold; text-align: center; }}
            .conf-med {{ color: #d97706; font-weight: bold; text-align: center; }}
            .conf-low {{ color: #dc2626; font-weight: bold; text-align: center; }}
            
            .raw-text {{
                font-family: 'Catamaran', 'Nirmala UI', sans-serif;
                font-size: 9pt;
                color: #475569;
                white-space: pre-wrap;
                word-wrap: break-word;
                background-color: #f8fafc;
                padding: 15px;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
            }}
            .page-break {{
                page-break-before: always;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <h1 class="header-title">Legal Document Intelligence Report</h1>
                <p class="header-subtitle">Generated: {now_str} | Document Type: {doc_type.upper()}</p>
            </div>
        </div>
    """

    # --- 1. Key Fields Table ---
    html += '<h2 class="section-title">1. Extracted Key Legal Fields</h2>'
    html += '''
    <table>
        <thead>
            <tr>
                <th style="width: 30%;">Key Field</th>
                <th style="width: 55%;">Extracted Value</th>
                <th style="width: 15%;">Confidence</th>
            </tr>
        </thead>
        <tbody>
    '''
    for k, v in fields.items():
        if k in ["transactions_table", "filtered_transactions_table", "verification_flags", "checklist"]:
            continue
        lbl = str(v.get("label", k.replace("_", " ").title()))
        val = str(v.get("value", "Not Detected")).replace("\n", "<br>")
        conf = int(v.get("confidence", 0.95) * 100)
        
        conf_cls = "conf-high" if conf >= 90 else ("conf-med" if conf >= 70 else "conf-low")
        
        html += f'''
            <tr>
                <td><strong>{lbl}</strong></td>
                <td>{val}</td>
                <td class="{conf_cls}">{conf}%</td>
            </tr>
        '''
    html += '</tbody></table>'

    # --- 2. Verification Checklist ---
    if checklist:
        html += '<h2 class="section-title">2. Document Verification Checklist</h2>'
        html += '''
        <table>
            <thead>
                <tr>
                    <th style="width: 35%;">Verification Item</th>
                    <th style="width: 15%;">Status</th>
                    <th style="width: 50%;">Details & Findings</th>
                </tr>
            </thead>
            <tbody>
        '''
        for item in checklist:
            item_title = str(item.get("title", item.get("item", "Check")))
            
            is_valid = item.get("is_valid")
            if is_valid is True:
                status = "PASSED"
                details = "Verified successfully."
            elif is_valid is False:
                status = "FAILED"
                details = "Verification failed or data missing."
            else:
                status = str(item.get("status", "PENDING")).upper()
                details = str(item.get("detail", item.get("details", "-"))).replace("\n", "<br>")
            
            status_color = "#dc2626"
            if status in ["PASSED", "PASS", "VERIFIED"]: status_color = "#16a34a"
            elif status == "WARNING": status_color = "#ca8a04"
            elif status == "PENDING": status_color = "#64748b"
            
            html += f'''
                <tr>
                    <td><strong>{item_title}</strong></td>
                    <td style="color: {status_color}; font-weight: bold; text-align: center;">{status}</td>
                    <td>{details}</td>
                </tr>
            '''
        html += '</tbody></table>'

    # --- 3. Transactions Table ---
    if isinstance(tx_table_data, list) and len(tx_table_data) > 0:
        html += '<h2 class="section-title">3. Registered Transactions</h2>'
        html += '''
        <table>
            <thead>
                <tr>
                    <th style="width: 5%;">Sr.</th>
                    <th style="width: 15%;">Doc No</th>
                    <th style="width: 15%;">Date</th>
                    <th style="width: 20%;">Nature</th>
                    <th style="width: 20%;">Executants</th>
                    <th style="width: 25%;">Claimants</th>
                </tr>
            </thead>
            <tbody>
        '''
        for idx, row in enumerate(tx_table_data):
            sr_num = str(row.get("sr") or (idx + 1))
            doc_no = str(row.get("doc_no", "-"))
            date_val = str(row.get("date", "-"))
            nature = str(row.get("nature", "-")).replace("\n", "<br>")
            execs = str(row.get("executants") or row.get("parties") or "-").replace("\n", "<br>")
            claims = str(row.get("claimants") or "-").replace("\n", "<br>")
            
            html += f'''
                <tr>
                    <td>{sr_num}</td>
                    <td>{doc_no}</td>
                    <td>{date_val}</td>
                    <td>{nature}</td>
                    <td>{execs}</td>
                    <td>{claims}</td>
                </tr>
            '''
        html += '</tbody></table>'

    # --- 4. Raw OCR Text ---
    if full_text:
        html += '<div class="page-break"></div>'
        html += '<h2 class="section-title">4. Raw OCR Text</h2>'
        clean_text = str(full_text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        html += f'<div class="raw-text">{clean_text}</div>'

    html += """
    </body>
    </html>
    """

    # ---------------------------------------------------------
    # Render with Playwright
    # ---------------------------------------------------------
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html, wait_until="networkidle")
        
        pdf_bytes = await page.pdf(
            format="A4",
            margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"},
            print_background=True,
            display_header_footer=True,
            header_template='<div></div>',
            footer_template='<div style="font-size: 8px; margin: 0 auto; color: #94a3b8;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>'
        )
        await browser.close()
        
    return pdf_bytes
