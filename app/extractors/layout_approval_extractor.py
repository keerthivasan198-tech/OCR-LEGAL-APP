# -*- coding: utf-8 -*-
"""
Dedicated Approved Layout CMDA / DTCP (அங்கீகரிக்கப்பட்ட மனைப்பிரிவு வரைபடம்) Extractor.
"""

import re
from typing import Dict, Any


class LayoutApprovalExtractor:
    """Extractor for Approved Layout (CMDA / DTCP)."""

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
        for key, label, patterns in [
            ("approval_no", "அனுமதி எண் (Layout Approval No)", [r'(?:approval|ppd|lo)\s*(?:no|number)[^\n:]*[:\s]+([^\n]+)']),
            ("authority", "அங்கீகார அமைப்பு (Approving Authority - CMDA/DTCP)", [r'(?:cmda|dtcp|authority)[^\n:]*[:\s]+([^\n]+)']),
            ("layout_name", "மனைப்பிரிவு பெயர் (Layout Name)", [r'(?:layout|subdivision)[^\n:]*[:\s]+([^\n]+)']),
            ("osr_details", "திறந்தவெளி ஒதுக்கீடு (OSR Details)", [r'(?:osr|open\s*space)[^\n:]*[:\s]+([^\n]+)']),
        ]:
            val = self._find_value(text, patterns)
            fields[key] = {"value": val or "Not Detected", "confidence": 0.90 if val else 0.0, "label": label}
        return fields
