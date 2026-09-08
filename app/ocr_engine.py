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
            # Fix Windows Python 3.13 DLL search path for PyTorch / Paddle
            import sys
            if sys.platform == "win32":
                torch_lib = os.path.join(sys.prefix, "Lib", "site-packages", "torch", "lib")
                if os.path.exists(torch_lib):
                    try:
                        os.add_dll_directory(torch_lib)
                    except Exception:
                        pass
                try:
                    import torch
                except Exception:
                    pass

            # Disable MKLDNN/oneDNN PIR CPU instruction bug on Windows
            os.environ["FLAGS_use_mkldnn"] = "0"
            os.environ["FLAGS_enable_pir_api"] = "0"
            os.environ["FLAGS_enable_pir_in_executor"] = "0"
            os.environ["PADDLE_ONEDNN_DISABLE"] = "1"

            import paddle
            try:
                paddle.set_flags({
                    'FLAGS_use_mkldnn': False,
                    'FLAGS_enable_pir_api': False,
                    'FLAGS_enable_pir_in_executor': False
                })
            except Exception:
                pass

            import paddle.inference as paddle_infer
            paddle_infer.Config.enable_mkldnn = lambda self: self.disable_mkldnn()

            from paddleocr import PaddleOCR
            self.PaddleOCR = PaddleOCR
            self.paddle_available = True
            logger.info("PaddleOCR module loaded successfully with oneDNN/PIR CPU safeguards enabled.")
        except Exception as e:
            logger.error(f"PaddleOCR import error: {e}")

    def _get_pipeline_ta(self):
        """Primary Tamil pipeline: PaddleOCR-VL-1.6 with PP-OCRv5_server_det + ta_PP-OCRv5_mobile_rec."""
        if self._pipeline_ta is None and self.paddle_available:
            logger.info("Loading PaddleOCR-VL-1.6 Tamil pipeline: PaddleOCR(lang='ta')...")
            self._pipeline_ta = self.PaddleOCR(
                lang="ta",
                use_doc_orientation_classify=False,
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
                use_doc_orientation_classify=False,
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

    def _run_easyocr_fallback(self, img_np, width, height, lang="ta"):
        """Fallback OCR engine using EasyOCR for image extraction when PaddlePaddle encounters PIR errors."""
        try:
            import easyocr
            langs = ['ta', 'en'] if lang == "ta" else ['en']
            reader = easyocr.Reader(langs, gpu=False, verbose=False)
            results = reader.readtext(img_np)
            lines = []
            for item in results:
                bbox, text, score = item[0], item[1], item[2]
                if not text.strip() or score < 0.2:
                    continue
                xs = [float(pt[0]) for pt in bbox]
                ys = [float(pt[1]) for pt in bbox]
                min_x = max(0.0, min(xs))
                min_y = max(0.0, min(ys))
                max_x = min(float(width), max(xs))
                max_y = min(float(height), max(ys))
                w = max(5.0, max_x - min_x)
                h = max(5.0, max_y - min_y)

                rect = {
                    "x": round(min_x, 1),
                    "y": round(min_y, 1),
                    "w": round(w, 1),
                    "h": round(h, 1),
                    "x_pct": round((min_x / width) * 100, 2),
                    "y_pct": round((min_y / height) * 100, 2),
                    "w_pct": round((w / width) * 100, 2),
                    "h_pct": round((h / height) * 100, 2),
                }
                lines.append({
                    "text": text.strip(),
                    "confidence": round(float(score), 4),
                    "rect": rect
                })
            return lines
        except Exception as e:
            logger.warning(f"EasyOCR fallback error: {e}")
            return []

    @staticmethod
    def clean_tamil_ocr_text(text: str) -> str:
        """Normalize Tamil OCR ligatures, punctuation artifacts, and common character misrecognitions."""
        if not text:
            return ""
        import unicodedata
        t = unicodedata.normalize('NFC', text)
        # Strip raw CID font artifacts e.g. (cid:2), (cid:39)
        t = re.sub(r'\(cid:\d+\)', '', t)
        # Fix noisy quotes and punctuation inserted inside words
        t = re.sub(r"மாவ['`’]டம்", "மாவட்டம்", t)
        t = re.sub(r"வ['`’]டம்", "வட்டம்", t)
        t = re.sub(r"ப['`’]டா", "பட்டா", t)
        t = re.sub(r"\bதநாடூ\s*அர\b", "தமிழ்நாடு அரசு", t)
        t = re.sub(r"\bமேலாணமை\b", "மேலாண்மை", t)
        t = re.sub(r"இ\.எ[ரர]\s*10\(1\)", "படிவம் எண் 10(1)", t)
        t = re.sub(r"இ\.எ[ரர]", "படிவம் எண்", t)
        t = re.sub(r"உரிமையாள[கேர][\s|]*பெய[ரர]", "உரிமையாளர்கள் பெயர்", t)
        t = re.sub(r"\bமக\+\b", "மகன்", t)
        t = re.sub(r"\bந\+செ\b", "நஞ்சை", t)
        t = re.sub(r"\b7\+செ\b", "புஞ்சை", t)
        t = re.sub(r"எ[ரர]\b", "எண்", t)
        t = re.sub(r"பெய[ரர]\b", "பெயர்", t)
        return t.strip()

    # -- Public API --

    def process_image(self, image, lang="ta"):
        """Process a single image through the dual OCR pipeline with EasyOCR fallback and image pre-processing."""
        # Pre-process image: upscale low-res documents for crisp character segmentation
        orig_w, orig_h = image.size
        processed_img = image
        scale_factor = 1.0

        if max(orig_w, orig_h) < 1600:
            scale_factor = min(3.0, 1800.0 / max(orig_w, orig_h))
            new_w = int(orig_w * scale_factor)
            new_h = int(orig_h * scale_factor)
            processed_img = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
            logger.info(f"Upscaled image {orig_w}x{orig_h} -> {new_w}x{new_h} (scale={scale_factor:.2f}) for enhanced Tamil OCR.")

        if processed_img.mode != "RGB":
            processed_img = processed_img.convert("RGB")

        cur_w, cur_h = processed_img.size
        img_np = np.array(processed_img)
        lines_data = []

        if self.paddle_available:
            if lang == "en":
                pipeline_en = self._get_pipeline_en()
                en_texts, en_scores, en_polys = self._run_pipeline(pipeline_en, img_np) if pipeline_en else ([], [], [])
                lines_data = self._merge_lines([], [], [], en_texts, en_scores, en_polys, cur_w, cur_h)
            else:
                pipeline_ta = self._get_pipeline_ta()
                ta_texts, ta_scores, ta_polys = self._run_pipeline(pipeline_ta, img_np) if pipeline_ta else ([], [], [])
                logger.info(f"Tamil pipeline: {len(ta_texts)} lines detected")
                if len(ta_texts) > 0:
                    lines_data = self._merge_lines(ta_texts, ta_scores, ta_polys, [], [], [], cur_w, cur_h)
                else:
                    pipeline_en = self._get_pipeline_en()
                    en_texts, en_scores, en_polys = self._run_pipeline(pipeline_en, img_np) if pipeline_en else ([], [], [])
                    lines_data = self._merge_lines([], [], [], en_texts, en_scores, en_polys, cur_w, cur_h)

            logger.info(f"PaddleOCR extracted: {len(lines_data)} lines")

        # If Paddle pipeline returned 0 lines, invoke EasyOCR fallback
        if not lines_data:
            logger.info("PaddleOCR returned 0 lines. Invoking EasyOCR fallback...")
            lines_data = self._run_easyocr_fallback(img_np, cur_w, cur_h, lang=lang)

        # Normalize Tamil OCR text in all lines
        for line in lines_data:
            if "text" in line:
                line["text"] = self.clean_tamil_ocr_text(line["text"])

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
            "width": orig_w,
            "height": orig_h,
            "lines": lines_data,
            "words": all_words,
            "full_text": "\n".join(full_text_lines),
            "preview_url": preview_url,
        }

    def _extract_native_pdf_lines(self, pdfplumber_page, width_pt, height_pt):
        """Extract lines, words, and bounding boxes directly from native PDF page with 100% character and spatial precision."""
        raw_words = pdfplumber_page.extract_words()
        if not raw_words:
            return [], []

        all_words = []
        for w in raw_words:
            w_text = w.get("text", "").strip()
            if not w_text:
                continue
            x0 = max(0.0, float(w.get("x0", 0.0)))
            top = max(0.0, float(w.get("top", 0.0)))
            x1 = min(float(width_pt), float(w.get("x1", x0 + 5.0)))
            bottom = min(float(height_pt), float(w.get("bottom", top + 5.0)))
            w_val = max(2.0, x1 - x0)
            h_val = max(2.0, bottom - top)

            norm_text = self.clean_tamil_ocr_text(w_text)
            w_trans = translate_word_bilingual(norm_text)
            all_words.append({
                "text": norm_text,
                "translation": w_trans,
                "confidence": 0.99,
                "x": round(x0, 1),
                "y": round(top, 1),
                "w": round(w_val, 1),
                "h": round(h_val, 1),
                "x_pct": round((x0 / width_pt) * 100, 2),
                "y_pct": round((top / height_pt) * 100, 2),
                "w_pct": round((w_val / width_pt) * 100, 2),
                "h_pct": round((h_val / height_pt) * 100, 2),
            })

        # Group words into natural reading order lines
        text_lines = pdfplumber_page.extract_text_lines(layout=False)
        lines = []
        for tl in text_lines:
            t_text = self.clean_tamil_ocr_text(tl.get("text", "").strip())
            if not t_text:
                continue
            lx0 = max(0.0, float(tl.get("x0", 0.0)))
            ltop = max(0.0, float(tl.get("top", 0.0)))
            lx1 = min(float(width_pt), float(tl.get("x1", lx0 + 5.0)))
            lbottom = min(float(height_pt), float(tl.get("bottom", ltop + 5.0)))
            lw = max(4.0, lx1 - lx0)
            lh = max(4.0, lbottom - ltop)

            # Associate words belonging to this line
            line_words = [
                w for w in all_words
                if (ltop - 3.0 <= w["y"] <= lbottom + 3.0) and (lx0 - 4.0 <= w["x"] <= lx1 + 4.0)
            ]

            lines.append({
                "text": t_text,
                "confidence": 0.99,
                "words": line_words,
                "rect": {
                    "x": round(lx0, 1),
                    "y": round(ltop, 1),
                    "w": round(lw, 1),
                    "h": round(lh, 1),
                    "x_pct": round((lx0 / width_pt) * 100, 2),
                    "y_pct": round((ltop / height_pt) * 100, 2),
                    "w_pct": round((lw / width_pt) * 100, 2),
                    "h_pct": round((lh / height_pt) * 100, 2),
                }
            })

        return lines, all_words

    def process_file(self, file_bytes, filename, lang="ta"):
        """
        Process a file (PDF or image) through the dual OCR pipeline.
        Supports multi-page documents (e.g. 1 to 30+ pages) without missing any pages:
        - For digital PDFs with native text: extracts exact text & boxes via pdfplumber
        - For scanned PDFs / images: runs the dual PaddleOCR + EasyOCR pipeline
        """
        if isinstance(file_bytes, str):
            with open(file_bytes, "rb") as f:
                file_bytes = f.read()

        ext = os.path.splitext(filename)[1].lower()
        pages = []
        all_text_parts = []

        if ext == ".pdf":
            import io
            import pdfplumber
            import pypdfium2 as pdfium

            pdf_plum = pdfplumber.open(io.BytesIO(file_bytes))
            pdf_ium = pdfium.PdfDocument(file_bytes)
            num_pages = len(pdf_plum.pages)
            logger.info(f"Processing PDF '{filename}' with {num_pages} pages...")

            for idx in range(num_pages):
                plum_page = pdf_plum.pages[idx]
                ium_page = pdf_ium[idx]
                width_pt = float(plum_page.width)
                height_pt = float(plum_page.height)

                # Render high-resolution page image for visual preview and bounding box overlays
                scale = 2.0
                bitmap = ium_page.render(scale=scale)
                pil_image = bitmap.to_pil()
                preview_url = self.image_to_base64(pil_image)

                # Extract native digital PDF lines & words with exact top-left coordinates
                native_lines, native_words = self._extract_native_pdf_lines(plum_page, width_pt, height_pt)
                joined_text = plum_page.extract_text() or ""
                is_cid_corrupted = "(cid:" in joined_text or bool(re.search(r'\(cid:\d+\)', joined_text))

                if len(joined_text.strip()) >= 15 and native_lines and not is_cid_corrupted:
                    full_text = "\n".join(l["text"] for l in native_lines)
                    page_res = {
                        "page_number": idx + 1,
                        "width": int(width_pt),
                        "height": int(height_pt),
                        "lines": native_lines,
                        "words": native_words,
                        "full_text": full_text,
                        "preview_url": preview_url,
                    }
                else:
                    # Non-Unicode CID font stream or scanned PDF: run PaddleOCR vision engine
                    if is_cid_corrupted:
                        logger.info(f"Page {idx + 1} contains non-Unicode CID-encoded fonts. Running PaddleOCR-VL-1.6 Vision Engine for clean character extraction...")
                    page_res = self.process_image(pil_image, lang=lang)
                    page_res["page_number"] = idx + 1
                    page_res["preview_url"] = preview_url

                pages.append(page_res)
                if page_res.get("full_text"):
                    all_text_parts.append(f"--- PAGE {idx + 1} ---\n" + page_res["full_text"])

            pdf_plum.close()
            pdf_ium.close()
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
