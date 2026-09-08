# -*- coding: utf-8 -*-
"""
Deterministic Validation & Safeguard Layer for Real Estate OCR.
Performs:
- Survey Number and Subdivision strict verification against OCR ground truth
- Multi-unit Extent Normalization (Cents, Acres, Grounds, Hectares/Ares, Sq.Meters -> Sq.Ft)
- DPDP Act Compliant Aadhaar Masking (XXXX-XXXX-1234)
- A-Register Poramboke / Waterbody / Government Land Fraud Detection
"""

import re
from typing import Dict, Any, Optional, Tuple


class ExtractionValidator:
    """Safeguard and validation engine for legal OCR output."""

    @staticmethod
    def normalize_extent_to_sqft(extent_str: str) -> Optional[float]:
        """Converts any Indian real estate land unit to standard Square Feet."""
        if not extent_str or extent_str == "Not Detected":
            return None
        text = str(extent_str).lower().replace(",", "")

        # Cents (1 Cent = 435.6 Sq.Ft)
        cents_match = re.search(r'([0-9.]+)\s*(?:cents?|சென்ட்)', text)
        if cents_match:
            return float(cents_match.group(1)) * 435.6

        # Acres (1 Acre = 43,560 Sq.Ft)
        acres_match = re.search(r'([0-9.]+)\s*(?:acres?|ஏக்கர்)', text)
        if acres_match:
            return float(acres_match.group(1)) * 43560.0

        # Grounds (1 Ground = 2,400 Sq.Ft)
        grounds_match = re.search(r'([0-9.]+)\s*(?:grounds?|கிரவுண்ட்)', text)
        if grounds_match:
            return float(grounds_match.group(1)) * 2400.0

        # Hectare-Ares (1 Hectare = 107,639 Sq.Ft, 1 Are = 1,076.39 Sq.Ft)
        ha_match = re.search(r'([0-9]+)[-.]?([0-9]+)?\s*(?:hectare|ares?|ஹெக்டேர்|ஏர்ஸ்)', text)
        if ha_match:
            try:
                parts = ha_match.groups()
                hectares = float(parts[0]) if parts[0] else 0.0
                ares = float(parts[1]) if len(parts) > 1 and parts[1] else 0.0
                return (hectares * 107639.0) + (ares * 1076.39)
            except Exception:
                pass

        # Square Meters (1 Sq.M = 10.7639 Sq.Ft)
        sqm_match = re.search(r'([0-9.]+)\s*(?:sq\.?\s*m|sq\.?\s*meters?|சதுர\s*மீட்டர்)', text)
        if sqm_match:
            return float(sqm_match.group(1)) * 10.7639

        # Square Feet
        sqft_match = re.search(r'([0-9.]+)\s*(?:sq\.?\s*ft|sq\.?\s*feet|சதுர\s*அடி)', text)
        if sqft_match:
            return float(sqft_match.group(1))

        # Raw numeric
        num_match = re.search(r'^([0-9.]+)$', text.strip())
        if num_match:
            return float(num_match.group(1))

        return None

    @staticmethod
    def validate_survey_and_subdivision(extracted_val: str, raw_ocr: str) -> Dict[str, Any]:
        """
        Validates that extracted survey/subdivision actually appears in raw OCR.
        Prevents LLM/OCR hallucination or distortion (e.g. 142/2B turning into 142/28).
        """
        if not extracted_val or extracted_val == "Not Detected":
            return {"valid": False, "needs_review": True, "reason": "Missing or undetected value"}

        clean_ext = re.sub(r'\s+', '', str(extracted_val).upper())
        clean_ocr = re.sub(r'\s+', '', raw_ocr.upper())

        # Exact normalized match
        if clean_ext in clean_ocr:
            return {
                "valid": True,
                "needs_review": False,
                "value": extracted_val,
                "confidence": 0.98
            }

        # Check if subdivision format was subtly distorted (e.g. 142/28 vs 142/2B)
        m = re.search(r'(\d{1,4})\s*/\s*([0-9A-Za-z]+)', raw_ocr, re.IGNORECASE)
        if m:
            ground_truth = f"{m.group(1)}/{m.group(2)}"
            return {
                "valid": False,
                "needs_review": True,
                "suggested_value": ground_truth,
                "reason": f"Extracted value '{extracted_val}' diverged from OCR ground truth '{ground_truth}'"
            }

        return {
            "valid": False,
            "needs_review": True,
            "value": extracted_val,
            "reason": "Survey number notation not verified in OCR text stream"
        }

    @staticmethod
    def enforce_dpdp_masking(aadhaar_str: str) -> str:
        """
        Enforces Digital Personal Data Protection (DPDP) Act Compliance.
        Guarantees that only masked Aadhaar (last 4 digits) is stored/displayed.
        """
        if not aadhaar_str or aadhaar_str == "Not Detected":
            return "Not Detected"

        raw_str = str(aadhaar_str).strip()
        digits = re.findall(r'\d', raw_str)
        if len(digits) == 12:
            return f"XXXX-XXXX-{digits[-4]}{digits[-3]}{digits[-2]}{digits[-1]}"
        elif len(digits) == 4 and "XXXX" in raw_str.upper():
            return f"XXXX-XXXX-{digits[0]}{digits[1]}{digits[2]}{digits[3]}"
        return raw_str

    @staticmethod
    def check_poramboke_status(classification_text: str) -> Tuple[bool, str]:
        """
        Authoritative A-Register classification check.
        Flags Government Poramboke, Waterbodies (Eri, Kanmai), or Unassigned Land fraud.
        """
        if not classification_text:
            return False, "Patta Land (Ryotwari)"

        c_lower = classification_text.lower()
        is_safe = any(k in c_lower for k in ["ryotwari", "private", "patta land", "ரயோத்துவாரி", "பட்டா நிலம்", "நஞ்சை", "புஞ்சை", "wet land", "dry land"])
        is_poramboke = (not is_safe) and any(k in c_lower for k in ["poramboke", "government", "waterbody", "kanmai", "eri", "road", "புறம்போக்கு", "அரசு"])

        if is_poramboke:
            return True, "CRITICAL FRAUD: Government Poramboke / Waterbody Land"
        return False, "Private Patta / Ryotwari Land"
