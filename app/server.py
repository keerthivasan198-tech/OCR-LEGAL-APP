# -*- coding: utf-8 -*-
"""
FastAPI Server for Real Estate & Legal Document OCR Web Application.
Provides REST API endpoints for:
- Document categorization & multi-page OCR
- Deep key-value extraction (with Land/Building/UDS, DPDP Masked Aadhaar)
- Multi-document Cross-Verification Matrix
- Dedicated Inherited Property (Varisu & Patta Mutation) Track
"""

import os
import io
import re
import csv
import json
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.samples import DOCUMENT_CATEGORIES, SAMPLE_DOCUMENTS, MULTI_DOC_BUNDLES
from app.extractor import DocumentExtractor
from app.ocr_engine import OCREngine
from app.cross_checker import CrossVerificationEngine
from app.translator import translate_word_bilingual

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OCRServer")

app = FastAPI(
    title="PlotChoice Real Estate OCR & Cross-Verification Engine",
    description="AI-powered OCR and cross-document intelligence for Indian & Tamil Nadu property records.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engines
extractor = DocumentExtractor()
ocr_engine = OCREngine()
cross_checker = CrossVerificationEngine()

# Ensure uploads folder exists
os.makedirs("uploads", exist_ok=True)

# Mount static folder
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_home():
    """Serve the main frontend SPA."""
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>OCR Service Running</h1><p>static/index.html not found</p>")

@app.get("/api/categories")
async def get_document_categories():
    """List all supported document categories and their metadata."""
    return {
        "status": "success",
        "count": len(DOCUMENT_CATEGORIES),
        "categories": DOCUMENT_CATEGORIES
    }

@app.get("/api/sample/{category_id}")
async def get_sample_document(category_id: str):
    """Retrieve pre-configured realistic sample data for instant demonstration."""
    if category_id not in SAMPLE_DOCUMENTS:
        raise HTTPException(status_code=404, detail=f"Sample category '{category_id}' not found.")

    sample = SAMPLE_DOCUMENTS[category_id]
    category_meta = next((c for c in DOCUMENT_CATEGORIES if c["id"] == category_id), None)

    # Run extraction on sample raw text
    extraction_result = extractor.extract(sample["raw_text"], doc_type=category_id)

    # Generate synthetic bounding boxes
    simulated_boxes = []
    all_sim_words = []
    lines = [l.strip() for l in sample["raw_text"].split("\n") if l.strip()]
    total_lines = max(1, len(lines))
    y_step = 85.0 / total_lines

    for idx, line in enumerate(lines):
        line_rect = {
            "x": 40,
            "y": 40 + int(idx * 28),
            "w": min(700, max(200, len(line) * 9)),
            "h": 22,
            "x_pct": 5.0,
            "y_pct": round(2.0 + (idx * y_step), 2),
            "w_pct": round(min(90.0, max(25.0, len(line) * 1.1)), 2),
            "h_pct": round(y_step * 0.85, 2)
        }
        line_words = []
        tokens = list(re.finditer(r'\S+', line))
        tot_chars = max(1, len(line))
        for m in tokens:
            w_text = m.group()
            w_pct_start = line_rect["x_pct"] + (m.start() / tot_chars) * line_rect["w_pct"]
            w_pct_w = max(1.5, (len(w_text) / tot_chars) * line_rect["w_pct"])
            w_trans = translate_word_bilingual(w_text)
            w_obj = {
                "text": w_text,
                "translation": w_trans,
                "confidence": 0.98,
                "x_pct": round(w_pct_start, 2),
                "y_pct": line_rect["y_pct"],
                "w_pct": round(w_pct_w, 2),
                "h_pct": line_rect["h_pct"]
            }
            line_words.append(w_obj)
            all_sim_words.append(w_obj)

        simulated_boxes.append({
            "text": line,
            "confidence": 0.98,
            "words": line_words,
            "rect": line_rect
        })

    return {
        "status": "success",
        "category": category_meta,
        "title": sample["title"],
        "raw_text": sample["raw_text"],
        "structured_sample": sample.get("structured", {}),
        "extracted_data": extraction_result,
        "is_sample": True,
        "simulated_page": {
            "page_number": 1,
            "width": 800,
            "height": 1100,
            "lines": simulated_boxes,
            "words": all_sim_words,
            "full_text": sample["raw_text"],
            "preview_url": None
        }
    }

@app.get("/api/bundles")
async def list_bundles():
    """List available multi-document verification project bundles."""
    bundles_meta = []
    for b_id, b in MULTI_DOC_BUNDLES.items():
        bundles_meta.append({
            "bundle_id": b["bundle_id"],
            "title": b["title"],
            "description": b["description"]
        })
    return {"status": "success", "bundles": bundles_meta}

@app.get("/api/bundle/{bundle_id}")
async def get_bundle(bundle_id: str):
    """Retrieve full bundle data for cross-verification matrix."""
    if bundle_id not in MULTI_DOC_BUNDLES:
        raise HTTPException(status_code=404, detail=f"Bundle '{bundle_id}' not found.")
    bundle = MULTI_DOC_BUNDLES[bundle_id]

    if "documents" in bundle:
        cross_check_res = cross_checker.run_standard_cross_check(bundle["documents"])
        return {
            "status": "success",
            "bundle": bundle,
            "cross_check": cross_check_res
        }
    elif "inheritance_data" in bundle:
        inh_res = cross_checker.run_inheritance_track_check(bundle["inheritance_data"])
        return {
            "status": "success",
            "bundle": bundle,
            "inheritance_check": inh_res
        }

@app.post("/api/cross-verify")
async def run_cross_verification(docs: Dict[str, Any]):
    """Run automated cross-document verification matrix."""
    res = cross_checker.run_standard_cross_check(docs)
    return {"status": "success", "matrix": res}

@app.post("/api/inheritance-verify")
async def run_inheritance_verification(inh_data: Dict[str, Any]):
    """Run dedicated inheritance title verification."""
    res = cross_checker.run_inheritance_track_check(inh_data)
    return {"status": "success", "inheritance": res}

@app.post("/api/ocr/process")
async def process_document_upload(
    file: UploadFile = File(...),
    doc_type: Optional[str] = Form("auto"),
    lang: Optional[str] = Form("ta")
):
    """Process uploaded file: runs OCR, deep entity extraction, and legal checklist."""
    try:
        content = await file.read()
        filename = file.filename or "uploaded_document"

        logger.info(f"Processing uploaded file: {filename}, size: {len(content)} bytes, type: {doc_type}, lang: {lang}")

        # Execute OCR engine
        ocr_result = ocr_engine.process_file(content, filename, lang=lang)

        text_to_extract = ocr_result["aggregated_text"]
        if not text_to_extract.strip():
            text_to_extract = f"Document: {filename}\nNo legible text detected."

        target_doc_type = doc_type if doc_type and doc_type != "auto" else None
        extraction_result = extractor.extract(text_to_extract, doc_type=target_doc_type, pages=ocr_result['pages'])

        return {
            "status": "success",
            "model": "PaddleOCR-VL-1.6",
            "filename": filename,
            "total_pages": ocr_result["total_pages"],
            "pages": ocr_result["pages"],
            "aggregated_text": ocr_result["aggregated_text"],
            "extraction": extraction_result
        }
    except Exception as e:
        logger.error(f"Error processing document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")

@app.post("/api/export")
async def export_data(data: dict):
    """Export extracted results into PDF, JSON, CSV, or Text format."""
    format_type = data.get("format", "json").lower()
    doc_type = data.get("doc_type", "document")
    extracted_fields = data.get("fields", {})

    if format_type == "pdf":
        try:
            from app.pdf_generator import generate_ocr_pdf_report
            pdf_bytes = generate_ocr_pdf_report(data)
            filename = data.get("filename", "Document")
            base_name = os.path.splitext(filename)[0]
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{base_name}_OCR_Report.pdf"'}
            )
        except Exception as e:
            logger.error(f"PDF generation failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    elif format_type == "csv":
        output = io.StringIO()
        writer = csv.writer(output)

        is_ec = (doc_type == "ec") or ("transactions_table" in extracted_fields)
        if is_ec:
            writer.writerow([
                "Sr", "Doc No/Year", "Execution Date", "Presentation Date", "Registration Date",
                "Nature", "Consideration Value", "Market Value", "PR Number",
                "Executant(s)", "Claimant(s)", "Schedule Details"
            ])
            tx_obj = extracted_fields.get("transactions_table", {})
            tx_list = tx_obj.get("value", []) if isinstance(tx_obj, dict) else (tx_obj if isinstance(tx_obj, list) else [])
            for tx in tx_list:
                exec_d = tx.get("execution_date", {}).get("standard") if isinstance(tx.get("execution_date"), dict) else tx.get("date", "-")
                pres_d = tx.get("presentation_date", {}).get("standard") if isinstance(tx.get("presentation_date"), dict) else exec_d
                reg_d = tx.get("registration_date", {}).get("standard") if isinstance(tx.get("registration_date"), dict) else exec_d

                sch_list = tx.get("schedules", [])
                sch_summary = ""
                if sch_list and isinstance(sch_list, list):
                    s0 = sch_list[0]
                    parts = []
                    if s0.get("extent") and s0.get("extent") != "-": parts.append(s0["extent"])
                    if s0.get("survey_no") and s0.get("survey_no") != "-": parts.append(f"Sy:{s0['survey_no']}")
                    if s0.get("plot_no") and s0.get("plot_no") != "-": parts.append(f"Plot:{s0['plot_no']}")
                    sch_summary = ", ".join(parts) or s0.get("property_type", "-")

                writer.writerow([
                    tx.get("sr", ""),
                    tx.get("doc_no", "-"),
                    exec_d,
                    pres_d,
                    reg_d,
                    tx.get("nature", "-"),
                    tx.get("consideration", "-"),
                    tx.get("market_value", "-"),
                    tx.get("pr_number", "-"),
                    tx.get("executants", "-"),
                    tx.get("claimants", "-"),
                    sch_summary
                ])
        else:
            writer.writerow(["Field Name", "Extracted Value", "Confidence"])
            for k, v in extracted_fields.items():
                if isinstance(v, dict):
                    val = v.get("value", "")
                    conf = v.get("confidence", "")
                    if isinstance(val, dict):
                        for sub_k, sub_v in val.items():
                            writer.writerow([f"{k}.{sub_k}", sub_v, conf])
                    else:
                        writer.writerow([k, val, conf])
                else:
                    writer.writerow([k, str(v), "1.0"])

        filename = data.get("filename", doc_type)
        base_name = os.path.splitext(filename)[0]
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{base_name}_extracted.csv"'}
        )

    elif format_type == "txt":
        lines = [
            "==================================================",
            "REAL ESTATE DOCUMENT OCR EXTRACTION REPORT",
            f"Document Type: {doc_type.upper()}",
            "==================================================\n"
        ]
        for k, v in extracted_fields.items():
            if isinstance(v, dict):
                val = v.get("value", "")
                lines.append(f"{k.replace('_', ' ').title()}: {val}")
            else:
                lines.append(f"{k.replace('_', ' ').title()}: {v}")

        return Response(
            content="\n".join(lines),
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={doc_type}_extracted.txt"}
        )

    else:
        return JSONResponse(
            content=data,
            headers={"Content-Disposition": f"attachment; filename={doc_type}_extracted.json"}
        )


@app.post("/api/export/pdf")
async def export_pdf(data: dict):
    """Export extracted results directly into a professional PDF report."""
    try:
        from app.pdf_generator import generate_ocr_pdf_report
        pdf_bytes = generate_ocr_pdf_report(data)
        filename = data.get("filename", "Document")
        base_name = os.path.splitext(filename)[0]
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{base_name}_OCR_Report.pdf"'}
        )
    except Exception as e:
        logger.error(f"PDF export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}")

