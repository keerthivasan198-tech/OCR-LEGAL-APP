# -*- coding: utf-8 -*-
"""
Dedicated Property Water Tax and EB Receipts (சொத்து வரி மற்றும் மின் கட்டண ரசீது) Extractor.
"""

import re
from typing import Dict, Any


class TaxReceiptsExtractor:
    """Extractor for Property Tax, Water Tax, and TANGEDCO EB Receipts."""

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
            ("tax_receipt_no", "வரி ரசீது எண் (Tax Receipt No)", [r'(?:receipt|bill)\s*(?:no|number)[^\n:]*[:\s]+([^\n]+)']),
            ("consumer_no", "நுகர்வோர் எண் (Consumer / Service No)", [r'(?:consumer|service)\s*(?:no|number)[^\n:]*[:\s]+([^\n]+)']),
            ("property_id", "சொத்து அடையாள எண் (Property ID / Assessment No)", [r'(?:assessment|property\s*id)[^\n:]*[:\s]+([^\n]+)']),
            ("amount_paid", "செலுத்திய தொகை (Amount Paid)", [r'(?:amount|paid|Rs\.?|₹)[^\n:]*[:\s]+([^\n]+)']),
            ("period", "காலம் (Period Covered)", [r'(?:period|year|half)[^\n:]*[:\s]+([^\n]+)']),
        ]:
            val = self._find_value(text, patterns)
            fields[key] = {"value": val or "Not Detected", "confidence": 0.90 if val else 0.0, "label": label}
        return fields
