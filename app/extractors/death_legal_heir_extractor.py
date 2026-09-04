# -*- coding: utf-8 -*-
"""
Dedicated Death Certificate & Legal Heir Certificate (இறப்பு மற்றும் வாரிசுச் சான்றிதழ்) Extractor.
"""

import re
from typing import Dict, Any


class DeathLegalHeirExtractor:
    """Extractor for Death Certificate and Legal Heir Certificate (Varisu)."""

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

        # Death Certificate fields
        deceased = self._find_value(text, [r'(?:இறந்தவர்|deceased|name of deceased)[^\n:]*[:\s]+([^\n]+)'])
        fields["deceased_name"] = {
            "value": deceased or "Not Detected",
            "confidence": 0.92 if deceased else 0.0,
            "label": "இறந்தவர் பெயர் (Deceased Name)",
        }

        dod = self._find_value(text, [
            r'(?:இறப்பு நாள்|date of death)[^\n:]*[:\s]+([^\n]+)',
            r'(?:death)[^\n]*(\d{2}[-/.]\d{2}[-/.]\d{4})',
        ])
        fields["date_of_death"] = {
            "value": dod or "Not Detected",
            "confidence": 0.92 if dod else 0.0,
            "label": "இறப்பு நாள் (Date of Death)",
        }

        # Legal Heir fields
        heir_list = self._find_value(text, [r'(?:வாரிசுகள்|legal\s*heirs?|heirs)[^\n:]*[:\s]+([^\n]+)'])
        fields["legal_heirs"] = {
            "value": heir_list or "Not Detected",
            "confidence": 0.90 if heir_list else 0.0,
            "label": "வாரிசுகள் பட்டியல் (Legal Heirs List)",
        }

        issuing = self._find_value(text, [r'(?:tahsildar|வட்டாட்சியர்|taluk office)[^\n:]*[:\s]+([^\n]+)'])
        fields["issuing_authority"] = {
            "value": issuing or "Not Detected",
            "confidence": 0.90 if issuing else 0.0,
            "label": "வழங்கிய அலுவலகம் (Issuing Authority - Tahsildar)",
        }

        # Patta Mutation status
        fields["patta_mutation_status"] = {
            "value": "Not Detected",
            "confidence": 0.0,
            "label": "பட்டா மாற்றம் (Patta Mutation Status - TN Act 1983)",
        }

        return fields
