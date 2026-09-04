# -*- coding: utf-8 -*-
"""
Dual-Pipeline OCR Engine for Tamil Nadu Property Documents.

Pipeline:
  INPUT (PDF/Image)
    -> PaddleOCR(lang='ta')  -- Primary Tamil recognition
    -> PaddleOCR(lang='en')  -- Secondary English recognition
    -> Smart Line Merger      -- Best of both per region
    -> Reading Order Sort     -- Top-to-bottom, left-to-right
    -> Output JSON
"""

import os, io, re, base64, logging
from typing import List, Dict, Any, Optional
from PIL import Image, ImageOps
import numpy as np
import pypdfium2 as pdfium
from app.translator import translate_word_bilingual

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OCREngine")


class OCREngine:
    """Dual-pipeline OCR: Tamil primary + English secondary with smart merging."""

    _instance = None
    _pipeline_ta = None
    _pipeline_en = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OCREngine, cls).__new__(cls)
            cls._instance._init_models()
        return cls._instance

    def _init_models(self):
        self.paddle_available = False
        try:
            from paddleocr import PaddleOCR
            self.PaddleOCR = PaddleOCR
            self.paddle_available = True
            logger.info("PaddleOCR module loaded successfully.")
        except Exception as e:
            logger.error(f"PaddleOCR import error: {e}")

    def _get_pipeline_ta(self):
        """Primary Tamil pipeline: PaddleOCR-VL-1.6 with PP-OCRv5_server_det + ta_PP-OCRv5_mobile_rec."""
        if self._pipeline_ta is None and self.paddle_available:
            logger.info("Loading PaddleOCR-VL-1.6 Tamil pipeline: PaddleOCR(lang='ta')...")
            self._pipeline_ta = self.PaddleOCR(
                lang="ta",
                use_doc_orientation_classify=True,
                use_doc_unwarping=False,
                use_textline_orientation=True,
            )
            logger.info("PaddleOCR-VL-1.6 Tamil pipeline loaded.")
        return self._pipeline_ta

    def _get_pipeline_en(self):
        """Secondary English pipeline: PaddleOCR-VL-1.6 with PP-OCRv6_medium_det + PP-OCRv6_medium_rec."""
        if self._pipeline_en is None and self.paddle_available:
            logger.info("Loading PaddleOCR-VL-1.6 English pipeline: PaddleOCR(lang='en')...")
            self._pipeline_en = self.PaddleOCR(
                lang="en",
                use_doc_orientation_classify=True,
                use_doc_unwarping=False,
                use_textline_orientation=True,
            )
            logger.info("PaddleOCR-VL-1.6 English pipeline loaded.")
        return self._pipeline_en

    # -- File Conversion --

    def convert_file_to_images(self, file_bytes, filename):
        ext = os.path.splitext(filename)[1].lower()
        images = []

        if isinstance(file_bytes, str):
            with open(file_bytes, "rb") as f:
                file_bytes = f.read()

        if ext == ".pdf":
            pdf = pdfium.PdfDocument(file_bytes)
            for page_index in range(len(pdf)):
                page = pdf[page_index]
                bitmap = page.render(scale=3.0)  # Higher scale = better Tamil OCR accuracy
                pil_image = bitmap.to_pil()
                images.append(pil_image)
        else:
            img = Image.open(io.BytesIO(file_bytes))
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass
            if img.mode != "RGB":
                img = img.convert("RGB")
            images.append(img)

        return images

    def image_to_base64(self, image, max_dim=1600, quality=85):
        img = image.copy()
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=quality, optimize=True)
        encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{encoded}"

    # -- Helpers --

    @staticmethod
    def _has_tamil(text):
        return bool(re.search(r'[\u0b80-\u0bff]', text))

    @staticmethod
    def _has_english(text):
        return bool(re.search(r'[A-Za-z]{2,}', text))

    @staticmethod
    def _has_digits(text):
        return bool(re.search(r'\d', text))

    @staticmethod
    def _poly_to_rect(poly, width, height):
        xs = [float(pt[0]) for pt in poly]
        ys = [float(pt[1]) for pt in poly]
        min_x = max(0.0, min(xs))
        min_y = max(0.0, min(ys))
        max_x = min(float(width), max(xs))
        max_y = min(float(height), max(ys))
        return {
            "x": round(min_x, 1),
            "y": round(min_y, 1),
            "w": round(max(5.0, max_x - min_x), 1),
            "h": round(max(5.0, max_y - min_y), 1),
            "x_pct": round((min_x / width) * 100, 2),
            "y_pct": round((min_y / height) * 100, 2),
            "w_pct": round(((max_x - min_x) / width) * 100, 2),
            "h_pct": round(((max_y - min_y) / height) * 100, 2),
        }

    @staticmethod
    def _poly_center_y(poly):
        ys = [float(pt[1]) for pt in poly]
        return (min(ys) + max(ys)) / 2.0

    @staticmethod
    def _poly_center_x(poly):
        xs = [float(pt[0]) for pt in poly]
        return (min(xs) + max(xs)) / 2.0

    # -- Core OCR Processing --

    def _run_pipeline(self, pipeline, img_np):
        """Run a PaddleOCR pipeline and return (texts, scores, polys)."""
        texts, scores, polys = [], [], []
        try:
            results = pipeline.predict(img_np)
            if results:
                for res in results:
                    if hasattr(res, 'get'):
                        rt = res.get("rec_texts", [])
                        rs = res.get("rec_scores", [])
                        rp = res.get("dt_polys", res.get("rec_polys", []))
                        texts.extend(rt)
                        scores.extend([float(s) for s in rs])
                        polys.extend(rp)
                    elif isinstance(res, list):
                        for item in res:
                            if isinstance(item, (list, tuple)) and len(item) == 2:
                                polys.append(item[0])
                                texts.append(item[1][0])
                                scores.append(float(item[1][1]))
        except Exception as e:
            logger.error(f"Pipeline error: {e}")

        return texts, scores, polys

    def _merge_lines(self, ta_texts, ta_scores, ta_polys,
                     en_texts, en_scores, en_polys,
                     width, height):
        """
        Smart merge: for each detected region, pick the best recognition.

        Strategy:
        - Tamil pipeline is PRIMARY (detects Tamil text correctly).
        - English pipeline is SECONDARY (better for pure English/digits).
        - English model cannot read Tamil script and hallucinates garbage ASCII
          (e.g. '(J6uL' for 'முத்துலட்சுமி', '6u(Lo' for 'செந்தில்குமார்').
        - When a region contains Tamil, the Tamil pipeline is authoritative.
        - Matched English lines are flagged so they are NEVER emitted as duplicate lines.
        """
        lines = []

        # Build a spatial index of English results for cross-referencing
        en_index = []
        for i, poly in enumerate(en_polys):
            if poly is not None and len(poly) > 0:
                xs = [float(pt[0]) for pt in poly]
                ys = [float(pt[1]) for pt in poly]
                x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
                en_index.append({
                    "idx": i,
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "cx": (x1 + x2) / 2.0, "cy": (y1 + y2) / 2.0,
                    "w": max(5.0, x2 - x1), "h": max(5.0, y2 - y1),
                    "poly": poly,
                    "text": en_texts[i] if i < len(en_texts) else "",
                    "score": en_scores[i] if i < len(en_scores) else 0.0,
                    "matched": False,
                })

        # Process Tamil pipeline results (primary)
        for i, poly in enumerate(ta_polys):
            if poly is None or len(poly) == 0:
                continue

            ta_text = ta_texts[i] if i < len(ta_texts) else ""
            ta_score = ta_scores[i] if i < len(ta_scores) else 0.0
            xs = [float(pt[0]) for pt in poly]
            ys = [float(pt[1]) for pt in poly]
            ta_x1, ta_y1, ta_x2, ta_y2 = min(xs), min(ys), max(xs), max(ys)
            ta_w = max(5.0, ta_x2 - ta_x1)
            ta_h = max(5.0, ta_y2 - ta_y1)
            ta_cy = (ta_y1 + ta_y2) / 2.0
            ta_cx = (ta_x1 + ta_x2) / 2.0

            # Find matching English lines using 2D box overlap
            best_en = None
            best_en_score = -1.0

            for en in en_index:
                # Vertical overlap
                v_ov = max(0.0, min(ta_y2, en["y2"]) - max(ta_y1, en["y1"]))
                v_ratio = v_ov / min(ta_h, en["h"])
                cy_diff = abs(ta_cy - en["cy"])

                # Horizontal overlap
                h_ov = max(0.0, min(ta_x2, en["x2"]) - max(ta_x1, en["x1"]))
                h_ratio = h_ov / min(ta_w, en["w"])
                cx_diff = abs(ta_cx - en["cx"])

                # Two boxes are the same physical line if vertical overlap is significant
                # and horizontal centers/spans overlap
                is_match = False
                if (v_ratio > 0.35 or cy_diff < 0.6 * max(ta_h, en["h"])) and (h_ratio > 0.10 or cx_diff < 0.7 * max(ta_w, en["w"])):
                    is_match = True

                if is_match:
                    en["matched"] = True  # Suppress English duplicate
                    if en["score"] > best_en_score:
                        best_en = en
                        best_en_score = en["score"]

            # Decide which text to use
            best_en_text = best_en["text"] if best_en else ""
            final_text = ta_text
            final_score = ta_score

            if ta_text.strip():
                has_ta = self._has_tamil(ta_text)
                has_en_in_ta = self._has_english(ta_text)
                has_digits_ta = self._has_digits(ta_text)

                if has_ta:
                    # Tamil script detected: Tamil model is authoritative.
                    # Never overwrite with English model garbage (which mangles Tamil script).
                    final_text = ta_text
                    final_score = ta_score
                elif has_digits_ta or has_en_in_ta:
                    # Pure English/digit line (e.g. table extents, numbers)
                    if best_en_text and best_en_score > ta_score:
                        final_text = best_en_text
                        final_score = best_en_score
                    else:
                        final_text = ta_text
                        final_score = ta_score
                else:
                    # Low-confidence / noise in Tamil pipeline
                    if best_en_text and best_en_score > 0.5:
                        final_text = best_en_text
                        final_score = best_en_score
            elif best_en_text:
                final_text = best_en_text
                final_score = best_en_score

            if not final_text.strip():
                continue

            rect = self._poly_to_rect(poly, width, height)
            lines.append({
                "text": final_text,
                "confidence": round(final_score, 4),
                "rect": rect,
                "sort_y": ta_cy,
                "sort_x": ta_cx,
            })

        # Include ONLY unmatched standalone English lines (e.g. purely English sections/headers)
        for en in en_index:
            if en.get("matched", False):
                continue
            if not en["text"].strip() or en["score"] < 0.5:
                continue

            # Check if this English box has spatial overlap with ANY already accepted line
            is_overlap = False
            for line in lines:
                l_rect = line["rect"]
                ly1, ly2 = l_rect["y"], l_rect["y"] + l_rect["h"]
                lx1, lx2 = l_rect["x"], l_rect["x"] + l_rect["w"]
                v_ov = max(0.0, min(ly2, en["y2"]) - max(ly1, en["y1"]))
                v_ratio = v_ov / min(l_rect["h"], en["h"])
                if v_ratio > 0.35:
                    h_ov = max(0.0, min(lx2, en["x2"]) - max(lx1, en["x1"]))
                    if h_ov > 0.10 * min(l_rect["w"], en["w"]):
                        is_overlap = True
                        break
            if is_overlap:
                continue

            # Check if text is redundant
            if any(en["text"].strip().lower() in l["text"].lower() for l in lines):
                continue

            poly = en["poly"]
            rect = self._poly_to_rect(poly, width, height)
            lines.append({
                "text": en["text"],
                "confidence": round(en["score"], 4),
                "rect": rect,
                "sort_y": en["cy"],
                "sort_x": en["cx"],
            })

        # Sort in natural document reading order: cluster into rows, then sort left-to-right within each row
        if lines:
            heights = [l["rect"]["h"] for l in lines if l.get("rect", {}).get("h", 0) > 0]
            avg_h = sum(heights) / len(heights) if heights else 20.0
            row_thresh = max(8.0, avg_h * 0.55)

            sorted_by_y = sorted(lines, key=lambda l: l["rect"]["y"])
            rows = []
            for item in sorted_by_y:
                y = item["rect"]["y"]
                placed = False
                for row in rows:
                    row_y = sum(r["rect"]["y"] for r in row) / len(row)
                    if abs(y - row_y) <= row_thresh:
                        row.append(item)
                        placed = True
                        break
                if not placed:
                    rows.append([item])

            rows.sort(key=lambda row: sum(r["rect"]["y"] for r in row) / len(row))
            ordered_lines = []
            for row in rows:
                row.sort(key=lambda r: r["rect"]["x"])
                ordered_lines.extend(row)

            for line in ordered_lines:
                if "sort_y" in line:
                    del line["sort_y"]
                if "sort_x" in line:
                    del line["sort_x"]

            lines = ordered_lines

        return lines

    # -- Public API --

    def process_image(self, image, lang="ta"):
        """Process a single image through the dual OCR pipeline."""
        width, height = image.size
        img_np = np.array(image)
        lines_data = []

        if self.paddle_available:
            pipeline_ta = self._get_pipeline_ta()
            pipeline_en = self._get_pipeline_en()

            if pipeline_ta is not None:
                ta_texts, ta_scores, ta_polys = self._run_pipeline(pipeline_ta, img_np)
                logger.info(f"Tamil pipeline: {len(ta_texts)} lines detected")
            else:
                ta_texts, ta_scores, ta_polys = [], [], []

            if pipeline_en is not None:
                en_texts, en_scores, en_polys = self._run_pipeline(pipeline_en, img_np)
                logger.info(f"English pipeline: {len(en_texts)} lines detected")
            else:
                en_texts, en_scores, en_polys = [], [], []

            lines_data = self._merge_lines(
                ta_texts, ta_scores, ta_polys,
                en_texts, en_scores, en_polys,
                width, height,
            )
            logger.info(f"Merged: {len(lines_data)} lines")

        # Generate word-level bounding boxes and dynamic translations for scanned lines
        all_words = []
        for line in lines_data:
            if "words" not in line or not line["words"]:
                line_words = []
                tokens = list(re.finditer(r'\S+', line.get("text", "")))
                rect = line.get("rect", {})
                line_w = rect.get("w_pct", 0)
                line_x = rect.get("x_pct", 0)
                line_y = rect.get("y_pct", 0)
                line_h = rect.get("h_pct", 0)
                total_len = len(line.get("text", ""))
                if total_len > 0 and line_w > 0:
                    for m in tokens:
                        w_text = m.group()
                        w_start_pct = line_x + (m.start() / total_len) * line_w
                        w_width_pct = max(1.2, (len(w_text) / total_len) * line_w)
                        w_trans = translate_word_bilingual(w_text)
                        w_obj = {
                            "text": w_text,
                            "translation": w_trans,
                            "confidence": line.get("confidence", 0.92),
                            "x_pct": round(w_start_pct, 2),
                            "y_pct": round(line_y, 2),
                            "w_pct": round(w_width_pct, 2),
                            "h_pct": round(line_h, 2),
                        }
                        line_words.append(w_obj)
                        all_words.append(w_obj)
                line["words"] = line_words
            else:
                all_words.extend(line["words"])

        full_text_lines = [line["text"] for line in lines_data]
        preview_url = self.image_to_base64(image)

        return {
            "width": width,
            "height": height,
            "lines": lines_data,
            "words": all_words,
            "full_text": "\n".join(full_text_lines),
            "preview_url": preview_url,
        }

    def _extract_native_pdf_lines(self, tp, width_pt, height_pt):
        """Extract lines, words, and bounding boxes directly from native PDF textpage with 100% character precision."""
        text = tp.get_text_range()
        lines = []
        curr_offset = 0
        total_chars = tp.count_chars()

        for raw_line in text.splitlines(keepends=True):
            clean_str = raw_line.strip('\r\n')
            line_len = len(raw_line)
            if not clean_str.strip():
                curr_offset += line_len
                continue

            start_offset = raw_line.find(clean_str)
            start_char = curr_offset + start_offset
            end_char = start_char + len(clean_str)

            xs, ys = [], []
            words_in_line = []

            # Extract word-level bounding boxes for fine-grained phrase, translation, and field mapping
            for m in re.finditer(r'\S+', clean_str):
                w_text = m.group()
                w_start = start_char + m.start()
                w_end = start_char + m.end()
                w_xs, w_ys = [], []
                for c in range(w_start, min(w_end, total_chars)):
                    wb = tp.get_charbox(c)
                    if wb and (wb[2] > wb[0]) and (wb[3] > wb[1]):
                        w_xs.extend([wb[0], wb[2]])
                        w_ys.extend([wb[1], wb[3]])
                if w_xs and w_ys:
                    w_min_x = max(0.0, min(w_xs))
                    w_max_x = min(width_pt, max(w_xs))
                    w_min_y = max(0.0, min(w_ys))
                    w_max_y = min(height_pt, max(w_ys))
                    w_top_y = height_pt - w_max_y
                    w_trans = translate_word_bilingual(w_text)
                    words_in_line.append({
                        "text": w_text,
                        "translation": w_trans,
                        "confidence": 0.99,
                        "x": round(w_min_x, 1),
                        "y": round(w_top_y, 1),
                        "w": round(max(2.0, w_max_x - w_min_x), 1),
                        "h": round(max(2.0, w_max_y - w_min_y), 1),
                        "x_pct": round((w_min_x / width_pt) * 100, 2),
                        "y_pct": round((w_top_y / height_pt) * 100, 2),
                        "w_pct": round((max(2.0, w_max_x - w_min_x) / width_pt) * 100, 2),
                        "h_pct": round((max(2.0, w_max_y - w_min_y) / height_pt) * 100, 2),
                    })

            for c in range(start_char, min(end_char, total_chars)):
                box = tp.get_charbox(c)
                if box and (box[2] > box[0]) and (box[3] > box[1]):
                    xs.extend([box[0], box[2]])
                    ys.extend([box[1], box[3]])

            if xs and ys:
                min_x = max(0.0, min(xs))
                max_x = min(width_pt, max(xs))
                min_y = max(0.0, min(ys))
                max_y = min(height_pt, max(ys))
                top_y = height_pt - max_y
                rect_w = max(5.0, max_x - min_x)
                rect_h = max(5.0, max_y - min_y)

                lines.append({
                    "text": clean_str.strip(),
                    "confidence": 0.99,
                    "words": words_in_line,
                    "rect": {
                        "x": round(min_x, 1),
                        "y": round(top_y, 1),
                        "w": round(rect_w, 1),
                        "h": round(rect_h, 1),
                        "x_pct": round((min_x / width_pt) * 100, 2),
                        "y_pct": round((top_y / height_pt) * 100, 2),
                        "w_pct": round((rect_w / width_pt) * 100, 2),
                        "h_pct": round((rect_h / height_pt) * 100, 2),
                    }
                })

            curr_offset += line_len

        return lines

    def process_file(self, file_bytes, filename, lang="ta"):
        """
        Process a file (PDF or image) through the dual OCR pipeline.
        Supports multi-page documents (e.g. 1 to 30+ pages) without missing any pages:
        - For digital PDFs with native text: extracts exact text & boxes in milliseconds
        - For scanned PDFs / images: runs the dual PaddleOCR (Tamil+English) pipeline
        """
        if isinstance(file_bytes, str):
            with open(file_bytes, "rb") as f:
                file_bytes = f.read()

        ext = os.path.splitext(filename)[1].lower()
        pages = []
        all_text_parts = []

        if ext == ".pdf":
            pdf = pdfium.PdfDocument(file_bytes)
            num_pages = len(pdf)
            logger.info(f"Processing PDF '{filename}' with {num_pages} pages...")

            for idx in range(num_pages):
                page = pdf[idx]
                width_pt, height_pt = page.get_size()

                # Render high-resolution page image for PaddleOCR-VL-1.6
                scale = 2.0
                bitmap = page.render(scale=scale)
                pil_image = bitmap.to_pil()

                # Process through PaddleOCR-VL-1.6 vision pipeline
                page_res = self.process_image(pil_image, lang=lang)
                page_res["page_number"] = idx + 1
                page_res["preview_url"] = self.image_to_base64(pil_image)

                pages.append(page_res)
                if page_res.get("full_text"):
                    all_text_parts.append(f"--- PAGE {idx + 1} ---\n" + page_res["full_text"])
        else:
            images = self.convert_file_to_images(file_bytes, filename)
            for idx, img in enumerate(images):
                page_res = self.process_image(img, lang=lang)
                page_res["page_number"] = idx + 1
                pages.append(page_res)
                if page_res.get("full_text"):
                    all_text_parts.append(f"--- PAGE {idx + 1} ---\n" + page_res["full_text"])

        aggregated_text = "\n\n".join(all_text_parts) if all_text_parts else ""
        logger.info(f"Completed processing '{filename}': {len(pages)} pages extracted.")
        return {
            "filename": filename,
            "total_pages": len(pages),
            "pages": pages,
            "aggregated_text": aggregated_text,
            "model": "PaddleOCR-VL-1.6",
            "engine": "PaddleOCR-VL-1.6 Vision-Language Model",
        }
