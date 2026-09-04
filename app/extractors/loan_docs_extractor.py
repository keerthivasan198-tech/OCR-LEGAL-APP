# -*- coding: utf-8 -*-
"""
Dedicated Loan Documents / Mortgage Deed (கடன் மற்றும் அடமான ஆவணங்கள்) Extractor.
"""

import re
from typing import Dict, Any


class LoanDocsExtractor:
    """Extractor for Loan Documents / MODT / Mortgage."""

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
            ("loan_account", "கடன் கணக்கு எண் (Loan Account No)", [r'(?:loan\s*(?:account|a/c)|கடன்)[^\n:]*[:\s]+([^\n]+)']),
            ("bank_name", "வங்கி பெயர் (Bank / Lender Name)", [r'(?:bank|lender|financial)[^\n:]*[:\s]+([^\n]+)']),
            ("mortgage_type", "அடமான வகை (Mortgage Type - MODT/Equitable)", [r'(?:mortgage|modt|equitable)[^\n:]*[:\s]+([^\n]+)']),
            ("loan_amount", "கடன் தொகை (Loan / Sanctioned Amount)", [r'(?:loan\s*amount|sanctioned|disbursed)[^\n:]*[:\s]+([^\n]+)']),
            ("property_description", "சொத்து விவரம் (Property Description)", [r'(?:property|schedule|description)[^\n:]*[:\s]+([^\n]+)']),
        ]:
            val = self._find_value(text, patterns)
            fields[key] = {"value": val or "Not Detected", "confidence": 0.90 if val else 0.0, "label": label}
        return fields
