# -*- coding: utf-8 -*-
"""
Dedicated Parent Documents / Mother Copy (தாய் பத்திரம்) Extractor.
"""

import re
from typing import Dict, Any


class ParentDocsExtractor:
    """Extractor for Parent Documents / Mother Deed / Prior Title Chain."""

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

        doc_no = self._find_value(text, [
            r'(?:ஆவண எண்|document\s*no|doc\.?\s*no)[^\n:]*[:\s]+([^\n]+)',
        ])
        fields["parent_document_number"] = {
            "value": doc_no or "Not Detected",
            "confidence": 0.92 if doc_no else 0.0,
            "label": "தாய் ஆவண எண் (Parent Document Number)",
        }

        year = self._find_value(text, [r'(?:year|வருடம்|dated)[^\n:]*[:\s]+(\d{4})'])
        fields["parent_document_year"] = {
            "value": year or "Not Detected",
            "confidence": 0.90 if year else 0.0,
            "label": "ஆவண வருடம் (Document Year)",
        }

        survey = self._find_value(text, [r'(?:புல\s*எண்|survey)[^\n:]*[:\s]+([^\n]+)'])
        fields["survey_number"] = {
            "value": survey or "Not Detected",
            "confidence": 0.90 if survey else 0.0,
            "label": "புல எண் (Survey Number)",
        }

        extent = self._find_value(text, [r'(?:பரப்பு|extent)[^\n:]*[:\s]+([^\n]+)'])
        fields["extent"] = {
            "value": extent or "Not Detected",
            "confidence": 0.90 if extent else 0.0,
            "label": "பரப்பு (Extent)",
        }

        chain = self._find_value(text, [r'(?:chain|previous|முந்தைய)[^\n:]*[:\s]+([^\n]+)'])
        fields["chain_of_title"] = {
            "value": chain or "Not Detected",
            "confidence": 0.85 if chain else 0.0,
            "label": "உரிமைத் தொடர்ச்சி (Chain of Title - Last 5 Years)",
        }

        return fields
