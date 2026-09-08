# -*- coding: utf-8 -*-
"""
Dedicated Sale Deed / Title Deed (கிரையப் பத்திரம்) Extractor.
Extracts:
- Vendor & Purchaser details (with DPDP Masked Aadhaar & PAN)
- History & Previous Owner / Mother Deed Reference
- Schedule of Property (Land, Land with Building, Apartment UDS & Floor)
- Survey Number & Sub-division
- Boundaries (N/S/E/W)
- Land Classification (Wet/Dry/House Site/Nanjai/Punjai)
- Consideration Amount, Document Number, Registration Date, SRO
"""

import re
from typing import Dict, Any, List
from app.translator import format_bilingual_entity
from app.validator import ExtractionValidator


class SaleDeedExtractor:
    """Extractor for Sale Deed / Title Deed."""

    def __init__(self):
        pass

    def _find_value(self, text, patterns, flags=re.IGNORECASE):
        for pat in patterns:
            m = re.search(pat, text, flags)
            if m:
                return m.group(1).strip()
        return None

    def extract(self, text: str) -> Dict[str, Any]:
        fields = {}

        # 1. Executant / Seller / Vendor
        vendor = self._find_value(text, [
            r'(?:விற்பவர்|vendor|seller|executant)[^\n:]*[:\s]+([^\n]+)',
        ])
        fields["vendor_details"] = {
            "value": vendor or "Not Detected",
            "confidence": 0.95 if vendor else 0.0,
            "label": "விற்பவர் விவரம் (Vendor / Executant Details)",
            "box_query": vendor,
        }

        # 2. Purchaser / Buyer / Claimant
        purchaser = self._find_value(text, [
            r'(?:வாங்குபவர்|purchaser|buyer|claimant)[^\n:]*[:\s]+([^\n]+)',
        ])
        fields["purchaser_details"] = {
            "value": purchaser or "Not Detected",
            "confidence": 0.95 if purchaser else 0.0,
            "label": "வாங்குபவர் விவரம் (Purchaser / Claimant Details)",
            "box_query": purchaser,
        }

        # 3. Previous Owner / Mother Deed Reference
        prev_owner = self._find_value(text, [
            r'(?:முந்தைய\s*உரிமையாளர்|previous\s*owner|prior\s*deed|mother\s*deed|parent\s*deed)[^\n]*[:\s]+([^\n]+)',
        ])
        fields["history_previous_owner"] = {
            "value": prev_owner or "Not Detected",
            "confidence": 0.92 if prev_owner else 0.0,
            "label": "முந்தைய உரிமையாளர் (Previous Owner / History)",
            "box_query": prev_owner,
        }

        prev_doc_ref = self._find_value(text, [
            r'(?:முந்தைய\s*ஆவணம்|previous\s*document|prior\s*doc\s*ref(?:erence)?|parent\s*doc\s*no)[^\n]*[:\s]+([^\n]+)',
            r'(?:Doc(?:ument)?\s*No\.?\s*(\d+/\d{4})[^\n]*registered)',
        ])
        fields["previous_doc_reference"] = {
            "value": prev_doc_ref or "Not Detected",
            "confidence": 0.91 if prev_doc_ref else 0.0,
            "label": "முந்தைய ஆவணக் குறிப்பு (Previous Document Reference)",
            "box_query": prev_doc_ref,
        }

        # 4. Schedule of Property Breakdown (Land, Building, Apartment UDS)
        prop_type = "Apartment / Flat (UDS + Built-up)" if any(k in text.lower() for k in ["flat", "apartment", "uds", "குடியிருப்பு"]) else (
            "Land with Building" if any(k in text.lower() for k in ["building", "built up", "house", "வீடு", "கட்டிடம்"]) else "Land / Plot"
        )
        fields["schedule_property_type"] = {
            "value": prop_type,
            "confidence": 0.90,
            "label": "சொத்து விவரம் (Schedule of Property)",
        }

        # 5. Survey Number & Sub-division
        survey = self._find_value(text, [
            r'(?:புல\s*எண்|survey|sy|t\.?s\.?)\s*(?:no\.?|number)?[^\n:]*[:\s]+([0-9A-Za-z/,\s-]+)',
            r'\b(\d{1,4}\s*[-/]\s*\d{1,3}[A-Za-z]?)\b',
        ])
        fields["survey_number"] = {
            "value": survey or "Not Detected",
            "confidence": 0.94 if survey else 0.0,
            "label": "புல எண் (Survey Number / S.No)",
            "box_query": survey,
        }

        # 6. Village / Taluk / District (with Bilingual Layer)
        dist_m = re.search(r'(?:District|மாவட்டம்)\s*[:\s]+([^\n:]+)', text, re.IGNORECASE)
        tal_m = re.search(r'(?:Taluk|வட்டம்)\s*[:\s]+([^\n:]+)', text, re.IGNORECASE)
        vil_m = re.search(r'(?:Village|கிராமம்)\s*[:\s]+([^\n:]+)', text, re.IGNORECASE)

        v_parts = []
        if vil_m:
            v_parts.append(format_bilingual_entity(vil_m.group(1).strip()))
        if tal_m:
            v_parts.append(format_bilingual_entity(tal_m.group(1).strip()))
        if dist_m:
            v_parts.append(format_bilingual_entity(dist_m.group(1).strip()))

        vtd = " / ".join(v_parts) if v_parts else None

        fields["village_taluk_district"] = {
            "value": vtd or "Not Detected",
            "confidence": 0.92 if vtd else 0.0,
            "label": "கிராமம் / வட்டம் / மாவட்டம் (Village / Taluk / District)",
            "box_query": "மாவட்டம் | வட்டம் | கிராமம்",
        }

        # 7. Land Extent
        extent = self._find_value(text, [
            r'(?:பரப்பு|extent|area)[^\n:]*[:\s]+([^\n]+)',
            r'([0-9.]+\s*(?:sq\.?\s*ft|cents?|acres?|grounds?|ஏர்|ares|hectare))',
        ])
        fields["land_extent"] = {
            "value": extent or "Not Detected",
            "confidence": 0.92 if extent else 0.0,
            "label": "பரப்பு (Land Extent)",
            "box_query": extent,
        }

        # 8. Building / UDS / Flat
        uds = self._find_value(text, [
            r'(?:undivided share|uds|பிரிக்கப்படா பங்கு)[^\n:]*[:\s]+([^\n]+)',
        ])
        fields["apartment_uds_floor"] = {
            "value": uds or "Not Detected",
            "confidence": 0.90 if uds else 0.0,
            "label": "பிரிக்கப்படா பங்கு / மாடி (UDS / Built-up / Floor)",
        }

        # 9. Boundaries
        b_match = re.search(r'(?:boundaries|எல்லைகள்)[^\n:]*[:\s]+([^\n]+(?:\n[^\n]+){1,4})', text, re.IGNORECASE)
        boundaries = b_match.group(1).strip() if b_match else None
        fields["boundaries"] = {
            "value": boundaries or "Not Detected",
            "confidence": 0.90 if boundaries else 0.0,
            "label": "எல்லைகள் (Boundaries N/S/E/W)",
        }

        # 10. Land Classification
        classification = self._find_value(text, [
            r'(?:classification|நில வகைப்பாடு|வகை)[^\n:]*[:\s]+([^\n]+)',
            r'\b(நஞ்சை|புஞ்சை|மனை|house\s*site|wet\s*land|dry\s*land|agricultural|residential)\b',
        ])
        fields["land_classification"] = {
            "value": classification or "House Site / Residential",
            "confidence": 0.90 if classification else 0.85,
            "label": "நில வகைப்பாடு (Classification - Wet/Dry/House Site)",
        }

        # 11. SRO Details
        sro = self._find_value(text, [
            r'(?:sub.?registrar|sro|பதிவாளர்|பதிவு அலுவலகம்)[^\n:]*[:\s]+([^\n]+)',
        ])
        fields["sro_details"] = {
            "value": sro or "Not Detected",
            "confidence": 0.92 if sro else 0.0,
            "label": "பதிவாளர் அலுவலகம் (SRO Details)",
            "box_query": sro,
        }

        # 12. Document Number & Registration Date
        doc_no = self._find_value(text, [
            r'(?:ஆவண எண்|document\s*no|doc\.?\s*no)[^\n:]*[:\s]+([^\n]+)',
        ])
        fields["document_number"] = {
            "value": doc_no or "Not Detected",
            "confidence": 0.92 if doc_no else 0.0,
            "label": "ஆவண எண் (Document Number)",
            "box_query": doc_no,
        }

        reg_date = self._find_value(text, [
            r'(?:பதிவு நாள்|registration\s*date|date\s*of\s*reg)[^\n:]*[:\s]+([^\n]+)',
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        ])
        fields["registration_date"] = {
            "value": reg_date or "Not Detected",
            "confidence": 0.90 if reg_date else 0.0,
            "label": "பதிவு நாள் (Registration Date)",
            "box_query": reg_date,
        }

        # 13. Consideration Amount
        amt = self._find_value(text, [
            r'(?:கிரையத்\s*தொகை|consideration|sale\s*value|sale\s*price)[^\n:]*[:\s]+([^\n]+)',
            r'(?:rs\.?|inr|₹)\s*([\d,]+)',
        ])
        fields["consideration_amount"] = {
            "value": amt or "Not Detected",
            "confidence": 0.93 if amt else 0.0,
            "label": "கிரையத் தொகை (Consideration Amount)",
            "box_query": amt,
        }

        # 14. DPDP Masked Aadhaar (Last 4 digits only)
        aadhaar_raw = self._find_value(text, [
            r'(?:aadhaar|ஆதார்)[^\n:]*[:\s]+([^\n]+)',
            r'([X\d]{4}[\s-]*[X\d]{4}[\s-]*\d{4})',
        ])
        masked_aadhaar = ExtractionValidator.enforce_dpdp_masking(aadhaar_raw) if aadhaar_raw else "Not Detected"
        fields["masked_aadhaar"] = {
            "value": masked_aadhaar,
            "confidence": 0.92 if masked_aadhaar != "Not Detected" else 0.0,
            "label": "ஆதார் (DPDP Masked Aadhaar - Last 4 Digits)",
        }

        # 15. PAN Number
        pan = self._find_value(text, [
            r'(?:pan|பான்)[^\n:]*[:\s]+([A-Z]{5}\d{4}[A-Z])',
            r'\b([A-Z]{5}\d{4}[A-Z])\b',
        ])
        fields["pan_number"] = {
            "value": pan or "Not Detected",
            "confidence": 0.94 if pan else 0.0,
            "label": "பான் எண் (PAN Number)",
        }

        return fields
