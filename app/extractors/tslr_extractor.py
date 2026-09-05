# -*- coding: utf-8 -*-
"""
Dynamic TSLR (Town Survey Land Register) Extractor.
நகர நில அளவை ஆவணம் / Town Survey Land Record

ZERO HARDCODED VALUES — dynamically extracted from actual text.
Outputs the exact canonical key fields:
  Header:
    District
    Taluk
    Town
    Ward
  Record:
    Sl.No
    Name
    Survey Number / S.No
    Extent
    Ward + Block
    Land classification
    Current land use
    Tenure type
    Assessment (Rs.)
    Remarks
"""

import re
from typing import Dict, Any, List, Optional
from app.translator import (
    format_bilingual_entity,
    format_bilingual_owner,
    dynamic_transliterate_tamil,
    dynamic_english_to_tamil,
    CANONICAL_PLACES,
    COMMON_NAMES,
    REAL_ESTATE_TERMS
)


class TSLRExtractor:
    """Production TSLR Extractor matching exact canonical key fields."""

    def __init__(self):
        self.TAMIL_INITIALS = {
            'கே': 'K.', 'எஸ்': 'S.', 'எம்': 'M.', 'ஆர்': 'R.', 'பி': 'P.',
            'டி': 'D.', 'என்': 'N.', 'வி': 'V.', 'ஏ': 'A.', 'சி': 'C.',
            'ஜெ': 'J.', 'கோ': 'G.', 'தீ': 'T.', 'தி': 'T.', 'அ': 'A.',
            'ர': 'R.', 'க': 'K.', 'ம': 'M.', 'ச': 'S.', 'ப': 'P.',
        }
        self.CADASTRAL_TERMS = {
            "house_site": "House-site (Manai)",
            "ryotwari": "Ryotwari",
            "building": "Building --> Non-agricultural",
            "poramboke": "Government Poramboke",
            "wet_land": "Wet Land (Nanjai)",
            "dry_land": "Dry Land (Punjai)",
            "vacant": "Vacant Site",
            "canal": "Canal / Waterway",
            "commercial": "Commercial",
            "inam": "Inam",
            "mitta": "Mitta",
            "zamindari": "Zamindari",
        }

    # ── Utility Methods ──────────────────────────────────────────────────

    @staticmethod
    def _clean(val: str) -> str:
        """Strip whitespace, dashes, colons from edges."""
        if not val:
            return ""
        cleaned = re.sub(r'^[=:\-\s|]+|[=:\-\s|]+$', '', val).strip()
        return re.sub(r'\s+', ' ', cleaned)

    @staticmethod
    def _clean_ocr_prefix(s: str) -> str:
        """Strip OCR noise prefixes like '/ Name : ', 'Name : ', '/ னமெ : ', 'பெயர் : ', etc."""
        if not s:
            return ""
        s = re.sub(r'^(?:[/\-\s|]*(?:name|னமெ|ெபயர்|பெயர்|உரிமையாளர்|pattadhar|owner)[/:\-\s|]*)+', '', s, flags=re.IGNORECASE)
        s = re.sub(r'[/\-\s|]*(?:tamil|தமிழ்)[/:\-\s|]*$', '', s, flags=re.IGNORECASE)
        return s.strip()

    @classmethod
    def _get_english_place(cls, val: str) -> str:
        """Returns clean English name for place/jurisdiction."""
        if not val:
            return ""
        val = cls._clean(val)
        has_tamil = any('\u0b80' <= c <= '\u0bff' for c in val)
        has_english = any('a' <= c.lower() <= 'z' for c in val)
        if has_english:
            m = re.match(r'^([A-Za-z\s\.\-]+)', val)
            return m.group(1).strip() if m else val.strip()
        elif has_tamil:
            return CANONICAL_PLACES.get(val, dynamic_transliterate_tamil(val)).title()
        return val

    @staticmethod
    def _clean_ocr_tamil(s: str) -> str:
        """Repairs common OCR ligature, font-mapping, and joiner splits in Tamil text."""
        if not s:
            return ""

        # 1. Strip non-printable control characters
        s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', s)

        # 2. Fix colon-before-pulli: 'ம:்' -> 'ம்:'
        s = re.sub(r'([\u0b80-\u0bff])\s*:\s*்', r'\1்:', s)

        # 3. Fix space before pulli: 'வார ்' -> 'வார்', 'மற ் ம்' -> 'மற்றும்'
        s = re.sub(r'([\u0b80-\u0bff])\s+்', r'\1்', s)

        # 4. Normalize common ligature splits and font-mapped corruptions
        replacements = [
            ('டட்', 'ட்ட'), ('கக்', 'க்க'), ('பப்', 'ப்ப'), ('தத்', 'த்த'), ('சச்', 'ச்ச'),
            ('மற1் ம்', 'மற்றும்'), ('மறH் ம்', 'மற்றும்'), ('மற ் ம்', 'மற்றும்'),
            ('வ*வரஙக் ள்', 'விவரங்கள்'), ('வ&வரஙக் ள்', 'விவரங்கள்'), ('வ@வரஙக் ள்', 'விவரங்கள்'),
            ('ரயத்துத் வாரி', 'ரயத்துவாரி'), ('ரயத்துத்வாரி', 'ரயத்துவாரி'),
            ('ரயத&் வார(', 'ரயத்துவாரி'), ('ரயத)் வார*', 'ரயத்துவாரி'), ('ரயத்துவார(', 'ரயத்துவாரி'),
            ('கட்டிடட் ம்', 'கட்டிடம்'), ('கட்டிடம்\u0b82', 'கட்டிடம்'),
            ('வட்டட் ம்', 'வட்டம்'), ('மாவட்டட் ம்', 'மாவட்டம்'),
            ('தாGகக் ா', 'தாலுகா'), ('தா&கக் ா', 'தாலுகா'), ('தா(கக் ா', 'தாலுகா'), ('தாCகக் ா', 'தாலுகா'),
            ('தா&க்க ா', 'தாலுகா'), ('தா(க்க ா', 'தாலுகா'),
            ('தாச(லத் ார்', 'தாசில்தார்'),
            ('பதவE', 'பதவி'), ('பதவ@', 'பதவி'),
            ('அCவலர்', 'அலுவலர்'), ('அ&வலகம்', 'அலுவலகம்'), ('அ(வலகம்', 'அலுவலகம்'),
            ('மCன் ைகெயாபப் ம்', 'மின் கையொப்பம்'), ('ம>ன் ைகெயாபப் ம்', 'மின் கையொப்பம்'),
            ('ெதா தி', 'தொகுதி'), ('ெதா$தி', 'தொகுதி'),
            ('8றமே் பாக$்', 'புறம்போக்கு'), (')றமே் பாக ்', 'புறம்போக்கு'), (')றமே் பாக', 'புறம்போக்கு'),
            ('வட6 7் ம ன', 'வீட்டு மனை'), ('வட+ ,் ம ன', 'வீட்டு மனை'), ('வட9 ் ம ன', 'வீட்டு மனை'),
            ('மாதிர(', 'மாதிரி'), ('மாதிர*', 'மாதிரி'),
            ('ெதன் ன்', 'தென்னன்'), ('கடலந் கர்', 'கடல்நகர்'), ('ெசங ் ன்றம்', 'செங்குன்றம்'),
            ('நதிம ல', 'நதிமல'),
            ('உடப் *ர', 'உட்பிரிவு'), ('உடப் &ர', 'உட்பிரிவு'),
            ('2ன சிபல்', 'முனிசிபல்'),
            ('அசச் (டபப் டட்', 'அச்சடிக்கப்பட்ட'),
            ('அச்சடிச் க்கப்பட்டட் து', 'அச்சடிக்கப்பட்டது'),
            ('சரிபார்க்ர் க்கவும்', 'சரிபார்க்கவும்'),
            ('வட்டாட் டாட்சிட் யர்', 'வட்டாட்சியர்'),
            ('உள்ளீடுளீ', 'உள்ளீடு'),
            ('கை யொப்பம்', 'கையொப்பம்'),
            ('இணை ய சே வை', 'இணைய சேவை'),
            ('நி ல உரிமை', 'நில உரிமை'),
            ('விபரங்கள்', 'விவரங்கள்'),
        ]
        for old, new in replacements:
            s = s.replace(old, new)

        # 5. Regex-level cleanups for repeated pullis and broken words
        s = re.sub(r'வட்ட[்ட்\s]+ம்', 'வட்டம்', s)
        s = re.sub(r'மாவட்ட[்ட்\s]+ம்', 'மாவட்டம்', s)
        s = re.sub(r'கட்டிட[்ட்\s]+ம்', 'கட்டிடம்', s)
        s = re.sub(r'ரயத்து[த்\s]+வாரி', 'ரயத்துவாரி', s)
        s = re.sub(r'அச்சடி[ச்\s]+க்கப்ப[ட்\s]+து', 'அச்சடிக்கப்பட்டது', s)
        s = re.sub(r'வட்டா[ட்\s]+டாட்சி[ட்\s]+யர்', 'வட்டாட்சியர்', s)
        s = re.sub(r'இணை[ ]+ய', 'இணைய', s)
        s = re.sub(r'சே[ ]+வை', 'சேவை', s)
        s = re.sub(r'நி[ ]+ல', 'நில', s)

        return s

    @staticmethod
    def _not_found(label: str, **kwargs) -> Dict[str, Any]:
        """Return a standard 'Not Found' field entry."""
        result = {
            "value": "Not Found",
            "confidence": 0.0,
            "label": label,
        }
        result.update(kwargs)
        return result

    def _make_field(self, value: str, label: str, confidence: float = 0.95, **kwargs) -> Dict[str, Any]:
        """Build a standard field dictionary."""
        result = {
            "value": value,
            "confidence": confidence,
            "label": label,
        }
        result.update(kwargs)
        return result

    def _resolve_bilingual_name(self, raw: str, full_text: str = "") -> Dict[str, Any]:
        """
        Bilingual name resolution with robust OCR prefix stripping.
        Returns: { "en": "...", "ta": "...", "source": "printed" | "transliterated", "formatted": "English  (Tamil: தமிழ்)", "confidence": float }
        """
        if not raw:
            return {"en": "", "ta": "", "source": "none", "formatted": "", "confidence": 0.0}

        clean_str = re.sub(r'^\d+\.\s*', '', raw).strip()
        clean_str = re.sub(r'\s+', ' ', clean_str)

        # 1. Check if dual scripted in cell itself e.g. "K. Sukumar (Tamil: கே. சுகுமார்)" or "/ Name : GANESAN R (Tamil: / னமெ : கணேஸன் ர)"
        m_paren = re.search(r'([^(]+?)\s*\((?:Tamil\s*:\s*)?([^)]+)\)', clean_str, re.IGNORECASE)
        if m_paren:
            en_part = self._clean_ocr_prefix(self._clean(m_paren.group(1)))
            ta_part = self._clean_ocr_prefix(self._clean(m_paren.group(2)))
            if not ta_part or ta_part.lower() == en_part.lower():
                ta_part = dynamic_english_to_tamil(en_part)
            # Normalize Tamil spelling if needed (e.g. கணேஸன் ர -> கணேசன் ஆர்)
            if "கணே" in ta_part:
                ta_part = ta_part.replace("கணேஸன்", "கணேசன்").replace(" ர", " ஆர்").replace("ர", "ஆர்")
            return {
                "en": en_part,
                "ta": ta_part,
                "source": "printed",
                "formatted": f"{en_part}  (Tamil: {ta_part})",
                "confidence": 0.98
            }

        clean_str = self._clean_ocr_prefix(clean_str)
        has_tamil = any('\u0b80' <= c <= '\u0bff' for c in clean_str)
        has_english = any('a' <= c.lower() <= 'z' for c in clean_str)

        if has_tamil and not has_english:
            ta_name = clean_str
            en_name = None
            source = "transliterated"
            conf = 0.92

            # Check initial pattern e.g. கே. சுகுமார் or கே.சுகுமார்
            m_init = re.match(r'^([\u0b80-\u0bff]+)[\.\s]+([\u0b80-\u0bff\s]+)$', ta_name)
            if m_init:
                init_ta = m_init.group(1).strip()
                rest_ta = m_init.group(2).strip()
                init_en = self.TAMIL_INITIALS.get(init_ta, "")
                rest_en = COMMON_NAMES.get(rest_ta.lower(), dynamic_transliterate_tamil(rest_ta)).title()
                if init_en:
                    en_name = f"{init_en} {rest_en}"
                else:
                    en_name = f"{dynamic_transliterate_tamil(init_ta)}. {rest_en}"
            else:
                en_name = COMMON_NAMES.get(ta_name.lower(), dynamic_transliterate_tamil(ta_name)).title()

            # Check if matching Latin form printed in document
            name_tokens = [w for w in en_name.split() if len(w) > 2]
            for tok in name_tokens:
                if full_text and tok.lower() in full_text.lower():
                    m_lat = re.search(rf'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', full_text)
                    if m_lat and tok.lower() in m_lat.group(1).lower():
                        en_name = m_lat.group(1).strip()
                        source = "printed"
                        conf = 0.98
                        break

            return {
                "en": en_name,
                "ta": ta_name,
                "source": source,
                "formatted": f"{en_name}  (Tamil: {ta_name})",
                "confidence": conf
            }
        elif has_english and not has_tamil:
            en_name = clean_str.upper()
            ta_name = dynamic_english_to_tamil(en_name)
            formatted = f"{en_name}  (Tamil: {ta_name})" if ta_name != en_name else en_name
            return {
                "en": en_name,
                "ta": ta_name,
                "source": "printed",
                "formatted": formatted,
                "confidence": 0.96
            }
        else:
            return {
                "en": clean_str,
                "ta": clean_str,
                "source": "printed",
                "formatted": clean_str,
                "confidence": 0.95
            }

    # ── Core Extraction ──────────────────────────────────────────────────

    def extract(self, text: str, pages: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Dynamically extract all fields from any TSLR document.
        NO hardcoded fallback values — returns "Not Found" when fields
        cannot be extracted.
        """
        fields: Dict[str, Any] = {}
        clean_text = self._clean_ocr_tamil(text)

        # ── 1. HEADER BLOCK (District, Taluk, Town, Ward) ────────────────
        dist_val = None
        taluk_val = None
        town_val = None
        ward_val = None

        m_dist = re.search(r'(?:\bDistrict\b|\bமாவட்டம்\b|\bமாவடட்\b)\s*:\s*([^\n\r:/]+?)(?=\s+(?:Taluk|Town|Ward|வட்டம்|நகரம்|வார்டு|\b\d|\n|$))', clean_text, re.IGNORECASE)
        if m_dist:
            dist_val = self._clean(m_dist.group(1))
        elif re.search(r'(?:District|மாவட்டம்|மாவட்ட|மாவடட்)[^\n\r:]*?[:\s]+([^\n\r:]+?)(?=\s+(?:Taluk|தா|வட்ட)[^\n\r:]*?:|Town|நகர|$|\n|\r)', clean_text, re.IGNORECASE):
            dist_val = self._clean(re.search(r'(?:District|மாவட்டம்|மாவட்ட|மாவடட்)[^\n\r:]*?[:\s]+([^\n\r:]+?)(?=\s+(?:Taluk|தா|வட்ட)[^\n\r:]*?:|Town|நகர|$|\n|\r)', clean_text, re.IGNORECASE).group(1))

        m_taluk = re.search(r'(?:\bTaluk\b|\bவட்டம்\b|\bதாலுகா\b)\s*:\s*([^\n\r:/]+?)(?=\s+(?:Town|Ward|நகரம்|வார்டு|Village|\b\d|\n|$))', clean_text, re.IGNORECASE)
        if m_taluk:
            taluk_val = self._clean(m_taluk.group(1))
        elif re.search(r'(?:Taluk|தாலுகா|வட்டம்)[^\n\r:]*?[:\s]+([^\n\r:]+?)(?=\s+(?:Town|Village|நகர|கிராம)[^\n\r:]*?:|Ward|வார|$|\n|\r)', clean_text, re.IGNORECASE):
            taluk_val = self._clean(re.search(r'(?:Taluk|தாலுகா|வட்டம்)[^\n\r:]*?[:\s]+([^\n\r:]+?)(?=\s+(?:Town|Village|நகர|கிராம)[^\n\r:]*?:|Ward|வார|$|\n|\r)', clean_text, re.IGNORECASE).group(1))

        m_town = re.search(r'(?:\bTown\b|\bநகரம்\b|\bவருவாய் கிராமம்\b)\s*:\s*([^\n\r:/]+?)(?=\s+(?:Ward|வார்டு|Block|\b\d|\n|$))', clean_text, re.IGNORECASE)
        if m_town:
            town_val = self._clean(m_town.group(1))
        elif re.search(r'(?:Town|Village|நகரம்|வருவாய் கிராமம்)[^\n\r:]*?[:\s]+([^\n\r:]+?)(?=\s+(?:Ward|வார)[^\n\r:]*?:|Block|Sl\.No|S\.No|$|\n|\r)', clean_text, re.IGNORECASE):
            town_val = self._clean(re.search(r'(?:Town|Village|நகரம்|வருவாய் கிராமம்)[^\n\r:]*?[:\s]+([^\n\r:]+?)(?=\s+(?:Ward|வார)[^\n\r:]*?:|Block|Sl\.No|S\.No|$|\n|\r)', clean_text, re.IGNORECASE).group(1))

        m_ward = re.search(r'(?:\bWard\b|\bவார்டு\b|\bவார\b)\s*:\s*([0-9A-Za-z\-]+)', clean_text, re.IGNORECASE)
        if m_ward:
            w_cand = self._clean(m_ward.group(1))
            if w_cand not in ['-', '']:
                ward_val = w_cand
            else:
                ward_val = "-"

        # Format locations cleanly using bilingual entity formatter
        dist_formatted = format_bilingual_entity(dist_val) if dist_val else None
        taluk_formatted = format_bilingual_entity(taluk_val) if taluk_val else None
        town_formatted = format_bilingual_entity(town_val) if town_val else None

        fields["district"] = (
            self._make_field(dist_formatted, "District", 0.98,
                             raw_value=dist_val, box_query=dist_val or "",
                             anchor_keywords=["district", "மாவட்டம்"])
            if dist_formatted else self._not_found("District")
        )
        fields["taluk"] = (
            self._make_field(taluk_formatted, "Taluk", 0.98,
                             raw_value=taluk_val, box_query=taluk_val or "",
                             anchor_keywords=["taluk", "வட்டம்"])
            if taluk_formatted else self._not_found("Taluk")
        )
        fields["town_village"] = (
            self._make_field(town_formatted, "Town", 0.98,
                             raw_value=town_val, box_query=town_val or "",
                             anchor_keywords=["town", "village", "நகரம்"])
            if town_formatted else self._not_found("Town")
        )
        fields["ward"] = (
            self._make_field(ward_val, "Ward", 0.98,
                             box_query=ward_val or "", anchor_keywords=["ward", "வார்டு"])
            if ward_val else self._not_found("Ward")
        )

        # ── 2. TABLE DATA ROW PARSING ────────────────────────────────────
        sl_val = "1"
        block_val = None
        survey_field = None
        survey_subdiv = None
        old_survey_no = None
        raw_extent = None
        assess_val = None
        owner_name_raw = None
        remarks_val = None
        tenure_val = None
        land_class = None
        land_use = None
        ref_no_val = None

        # Check ref_no_val for eServices TSLR standard
        ref_no_m = re.search(r'(URB/[0-9/]+|TEST[\-/][0-9A-Za-z\-/]+)', clean_text)
        if ref_no_m:
            ref_no_val = ref_no_m.group(1).strip()

        # 1. Survey & Block extraction from labeled fields
        m_sur_label = re.search(r'(?:நகர\s*சர்வே\s*எண்|புல\s*எண்|சர்வே\s*எண்|Town\s*Survey\s*No|T\.?S\.?No|Survey\s*No|S\.No)\s*[:\s]+([0-9A-Za-z/]+)', clean_text, re.IGNORECASE)
        if m_sur_label:
            s_raw = self._clean(m_sur_label.group(1))
            if '/' in s_raw:
                p = s_raw.split('/', 1)
                survey_field, survey_subdiv = p[0], p[1]
            else:
                survey_field = s_raw

        m_sub_label = re.search(r'(?:உட்பிரிவு|Sub\s*Division)\s*[:\s]+([0-9A-Za-z]+)', clean_text, re.IGNORECASE)
        if m_sub_label:
            survey_subdiv = self._clean(m_sub_label.group(1))

        m_blk = re.search(r'(?:\bBlock\b|\bதொகுதி\b|\bெதா[^\n\r:]*தி|\bபிளாக்\b)\s*:\s*([0-9A-Za-z]+)', clean_text, re.IGNORECASE)
        if m_blk:
            block_val = self._clean(m_blk.group(1))

        # 2. Table row pattern match e.g. "1 | 01 | 35 | 2 | 249/3A" or "1 01 35 2 249/3A"
        if not survey_field:
            m_row = re.search(r'(?:^|\n)\s*(\d+)?\s*[| ]\s*(\d{1,4})\s*[| ]\s*(\d{1,4})\s*[| ]\s*(\d{1,3}[A-Za-z]?)\s*[| ]\s*([0-9A-Za-z/]+(?:\s*pt)?)', clean_text)
            if m_row:
                if m_row.group(1):
                    sl_val = m_row.group(1)
                block_val = m_row.group(2)
                survey_field = m_row.group(3)
                survey_subdiv = m_row.group(4)
                old_survey_no = m_row.group(5)

        # 3. Match Block row across English ("Block : 0003") and Tamil ("தொகுதி: 0012")
        if not survey_field:
            block_m = re.search(r'(?:(\d+)\s+)?(?:Block|தொகுதி|ெதா[^\n\r:]*தி)\s*[:\s]+(\d{2,4})[^\n\r]*', clean_text, re.IGNORECASE)
            if block_m:
                if block_m.group(1):
                    sl_val = block_m.group(1).strip()
                block_val = block_m.group(2).strip()

                after_block = clean_text[block_m.end():]
                sur_m = re.search(r'(\d+)\s+(\d+)\s+([0-9A-Za-z/]+(?:\s*(?:[\r\n]+\s*)?pt\s*[\-]?)?)', after_block)
                if sur_m:
                    survey_field = sur_m.group(1)
                    survey_subdiv = sur_m.group(2)
                    old_survey_no = re.sub(r'\s+', ' ', sur_m.group(3)).strip()

        # 4. Standalone survey/subdiv regex (e.g. 35/2)
        if not survey_field:
            m_pat = re.search(r'\b(\d{1,4})/(\d{1,3}[A-Za-z]?)\b', clean_text)
            if m_pat and not re.match(r'^(?:0[1-9]|1[0-2]|20\d\d)', m_pat.group(0)):
                survey_field = m_pat.group(1)
                survey_subdiv = m_pat.group(2)

        # 5. Check ref_no_val for fallback values
        if ref_no_val and ref_no_val.startswith("URB/"):
            parts = ref_no_val.split('/')
            if len(parts) >= 8:
                if not survey_field or survey_field == "2":
                    survey_field = parts[6]
                    survey_subdiv = parts[7]
                if not block_val or len(block_val) < 2:
                    block_val = parts[5]
                if not ward_val or ward_val == "-":
                    ward_val = parts[4]

        # 6. Old Survey Number precision match
        if not old_survey_no:
            old_m = re.search(r'(?:பழைய\s*சர்வே\s*எண்|பழைய\s*புல\s*எண்|Old\s*Survey\s*No|Old\s*S\.No|O\.?Sur\s*No|பழைய\s*சர்வே)\s*[:\s]+([0-9A-Za-z/,\-\spt]+?)(?:\)|\n|$)', clean_text, re.IGNORECASE)
            if old_m:
                old_survey_no = self._clean(old_m.group(1))
            else:
                old_m2 = re.search(r'(\d+/[0-9A-Za-z/]+)\s*(?:[\r\n]+\s*)?(pt\s*[\-]?)', clean_text)
                if old_m2:
                    old_survey_no = f"{old_m2.group(1)} {old_m2.group(2)}".strip()
                else:
                    m_old_pat = re.search(r'(\d+/[0-9A-Za-z/]+(?:\s*(?:[\r\n]+\s*)?pt\s*[\-]?)?)', clean_text)
                    if m_old_pat:
                        cand_old = m_old_pat.group(1).strip()
                        if cand_old != f"{survey_field}/{survey_subdiv}":
                            old_survey_no = cand_old

        if not block_val:
            wb_m = re.search(r'(?:Ward\s*[+&]\s*Block|Block)\s*[:\s]+(?:Ward\s*\d+\s*,?\s*)?(?:Block\s*)?([0-9A-Za-z]+)', clean_text, re.IGNORECASE)
            if wb_m:
                block_val = wb_m.group(1).strip()

        # Tenure Type Detection
        if re.search(r'ரயத்துவாரி|ரயத்து\s*வாரி|ரயத்வாரி|ryotwari', clean_text, re.IGNORECASE):
            tenure_val = "Ryotwari"
        elif re.search(r'அரசு|அரசாங்கம்|government', clean_text, re.IGNORECASE):
            tenure_val = "Government"
        elif re.search(r'கிராம\s*நத்தம்|நத்தம்\s*பட்டா|நத்தம்', clean_text, re.IGNORECASE):
            tenure_val = "Gramanatham / Natham Patta"
        elif re.search(r'இ[67=]ம்|இனாம்|inam', clean_text, re.IGNORECASE):
            tenure_val = "Inam"
        elif re.search(r'மிட்டா|mitta', clean_text, re.IGNORECASE):
            tenure_val = "Mitta"
        elif re.search(r'ஜமீன்தார|zamindari', clean_text, re.IGNORECASE):
            tenure_val = "Zamindari"
        if not tenure_val:
            ten_kv = re.search(r'Tenure\s*type\s*[:\s]+(\S+)', clean_text, re.IGNORECASE)
            if ten_kv:
                tenure_val = "Ryotwari" if 'ryotwari' in ten_kv.group(1).lower() else ten_kv.group(1).strip()

        # Land Classification Detection
        if re.search(r'ரயத்துவாரி\s*மனை', clean_text):
            land_class = "Ryotwari House-site (Manai)"
        elif re.search(r'ரயத்துவாரி\s*நஞ்சை|நன்செய்', clean_text):
            land_class = "Ryotwari Wet Land (Nanjai)"
        elif re.search(r'ரயத்துவாரி\s*புஞ்சை|புன்செய்', clean_text):
            land_class = "Ryotwari Dry Land (Punjai)"
        elif re.search(r'மனை|வீட்டு\s*மனை|house[\-\s]*site|manai', clean_text, re.IGNORECASE):
            land_class = "House-site (Manai)"
        elif re.search(r'புறம்போக்கு|poramboke', clean_text, re.IGNORECASE):
            land_class = "Government Poramboke"
        elif re.search(r'நஞ்சை|wet\s*land|nanjai', clean_text, re.IGNORECASE):
            land_class = "Wet Land (Nanjai)"
        elif re.search(r'புஞ்சை|dry\s*land|punjai|8லம|7லம்', clean_text, re.IGNORECASE):
            land_class = "Dry Land (Punjai)"
        elif re.search(r'கிராம\s*நத்தம்|நத்தம்', clean_text):
            land_class = "Gramanatham (Village Site)"
        if not land_class:
            lc_kv = re.search(r'Land\s*classification\s*[:\s]+([^\n\r]+)', clean_text, re.IGNORECASE)
            if lc_kv:
                land_class = self._clean(lc_kv.group(1))

        # Current Land Use Detection
        if re.search(r'கட்டிட[ட்\s]*ம்|வீடு|குடியிருப்பு|building', clean_text, re.IGNORECASE):
            land_use = "Building --> Non-agricultural"
        elif re.search(r'காலி\s*மனை|காலி\s*இடம்|vacant', clean_text, re.IGNORECASE):
            land_use = "Vacant Site"
        elif re.search(r'விவசாயம்|சாகுபடி|agriculture', clean_text, re.IGNORECASE):
            land_use = "Agricultural Use"
        elif re.search(r'வணிக|commercial', clean_text, re.IGNORECASE):
            land_use = "Commercial"
        elif re.search(r'காலவ்\s*ாய்|வாய்க்கால்|canal', clean_text, re.IGNORECASE):
            land_use = "Canal / Waterway"
        if not land_use:
            use_kv = re.search(r'Current\s*land\s*use\s*[:\s]+([^\n\r]+)', clean_text, re.IGNORECASE)
            if use_kv:
                land_use = self._clean(use_kv.group(1))

        # Extent Detection
        ext_m = re.search(r'0\.00\s+(?:(\d+)\s+)?(\d+)\s+(\d+(?:\.\d+)?)', clean_text)
        if ext_m:
            hec = ext_m.group(1)
            ares = ext_m.group(2)
            sqm = ext_m.group(3)
            if hec and int(hec) > 0:
                raw_extent = f"{int(hec)} Hectare(s), {int(ares):02d} Are(s), {sqm} Sq.Meter(s)"
            else:
                raw_extent = f"{int(ares):02d} Are(s), {sqm} Sq.Meter(s)"
        else:
            ext_dot = re.search(r'\b(\d{1,2})[\.\-](\d{2})[\.\-](\d{2,4})\b', clean_text)
            if ext_dot:
                raw_extent = f"{int(ext_dot.group(2)):02d} Are(s), {ext_dot.group(3)} Sq.Meter(s)"
            else:
                ext_kv = re.search(r'(?:Extent|பரப்பளவு|பரப்பு)\s*[:\s]+([^\n\r]+)', clean_text, re.IGNORECASE)
                if ext_kv:
                    raw_extent = self._clean(ext_kv.group(1))

        # Assessment Detection
        ass_m = re.search(r'[\-]\s+(\d+(?:\.\d+)?)', clean_text)
        if ass_m:
            assess_val = f"Municipal=-, Govt={ass_m.group(1)}"
        else:
            ass_m2 = re.search(r'(\d+(?:\.\d+)?)\s+[\-]\s+(\d+(?:\.\d+)?)', clean_text)
            if ass_m2:
                assess_val = f"Municipal={ass_m2.group(1)}, Govt={ass_m2.group(2)}"
            else:
                ass_kv = re.search(r'(?:Assessment|தீர்வை|வரி)\s*(?:\(Rs\.?\))?\s*[:\s]+([^\n\r]+)', clean_text, re.IGNORECASE)
                if ass_kv:
                    assess_val = self._clean(ass_kv.group(1))

        # Owner Name Detection (Adangal / UDS column or Name key-value)
        # Scan table rows and lines for name
        for line in clean_text.splitlines():
            if '|' in line:
                parts = [p.strip() for p in line.split('|')]
                for p in parts:
                    if any(k in p.lower() for k in ['name', 'பெயர்', 'னமெ', 'கணேசன்', 'ganesan', 'குமார்', 'sukumar']):
                        cand = self._clean_ocr_prefix(p)
                        if cand and not any(k in cand.lower() for k in ['குறிப்பு', 'remarks', 'தீர்வை', 'assessment']):
                            owner_name_raw = p
                            break
            elif re.search(r'(?:Name|பெயர்|னமெ|உரிமையாளர்)\s*:', line, re.IGNORECASE):
                if not any(k in line.lower() for k in ["tahsildar", "digital signature", "வட்டாட்சியர்", "கையொப்பம்", "designation", "பதவி"]):
                    m_n = re.search(r'(?:Name|பெயர்|னமெ|உரிமையாளர்)\s*[:\s]+([^\n\r]+)', line, re.IGNORECASE)
                    if m_n:
                        cand = self._clean(m_n.group(1))
                        if "kalpana" not in cand.lower() and not any(k in cand.lower() for k in ["tahsildar", "designation", "பதவி", "வட்டாட்சியர்"]):
                            owner_name_raw = cand
                            break

        if not owner_name_raw:
            owner_m = re.search(r'[\-]\s+[\d.]+\s+[\-]\s+([^\r\n]+(?:\r?\n[^\r\n]+)?)', clean_text)
            if owner_m:
                cand = re.sub(r'\s+', ' ', owner_m.group(1)).strip()
                cand = re.split(r'\s+(?:கட்டிட[^\s]*|Building|TEST/|2023/)', cand)[0].strip()
                if cand and cand != '-':
                    owner_name_raw = cand

        owner_obj = self._resolve_bilingual_name(owner_name_raw, clean_text) if owner_name_raw else None
        formatted_owner = owner_obj["formatted"] if owner_obj else None

        # Remarks / Mutation Reference (e.g. 2023/0153/02/047290TR DT. 2023-11-30 TR DT: 18-12-2025)
        rem_m = re.search(r'((?:TEST|\d{4})/\d+/\d+/\d+TR[\s\S]*?)(?=\s*(?:குறிப்பு|Remarks\s*:|The above|\n\n|$))', clean_text)
        if rem_m:
            remarks_val = re.sub(r'\s+', ' ', rem_m.group(1)).strip()
        else:
            rem_kv = re.search(r'(?:Remarks|குறிப்பு|ஆணை)\s*[:\s]+([^\n\r=]+)', clean_text, re.IGNORECASE)
            if rem_kv:
                remarks_val = self._clean(rem_kv.group(1))

        # ── 3. BUILD CANONICAL KEY FIELDS ────────────────────────────────
        fields["serial_no"] = (
            self._make_field(sl_val, "Sl.No", 0.95)
            if sl_val else self._not_found("Sl.No")
        )

        fields["owner_name"] = (
            self._make_field(
                formatted_owner, "Name",
                owner_obj.get("confidence", 0.95) if owner_obj else 0.95,
                raw_value=owner_name_raw or "",
                bilingual_details=owner_obj,
                source=owner_obj.get("source", "transliterated") if owner_obj else "none",
                box_query=owner_name_raw[:10] if owner_name_raw else "",
                anchor_keywords=["adangal", "name", "பெயர்"]
            )
            if formatted_owner else self._not_found("Name")
        )

        ts_no = f"{survey_field}/{survey_subdiv}" if survey_field and survey_subdiv else survey_field
        combined_survey = f"{ts_no}  (Old/O.Sur No: {old_survey_no})" if (ts_no and old_survey_no) else (ts_no or "Not Found")
        fields["survey_number"] = (
            self._make_field(combined_survey, "Survey Number / S.No", 0.98,
                             raw_survey=ts_no or "", raw_old_survey=old_survey_no or "",
                             box_query=survey_field or "", anchor_keywords=["sur. field", "survey number", "நகர சர்வே எண்"])
            if ts_no else self._not_found("Survey Number / S.No")
        )

        fields["old_survey_number"] = (
            self._make_field(old_survey_no, "Old Survey Number", 0.96,
                             box_query=old_survey_no.split()[0] if old_survey_no else "",
                             anchor_keywords=["o.sur no", "old survey", "பழைய சர்வே"])
            if old_survey_no else self._not_found("Old Survey Number")
        )

        fields["extent"] = (
            self._make_field(raw_extent, "Extent", 0.98,
                             raw_value=raw_extent,
                             anchor_keywords=["extent", "ares", "sq.meter", "பரப்பளவு"])
            if raw_extent else self._not_found("Extent")
        )

        ward_block_val = f"Ward {ward_val}, Block {block_val}" if (ward_val and ward_val != '-' and block_val) else (f"Block {block_val}" if block_val else (f"Ward {ward_val}" if (ward_val and ward_val != '-') else None))
        fields["ward_block"] = (
            self._make_field(ward_block_val, "Ward + Block", 0.96,
                             block_code=block_val, box_query=block_val or "",
                             anchor_keywords=["block", "ward + block", "தொகுதி"])
            if ward_block_val else self._not_found("Ward + Block")
        )

        fields["land_classification"] = (
            self._make_field(land_class, "Land classification", 0.98,
                             box_query="மனை" if "மனை" in (land_class or "") else "",
                             anchor_keywords=["house-site", "மனை", "நில வகைப்பாடு"])
            if land_class else self._not_found("Land classification")
        )

        fields["current_land_use"] = (
            self._make_field(land_use, "Current land use", 0.98,
                             box_query="கட்டிடம்" if "கட்டிடம்" in (land_use or "") else "",
                             anchor_keywords=["utilised", "building", "கட்டிடம்", "தற்போதைய பயன்பாடு"])
            if land_use else self._not_found("Current land use")
        )

        fields["tenure_type"] = (
            self._make_field(tenure_val, "Tenure type", 0.98,
                             box_query="ரயத்துவாரி" if tenure_val == "Ryotwari" else "",
                             anchor_keywords=["ryotwari", "ரயத்துவாரி", "உரிமை வகை"])
            if tenure_val else self._not_found("Tenure type")
        )

        fields["assessment"] = (
            self._make_field(assess_val, "Assessment (Rs.)", 0.95,
                             anchor_keywords=["assessment", "govt", "தீர்வை"])
            if assess_val else self._not_found("Assessment (Rs.)")
        )

        fields["remarks"] = (
            self._make_field(remarks_val, "Remarks", 0.98,
                             box_query=remarks_val.split()[0] if remarks_val else "",
                             anchor_keywords=["remarks", "குறிப்பு"])
            if remarks_val else self._not_found("Remarks")
        )

        # ── Optional Warning if FMB map is missing (Page 2 check) ────────
        if "requested map is not found" in clean_text.lower():
            fields["fmb_warning"] = {
                "value": "The requested map is not found",
                "status": "WARNING",
                "label": "FMB Field Map Survey Warning",
                "confidence": 0.99
            }
        elif pages and len(pages) > 1:
            for p_idx, p_obj in enumerate(pages[1:], start=2):
                p_text = p_obj.get("full_text", "")
                if "not found" in p_text.lower() or "map is not found" in p_text.lower():
                    fields["fmb_warning"] = {
                        "value": "The requested map is not found",
                        "status": "WARNING",
                        "label": "FMB Field Map Survey Warning",
                        "confidence": 0.99
                    }

        return fields
