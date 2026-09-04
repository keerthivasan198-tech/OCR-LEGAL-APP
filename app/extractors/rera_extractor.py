# -*- coding: utf-8 -*-
"""
Dedicated RERA Approval Certificate (ரேரா பதிவுச் சான்றிதழ்) Extractor.
"""

import re
from typing import Dict, Any


class RERAExtractor:
    """Extractor for TNRERA Registration Certificate."""

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
            ("rera_number", "ரேரா எண் (RERA Registration No)", [r'(?:rera|tnrera)\s*(?:no|number|reg)[^\n:]*[:\s]+([^\n]+)']),
            ("project_name", "திட்டப் பெயர் (Project Name)", [r'(?:project\s*name)[^\n:]*[:\s]+([^\n]+)']),
            ("promoter_name", "ஊக்குவிப்பாளர் (Promoter Name)", [r'(?:promoter|developer|builder)[^\n:]*[:\s]+([^\n]+)']),
            ("validity", "செல்லுபடி (Validity Period)", [r'(?:valid|expiry)[^\n:]*[:\s]+([^\n]+)']),
        ]:
            val = self._find_value(text, patterns)
            fields[key] = {"value": val or "Not Detected", "confidence": 0.90 if val else 0.0, "label": label}
        return fields
