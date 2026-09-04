# -*- coding: utf-8 -*-
"""
Dedicated Approved Building Plan (கட்டிட அனுமதி வரைபடம்) Extractor.
"""

import re
from typing import Dict, Any


class BuildingPlanExtractor:
    """Extractor for Approved Building Plan."""

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
            ("permit_number", "அனுமதி எண் (Planning Permit No)", [r'(?:permit|sanction)\s*(?:no|number)[^\n:]*[:\s]+([^\n]+)']),
            ("applicant_name", "விண்ணப்பதாரர் (Applicant Name)", [r'(?:applicant|owner)[^\n:]*[:\s]+([^\n]+)']),
            ("plot_details", "மனை விவரம் (Plot Details)", [r'(?:plot|site)[^\n:]*[:\s]+([^\n]+)']),
            ("built_up_area", "கட்டிய பரப்பு (Built-up Area)", [r'(?:built.?up|plinth)[^\n:]*[:\s]+([^\n]+)']),
            ("fsi", "தள பரப்பு குறியீடு (FSI / FAR)", [r'(?:fsi|far|floor\s*area)[^\n:]*[:\s]+([^\n]+)']),
        ]:
            val = self._find_value(text, patterns)
            fields[key] = {"value": val or "Not Detected", "confidence": 0.90 if val else 0.0, "label": label}
        return fields
