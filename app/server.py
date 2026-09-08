# -*- coding: utf-8 -*-
"""
FastAPI Server for Real Estate & Legal Document OCR Web Application.
Provides REST API endpoints for:
- Document categorization & multi-page OCR
- Deep key-value extraction (with Land/Building/UDS, DPDP Masked Aadhaar)
- Local AI Service integration (Qwen2.5-7B via llama.cpp)
- Multi-document Cross-Verification Matrix
- Dedicated Inherited Property (Varisu & Patta Mutation) Track
"""

import os
import io
import re
import csv
import json
import logging
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.samples import DOCUMENT_CATEGORIES, SAMPLE_DOCUMENTS, MULTI_DOC_BUNDLES
from app.extractor import DocumentExtractor
from app.ocr_engine import OCREngine
from app.cross_checker import CrossVerificationEngine
from app.translator import translate_word_bilingual
from app.llm_engine import QwenDocumentExtractor
from app.validator import ExtractionValidator

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
llm_extractor = QwenDocumentExtractor()

# Zero-disk persistence policy: Documents and extraction details are processed strictly in RAM and never stored permanently
uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
if os.path.exists(uploads_dir):
    for f in os.listdir(uploads_dir):
        fp = os.path.join(uploads_dir, f)
        try:
            if os.path.isfile(fp):
                os.unlink(fp)
        except Exception:
            pass
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


@app.get("/api/llm/status")
async def get_llm_status():
    """Check availability of local Qwen2.5-7B LLM service via llama.cpp."""
    is_avail = await llm_extractor.is_available()
    return {
        "status": "success",
        "llm_available": is_avail,
        "base_url": llm_extractor.base_url,
        "recommended_model": "Qwen2.5-7B-Instruct-GGUF (Q4_K_M)",
        "port": 8080,
        "mode": "Local Private Service (OpenAI-compatible)" if is_avail else "Offline (Rule-based & IndicTrans2 fallback active)"
    }


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


@app.post("/api/llm/extract")
async def run_llm_extraction(payload: Dict[str, Any]):
    """Direct structured extraction using local Qwen2.5-7B LLM engine."""
    doc_type = payload.get("doc_type", "sale_deed")
    text = payload.get("text", "")
    page_num = payload.get("page_num", 1)
    target_fields = payload.get("target_fields")

    if not text.strip():
        raise HTTPException(status_code=400, detail="Empty text provided for LLM extraction.")

    is_avail = await llm_extractor.is_available()
    if not is_avail:
        # Fallback to local rule-based extractor
        fallback_res = extractor.extract(text, doc_type=doc_type)
        return {
            "status": "fallback",
            "engine": "Rule-Based + IndicTrans2",
            "extracted_fields": fallback_res.get("fields", {})
        }

    llm_res = await llm_extractor.extract_document_fields(
        doc_type=doc_type,
        ocr_text=text,
        page_num=page_num,
        target_fields=target_fields
    )

    # Post-process with deterministic validation safeguards
    for field_k, field_obj in llm_res.items():
        if isinstance(field_obj, dict) and "value" in field_obj:
            v_str = str(field_obj["value"])
            if "survey" in field_k:
                sy_val = ExtractionValidator.validate_survey_and_subdivision(v_str, text)
                if not sy_val["valid"] and sy_val.get("suggested_value"):
                    field_obj["value"] = sy_val["suggested_value"]
                    field_obj["needs_review"] = True
            elif "aadhaar" in field_k:
                field_obj["value"] = ExtractionValidator.enforce_dpdp_masking(v_str)

    return {
        "status": "success",
        "engine": "Qwen2.5-7B-Instruct (llama.cpp)",
        "extracted_fields": llm_res
    }


@app.post("/api/ocr/process")
async def process_document_upload(
    file: UploadFile = File(...),
    doc_type: Optional[str] = Form("auto"),
    lang: Optional[str] = Form("ta"),
    use_llm: Optional[bool] = Form(False)
):
    """Process uploaded file: runs OCR, deep entity extraction, and legal checklist."""
    try:
        content = await file.read()
        filename = file.filename or "uploaded_document"

        logger.info(f"Processing uploaded file: {filename}, size: {len(content)} bytes, type: {doc_type}, lang: {lang}, use_llm: {use_llm}")

        # Execute OCR engine
        ocr_result = ocr_engine.process_file(content, filename, lang=lang)

        text_to_extract = ocr_result["aggregated_text"]
        if not text_to_extract.strip():
            text_to_extract = f"Document: {filename}\nNo legible text detected."

        target_doc_type = doc_type if doc_type and doc_type != "auto" else None
        extraction_result = extractor.extract(text_to_extract, doc_type=target_doc_type, pages=ocr_result['pages'], file_bytes=content, filename=filename)

        # If LLM requested and available, enhance fields
        if use_llm and await llm_extractor.is_available():
            detected_type = extraction_result.get("document_type_id", "sale_deed")
            rel_pages = llm_extractor.filter_relevant_pages(ocr_result["pages"], detected_type)
            combined_text = "\n\n".join(p.get("text", "") for p in rel_pages)
            llm_fields = await llm_extractor.extract_document_fields(detected_type, combined_text)
            if llm_fields:
                fields_dict = extraction_result.setdefault("fields", {})
                for k, v in llm_fields.items():
                    if isinstance(v, dict) and v.get("value") is not None:
                        val_str = str(v.get("value")).strip()
                        if not val_str or val_str.lower() in ["null", "none", "not detected", "-", ""]:
                            continue

                        # Validate survey numbers and Aadhaar
                        if "survey" in k:
                            sy_val = ExtractionValidator.validate_survey_and_subdivision(val_str, combined_text)
                            if not sy_val["valid"] and sy_val.get("suggested_value"):
                                v["value"] = sy_val["suggested_value"]
                                v["needs_review"] = True
                        elif "aadhaar" in k:
                            v["value"] = ExtractionValidator.enforce_dpdp_masking(val_str)
                        elif k in ["village", "taluk", "district", "town_village"]:
                            from app.translator import format_bilingual_entity
                            v["value"] = format_bilingual_entity(val_str)

                        # Match exact key or common aliases
                        matched_key = k if k in fields_dict else None
                        if not matched_key:
                            for alt in [f"{k}s", k.rstrip("s"), f"{k}_name", f"{k}_details"]:
                                if alt in fields_dict:
                                    matched_key = alt
                                    break

                        target_key = matched_key or k
                        if target_key in fields_dict:
                            fields_dict[target_key]["llm_enhanced"] = v
                            curr_val = str(fields_dict[target_key].get("value", "")).strip()
                            # Replace if current is "Not Detected", empty, or LLM extracted valid data
                            if not curr_val or curr_val.lower() in ["-", "null", "none", "not detected", ""]:
                                fields_dict[target_key]["value"] = v.get("value")
                                fields_dict[target_key]["confidence"] = max(fields_dict[target_key].get("confidence", 0.0), v.get("confidence", 0.95))
                                if "box_query" not in fields_dict[target_key] or not fields_dict[target_key]["box_query"]:
                                    fields_dict[target_key]["box_query"] = v.get("value")
                        else:
                            fields_dict[target_key] = {
                                "value": v.get("value"),
                                "confidence": v.get("confidence", 0.95),
                                "source_text": v.get("source_text", ""),
                                "llm_enhanced": v,
                                "box_query": v.get("value")
                            }

        return {
            "status": "success",
            "model": "PaddleOCR-VL-1.6",
            "filename": filename,
            "storage_policy": "ephemeral_memory_only (zero_disk_retention)",
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
                "sr_no", "doc_no_year", "execution_date", "presentation_date", "registration_date",
                "nature", "executants", "claimants", "vol_page", "consideration_value",
                "market_value", "pr_numbers", "remarks"
            ])
            tx_obj = extracted_fields.get("transactions_table", {})
            tx_list = tx_obj.get("value", []) if isinstance(tx_obj, dict) else (tx_obj if isinstance(tx_obj, list) else [])
            for tx in tx_list:
                exec_d = tx.get("execution_date") or tx.get("date") or "-"
                pres_d = tx.get("presentation_date") or exec_d
                reg_d = tx.get("registration_date") or exec_d

                writer.writerow([
                    tx.get("sr_no") or tx.get("sr") or "",
                    tx.get("doc_no_year") or tx.get("doc_no") or "-",
                    exec_d,
                    pres_d,
                    reg_d,
                    tx.get("nature", "-"),
                    tx.get("executants", "-"),
                    tx.get("claimants", "-"),
                    tx.get("vol_page", "-"),
                    tx.get("consideration_value") or tx.get("consideration") or "-",
                    tx.get("market_value", "-"),
                    tx.get("pr_numbers") or tx.get("pr_number") or "-",
                    tx.get("remarks") or tx.get("document_remarks") or ""
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
