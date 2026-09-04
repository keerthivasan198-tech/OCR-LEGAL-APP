# -*- coding: utf-8 -*-
"""
Bilingual Translation Layer for Real Estate OCR.
Primary engine: IndicTrans2 (AI4Bharat) — true neural Tamil ↔ English translation.
Fallback engine: Phonetic transliteration (rule-based, no model required).

Standard Output Format:  English Name (Tamil Name)
Examples:
    - Village: Kallidaikurichi (கள்ளிடைக்குறிச்சி)
    - District: Villupuram (விழுப்புரம்)
    - Taluk: Ambasamudram (அம்பாசமுத்திரம்)
    - Owner: Elangovan (S/o Nagappan) (நாகப்பன் மகன் இளங்கோவன்)
"""

import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# IndicTrans2 engine — imported lazily (None until first use)
try:
    from app.indic_translator import translate_to_tamil, translate_to_english, is_available as _it2_available
    _INDICTRANS2_IMPORTED = True
except ImportError:
    _INDICTRANS2_IMPORTED = False
    def translate_to_tamil(text): return None   # type: ignore
    def translate_to_english(text): return None  # type: ignore
    def _it2_available(): return False            # type: ignore

# Independent Tamil vowels
TAMIL_VOWELS = {
    'அ': 'a', 'ஆ': 'aa', 'இ': 'i', 'ஈ': 'ee', 'உ': 'u', 'ஊ': 'oo',
    'எ': 'e', 'ஏ': 'e', 'ஐ': 'ai', 'ஒ': 'o', 'ஓ': 'o', 'ஔ': 'au',
}

# Consonants: Unvoiced (default) and Voiced (intervocalic / post-nasal)
TAMIL_CONSONANTS = {
    'க': ('k', 'g'), 'ங': ('ng', 'ng'), 'ச': ('s', 's'), 'ஞ': ('ny', 'ny'),
    'ட': ('t', 'd'), 'ண': ('n', 'n'), 'த': ('th', 'th'), 'ந': ('n', 'n'),
    'ப': ('p', 'b'), 'ம': ('m', 'm'), 'ய': ('y', 'y'), 'ர': ('r', 'r'),
    'ல': ('l', 'l'), 'வ': ('v', 'v'), 'ழ': ('zh', 'zh'), 'ள': ('l', 'l'),
    'ற': ('r', 'r'), 'ன': ('n', 'n'), 'ஜ': ('j', 'j'), 'ஷ': ('sh', 'sh'),
    'ஸ': ('s', 's'), 'ஹ': ('h', 'h'), 'க்ஷ': ('ksh', 'ksh')
}

# Vowel diacritics / signs
TAMIL_VOWEL_SIGNS = {
    'ா': 'aa', 'ி': 'i', 'ீ': 'ee', 'ு': 'u', 'ூ': 'oo',
    'ெ': 'e', 'ே': 'e', 'ை': 'ai', 'ொ': 'o', 'ோ': 'o', 'ௌ': 'au',
    '்': ''  # Virama removes inherent vowel
}

# Canonical dictionary of Tamil Nadu revenue locations for official government spellings
CANONICAL_PLACES = {
    # Districts
    "திருவாரூர்": "Thiruvarur", "thiruvarur": "திருவாரூர்",
    "திருவாளூர்": "Thiruvarur", "திருவாளுர்": "Thiruvarur", "திடுவாதர்": "Thiruvarur",
    "விழுப்புரம்": "Villupuram", "villupuram": "விழுப்புரம்",
    "தஞ்சாவூர்": "Thanjavur", "thanjavur": "தஞ்சாவூர்",
    "ஈரோடு": "Erode", "erode": "ஈரோடு",
    "சேலம்": "Salem", "salem": "சேலம்", "சலம்": "Salem",
    "மதுரை": "Madurai", "madurai": "மதுரை",
    "கோயம்புத்தூர்": "Coimbatore", "coimbatore": "கோயம்புத்தூர்",
    "சென்னை": "Chennai", "chennai": "சென்னை",
    "திருச்சிராப்பள்ளி": "Tiruchirappalli", "tiruchirappalli": "திருச்சிராப்பள்ளி",
    "தூத்துக்குடி": "Thoothukudi", "thoothukudi": "தூத்துக்குடி", "தாத்துச்குய": "Thoothukudi",
    "திண்டுக்கல்": "Dindigul", "dindigul": "திண்டுக்கல்",
    "திருப்பூர்": "Tiruppur", "tiruppur": "திருப்பூர்",
    "திருநெல்வேலி": "Tirunelveli", "tirunelveli": "திருநெல்வேலி",
    "வேலூர்": "Vellore", "vellore": "வேலூர்",
    "கடலூர்": "Cuddalore", "cuddalore": "கடலூர்",
    "நாகப்பட்டினம்": "Nagapattinam", "nagapattinam": "நாகப்பட்டினம்",
    "புதுக்கோட்டை": "Pudukkottai", "pudukkottai": "புதுக்கோட்டை",
    "ராமநாதபுரம்": "Ramanathapuram", "ramanathapuram": "ராமநாதபுரம்",
    "சிவகங்கை": "Sivaganga", "sivaganga": "சிவகங்கை",
    "விருதுநகர்": "Virudhunagar", "virudhunagar": "விருதுநகர்",
    "தேனி": "Theni", "theni": "தேனி",
    "கரூர்": "Karur", "karur": "கரூர்",
    "நாமக்கல்": "Namakkal", "namakkal": "நாமக்கல்",
    "நீலகிரி": "Nilgiris", "nilgiris": "நீலகிரி",
    "தர்மபுரி": "Dharmapuri", "dharmapuri": "தர்மபுரி",
    "கிருஷ்ணகிரி": "Krishnagiri", "krishnagiri": "கிருஷ்ணகிரி",
    "அரியலூர்": "Ariyalur", "ariyalur": "அரியலூர்",
    "பெரம்பலூர்": "Perambalur", "perambalur": "பெரம்பலூர்",
    "காஞ்சிபுரம்": "Kanchipuram", "kanchipuram": "காஞ்சிபுரம்",
    "திருவள்ளூர்": "Tiruvallur", "tiruvallur": "திருவள்ளூர்",
    "ராணிப்பேட்டை": "Ranipet", "ranipet": "ராணிப்பேட்டை",
    "திருப்பத்தூர்": "Tirupathur", "tirupathur": "திருப்பத்தூர்",
    "தென்காசி": "Tenkasi", "tenkasi": "தென்காசி",
    "கன்னியாகுமரி": "Kanyakumari", "kanyakumari": "கன்னியாகுமரி",
    "கள்ளக்குறிச்சி": "Kallakurichi", "kallakurichi": "கள்ளக்குறிச்சி",
    "செங்கல்பட்டு": "Chengalpattu", "chengalpattu": "செங்கல்பட்டு", "chengleput": "செங்கல்பட்டு",
    "chengleput joint i": "செங்கல்பட்டு இணை I", "chengleput joint 1": "செங்கல்பட்டு இணை I", "chengleput joint": "செங்கல்பட்டு இணை",
    "மயிலாடுதுறை": "Mayiladuthurai", "mayiladuthurai": "மயிலாடுதுறை",

    # Taluks
    "திண்டிவனம்": "Tindivanam", "tindivanam": "திண்டிவனம்",
    "செங்கல்பட்டு": "Chengalpattu", "chengalpattu": "செங்கல்பட்டு",
    "பட்டுக்கோட்டை": "Pattukkottai", "pattukkottai": "பட்டுக்கோட்டை",
    "நன்னிலம்": "Nannilam", "nannilam": "நன்னிலம்", "நள்aிலம்": "நன்னிலம்", "நளகாலம்": "நன்னிலம்",
    "கோபிசெட்டிபாளையம்": "Gobichettipalayam", "gobichettipalayam": "கோபிசெட்டிபாளையம்",
    "பொள்ளாச்சி": "Pollachi", "pollachi": "பொள்ளாச்சி",
    "மேலூர்": "Melur", "melur": "மேலூர்",
    "அத்தூர்": "Attur", "attur": "அத்தூர்",
    "மன்னார்குடி": "Mannargudi", "mannargudi": "மன்னார்குடி",
    "கோடவாசல்": "Kodavasal", "kodavasal": "கோடவாசல்",
    "நீடாமங்கலம்": "Needamangalam", "needamangalam": "நீடாமங்கலம்",
    "வலங்கைமான்": "Valangaiman", "valangaiman": "வலங்கைமான்",
    "அம்பத்தூர்": "Ambattur", "ambattur": "அம்பத்தூர்",
    "மாம்பலம்": "Mambalam", "mambalam": "மாம்பலம்",
    "திருவொற்றியூர்": "Tiruvottiyur", "tiruvottiyur": "திருவொற்றியூர்",
    "மேட்டுப்பாளையம்": "Mettupalayam", "mettupalayam": "மேட்டுப்பாளையம்",
    "சூலூர்": "Sulur", "sulur": "சூலூர்",

    # Villages
    "அலப்பாக்கம்": "Alappakkam", "alappakkam": "அலப்பாக்கம்",
    "வடமங்கலம்": "Vadamangalam", "vadamangalam": "வடமங்கலம்",
    "கீழையூர்": "Keezhaiyur", "keezhaiyur": "கீழையூர்",
    "சித்தோடு": "Chithode", "chithode": "சித்தோடு",
    "ஓடையகுளம்": "Odayakulam", "odayakulam": "ஓடையகுளம்", "உடையகுளம்": "ஓடையகுளம்",
    "செங்கபடை": "Sengapadai", "sengapadai": "செங்கபடை",
    "குமாரப்பாளையம்": "Kumarapalayam", "kumarapalayam": "குமாரப்பாளையம்",
    "வேளச்சேரி": "Velachery", "velachery": "வேளச்சேரி",
    "சோழிங்கநல்லூர்": "Sholinganallur", "sholinganallur": "சோழிங்கநல்லூர்",
    "ஆலந்தூர்": "Alandur", "alandur": "ஆலந்தூர்",
    "அடையாறு": "Adyar", "adyar": "அடையாறு", "adayar": "அடையாறு",
    "மயிலாப்பூர்": "Mylapore", "mylapore": "மயிலாப்பூர்",
    "கிண்டி": "Guindy", "guindy": "கிண்டி",
    "சென்னை தெற்கு": "Chennai South", "chennai south": "சென்னை தெற்கு",
    "சென்னை வடக்கு": "Chennai North", "chennai north": "சென்னை வடக்கு",
    "சென்னை மத்தி": "Chennai Central", "chennai central": "சென்னை மத்தி",
    "அம்பாசமுத்திரம்": "Ambasamudram", "ambasamudram": "அம்பாசமுத்திரம்",
    "கள்ளிடைக்குறிச்சி": "Kallidaikurichi", "kallidaikurichi": "கள்ளிடைக்குறிச்சி",
    "அயனாவரம்": "Ayanavaram", "ayanavaram": "அயனாவரம்",
    "வில்லிவாக்கம்": "Villivakkam", "villivakkam": "வில்லிவாக்கம்",
    "பெரம்பூர்": "Perambur", "perambur": "பெரம்பூர்",
    "எழும்பூர்": "Egmore", "egmore": "எழும்பூர்",
    "புரசைவாக்கம்": "Purasawalkam", "purasawalkam": "புரசைவாக்கம்",
    "மண்ணடி": "Mannady", "mannady": "மண்ணடி",
    "ராயபுரம்": "Royapuram", "royapuram": "ராயபுரம்",
    "தண்டையார்பேட்டை": "Tondiarpet", "tondiarpet": "தண்டையார்பேட்டை"
}

COMMON_NAMES = {
    "சுகுமார்": "Sukumar", "sukumar": "சுகுமார்",
    "முத்துலட்சுமி": "Muthulakshmi", "muthulakshmi": "முத்துலட்சுமி",
    "இராமன்": "Raman", "raman": "இராமன்", "ராமன்": "Raman",
    "செந்தில்குமார்": "Senthilkumar", "senthilkumar": "செந்தில்குமார்",
    "சந்தில்குமார்": "Senthilkumar",
    "சண்முகம்": "Shanmugam", "shanmugam": "சண்முகம்",
    "ராஜேந்திரன்": "Rajendran", "rajendran": "ராஜேந்திரன்", "இராஜந்திரன்": "Rajendran", "இராஜேந்திரன்": "Rajendran",
    "பக்கிரிசாமி": "Pakkirisamy", "pakkirisamy": "பக்கிரிசாமி",
    "கோவிந்தராசு": "Govindarasu", "govindarasu": "கோவிந்தராசு",
    "வேலுசாமி": "Velusamy", "velusamy": "வேலுசாமி",
    "பான்னுசாமி": "Ponnusamy", "பொன்னுசாமி": "Ponnusamy", "ponnusamy": "பொன்னுசாமி",
    "தனலட்சுமி": "Dhanalakshmi", "dhanalakshmi": "தனலட்சுமி",
    "சுப்பிரமணியம்": "Subramaniam", "subramaniam": "சுப்பிரமணியம்",
    "பாலசுப்பிரமணியம்": "Balasubramaniam", "balasubramaniam": "பாலசுப்பிரமணியம்",
    "சின்னசாமி": "Chinnaswamy", "chinnaswamy": "சின்னசாமி",
    "அம்சவல்லி": "Amsavalli", "amsavalli": "அம்சவல்லி",
    "கிருஷ்ணன்": "Krishnan", "krishnan": "கிருஷ்ணன்",
    "கார்த்திக்": "Karthik", "karthik": "கார்த்திக்",
    "பிரியா": "Priya", "priya": "பிரியா"
}

REAL_ESTATE_TERMS = {
    # Directions
    "வடக்கில்": "North", "வடக்கு": "North", "north": "வடக்கு",
    "தெற்கில்": "South", "தெற்கு": "South", "south": "தெற்கு",
    "கிழக்கில்": "East", "கிழக்கு": "East", "east": "கிழக்கு",
    "மேற்கில்": "West", "மேற்கு": "West", "west": "மேற்கு",

    # Property details
    "மனை": "Plot / Site", "plot": "மனை",
    "எண்": "No.", "number": "எண்",
    "புல": "Survey", "survey": "சர்வே / புல",
    "சர்வே": "Survey",
    "சொத்து": "Property", "சொத்து": "Property", "property": "சொத்து",
    "விவரம்": "Details", "விவரங்கள்": "Details", "details": "விவரங்கள்",
    "கிராமம்": "Village", "village": "கிராமம்",
    "வட்டம்": "Taluk", "taluk": "வட்டம்",
    "மாவட்டம்": "District", "district": "மாவட்டம்",
    "ஆவணம்": "Document / Deed", "document": "ஆவணம்",
    "சார்பதிவாளர்": "Sub-Registrar", "sub": "சார்", "registrar": "பதிவாளர்",
    "அலுவலகம்": "Office", "office": "அலுவலகம்",
    "நாள்": "Date", "date": "நாள்",
    "தேடுதல்": "Search", "search": "தேடுதல்",
    "காலம்": "Period", "period": "காலம்",
    "விஸ்தீரணம்": "Extent", "பரப்பு": "Extent", "extent": "விஸ்தீரணம் / பரப்பு",
    "கைமாற்றுத்": "Consideration", "consideration": "கைமாற்றுத் தொகை",
    "தொகை": "Amount", "தொகை": "Amount", "amount": "தொகை", "value": "மதிப்பு",
    "சந்தை": "Market", "market": "சந்தை",
    "மதிப்பு": "Value",
    "முந்தைய": "Prior", "prior": "முந்தைய",
    "குறிப்புகள்": "Remarks", "remarks": "குறிப்புகள்",
    "தான": "Gift", "gift": "தானம்",
    "செட்டில்மெண்ட்": "Settlement", "settlement": "செட்டில்மெண்ட்",
    "கிரையப்": "Sale", "கிரையம்": "Sale", "sale": "கிரையம்", "conveyance": "கிரையப் பத்திரம்",
    "பத்திரம்": "Deed", "deed": "பத்திரம்",
    "வில்லங்கம்": "Encumbrance", "encumbrance": "வில்லங்கம்",
    "சான்றிதழ்": "Certificate", "சான்று": "Certificate", "certificate": "சான்றிதழ்",
    "படிவம்": "Form", "form": "படிவம்",
    "உரிமையாளர்": "Owner", "owner": "உரிமையாளர்",
    "பரிவர்த்தனை": "Transaction", "transaction": "பரிவர்த்தனை",
    "பரிவர்த்தனைகள்": "Transactions", "transactions": "பரிவர்த்தனைகள்",
    "எழுதி": "Executed",
    "கொடுத்தவர்": "Executant", "கொடுத்தவர்": "Executant", "executant": "எழுதிக் கொடுத்தவர்", "executants": "எழுதிக் கொடுத்தவர்கள்",
    "வாங்கியவர்": "Claimant", "claimant": "எழுதி வாங்கியவர்", "claimants": "எழுதி வாங்கியவர்கள்",
    "அடுக்குமாடி": "Apartment / Flat", "flat": "அடுக்குமாடி குடியிருப்பு",
    "குடியிருப்பு": "Residential", "residential": "குடியிருப்பு",
    "கதவு": "Door", "door": "கதவு",
    "புதிய": "New", "new": "புதிய",
    "பழைய": "Old", "old": "பழைய",
    "பிளாக்": "Block", "block": "பிளாக்",
    "தெரு": "Street", "street": "தெரு",
    "சாலை": "Road", "road": "சாலை",
    "நகரம்": "Town", "town": "நகரம்",
    "சதுரடி": "Sq. Ft", "sqft": "சதுரடி", "sq.ft": "சதுரடி",
    "சதுர": "Square", "square": "சதுர",
    "மீட்டர்": "Meter", "meter": "மீட்டர்",
    "சென்ட்": "Cent", "cent": "சென்ட்",
    "ஏக்கர்": "Acre", "acre": "ஏக்கர்",
    "அடமானம்": "Mortgage", "mortgage": "அடமானம்",
    "விடுதலை": "Release", "release": "விடுதலை",
    "பாகப்பிரிவினை": "Partition", "partition": "பாகப்பிரிவினை",
    "அதிகாரப்": "Power of", "power": "அதிகாரம்", "attorney": "முகவர் / பத்திரம்",
    "அரசு": "Government", "government": "அரசு",
    "பதிவு": "Registration", "registration": "பதிவு",
    "துறை": "Department", "department": "துறை",
    "வங்கி": "Bank", "bank": "வங்கி",
    "கடன்": "Loan", "loan": "கடன்",
    "இன்மை": "Nil", "nil": "இன்மை",

    # Administrative and Jurisdiction terms
    "taluk": "வட்டம்",
    "district": "மாவட்டம்",
    "village": "கிராமம்",
    "jurisdiction": "எல்லை",
    "sro": "சார்பதிவாளர் அலுவலகம்",
    "sub-registrar": "சார்பதிவாளர்",
    "sub registrar": "சார்பதிவாளர்",
    "office": "அலுவலகம்",
    "zone": "மண்டலம்",
    "south": "தெற்கு",
    "north": "வடக்கு",
    "central": "மத்தி",
    "chennai south": "சென்னை தெற்கு",
    "chennai north": "சென்னை வடக்கு",
    "chennai central": "சென்னை மத்தி",
    "adayar": "அடையாறு",
    "adyar": "அடையாறு",
    "guindy": "கிண்டி",
    "mylapore": "மயிலாப்பூர்",
    "velachery": "வேளச்சேரி",
    "thiruvarur": "திருவாரூர்",
    "coimbatore": "கோயம்புத்தூர்",
    "madurai": "மதுரை",
    "salem": "சேலம்",
    "tirunelveli": "திருநெல்வேலி",
    "thoothukudi": "தூத்துக்குடி",
}


# ---------------------------------------------------------------------------
# English → Tamil phonetic transliteration tables
# ---------------------------------------------------------------------------

# Multi-char cluster → Tamil (checked longest-first)
_EN_TA_MULTI: list[tuple[str, str]] = [
    # Vowel clusters (order: longest first)
    ("oo",  "ூ"),  ("ee",  "ீ"),  ("ai",  "ை"),  ("au",  "ௌ"),
    ("ou",  "ௌ"),  ("aa",  "ா"),  ("ae",  "ை"),
    # Consonant clusters
    ("ksh", "க்ஷ"), ("thr", "த்ர"), ("shr", "ஷ்ர"),
    ("sh",  "ஷ"),  ("ch",  "ச"),  ("ng",  "ங"),   ("ny",  "ஞ"),
    ("nh",  "ஞ"),  ("zh",  "ழ"),  ("th",  "த"),   ("ph",  "ப"),
    ("gh",  "க"),  ("kh",  "க"),  ("bh",  "ப"),   ("dh",  "த"),
    ("jh",  "ஜ"),  ("ck",  "க்க"), ("tt",  "ட்ட"), ("ll",  "ல்ல"),
    ("nn",  "ண்ண"), ("mm",  "ம்ம"), ("rr",  "ற்ற"), ("ss",  "ஸ்ஸ"),
    ("pp",  "ப்ப"), ("bb",  "ப்ப"), ("dd",  "ட்ட"), ("ff",  "ப்"),
]

# Single char → Tamil consonant (no inherent vowel added separately)
_EN_TA_SINGLE_CONS: dict[str, str] = {
    'k': 'க', 'g': 'க', 'c': 'க', 's': 'ஸ', 'z': 'ஸ',
    't': 'ட', 'd': 'ட', 'p': 'ப', 'b': 'ப', 'f': 'ப',
    'm': 'ம', 'n': 'ன', 'y': 'ய', 'r': 'ர', 'l': 'ல',
    'v': 'வ', 'w': 'வ', 'j': 'ஜ', 'h': 'ஹ', 'q': 'க',
    'x': 'க்ஸ',
}

# Single char → Tamil vowel sign (when following a consonant) or standalone vowel
_EN_TA_VOWEL_SIGN: dict[str, str] = {
    'a': 'அ', 'i': 'இ', 'u': 'உ', 'e': 'எ', 'o': 'ஒ',
}
_EN_TA_VOWEL_DIAC: dict[str, str] = {
    'a': 'ா', 'i': 'ி', 'u': 'ு', 'e': 'ெ', 'o': 'ொ',
}


def dynamic_english_to_tamil(text: str) -> str:
    """
    Translates any English name/place to Tamil.
    Primary: Canonical and administrative dictionary lookup.
    Secondary: IndicTrans2 neural translation (accurate, context-aware).
    Fallback: Phonetic transliteration rules (always available).
    """
    word = text.strip()
    if not word:
        return ""

    # 1. Quick canonical and administrative dictionary lookup first (instant, accurate)
    lookup = (
        CANONICAL_PLACES.get(word.lower())
        or COMMON_NAMES.get(word.lower())
        or REAL_ESTATE_TERMS.get(word.lower())
    )
    if lookup and any('\u0b80' <= c <= '\u0bff' for c in lookup):
        return lookup

    # 2. Try IndicTrans2 neural translation (best quality)
    if _INDICTRANS2_IMPORTED and _it2_available():
        try:
            result = translate_to_tamil(word)
            if result and any('\u0b80' <= c <= '\u0bff' for c in result):
                logger.debug(f"IndicTrans2 en→ta: {word!r} → {result!r}")
                return result
        except Exception as e:
            logger.warning(f"IndicTrans2 en→ta failed for {word!r}: {e}")

    # 3. Phonetic fallback
    return _phonetic_english_to_tamil(word)


def _phonetic_english_to_tamil(text: str) -> str:
    """Pure phonetic rule-based English→Tamil transliteration (fallback)."""
    word = text.strip()
    if not word:
        return ""

    s = word.lower()
    out_chars: list[str] = []
    i = 0
    n = len(s)

    while i < n:
        # Try longest multi-char cluster first
        matched = False
        for cluster, ta in _EN_TA_MULTI:
            cl = len(cluster)
            if s[i:i+cl] == cluster:
                if cluster in ("oo", "ee", "ai", "au", "ou", "aa", "ae"):
                    out_chars.append(ta)
                else:
                    out_chars.append(ta)
                i += cl
                matched = True
                break

        if matched:
            continue

        ch = s[i]

        if ch in _EN_TA_VOWEL_SIGN:
            if out_chars and out_chars[-1] not in ('அ', 'ஆ', 'இ', 'ஈ', 'உ', 'ஊ', 'எ', 'ஏ', 'ஒ', 'ஓ',
                                                     'ா', 'ி', 'ீ', 'ு', 'ூ', 'ெ', 'ே', 'ை', 'ொ', 'ோ', 'ௌ'):
                if ch == 'a':
                    pass  # inherent 'a'
                else:
                    out_chars.append(_EN_TA_VOWEL_DIAC[ch])
            else:
                out_chars.append(_EN_TA_VOWEL_SIGN[ch])
            i += 1

        elif ch in _EN_TA_SINGLE_CONS:
            ta_cons = _EN_TA_SINGLE_CONS[ch]
            if i + 1 < n and s[i+1] not in _EN_TA_VOWEL_SIGN and s[i+1] not in ('a','e','i','o','u'):
                out_chars.append(ta_cons)
                out_chars.append('்')
            else:
                out_chars.append(ta_cons)
            i += 1

        else:
            out_chars.append(ch)
            i += 1

    return "".join(out_chars)


def dynamic_transliterate_tamil(word: str) -> str:
    """
    Translates any Tamil word/phrase to English.
    Primary: IndicTrans2 neural translation.
    Fallback: Phonetic rule-based transliteration.
    """
    clean = word.strip()
    if not clean:
        return ""

    # 1. Quick dictionary lookup
    if clean in COMMON_NAMES:
        return COMMON_NAMES[clean]
    if clean in CANONICAL_PLACES:
        return CANONICAL_PLACES[clean]

    # 2. Try IndicTrans2 neural translation (best quality)
    if _INDICTRANS2_IMPORTED and _it2_available():
        try:
            result = translate_to_english(clean)
            if result and any('a' <= c.lower() <= 'z' for c in result):
                logger.debug(f"IndicTrans2 ta→en: {clean!r} → {result!r}")
                return result.strip().title()
        except Exception as e:
            logger.warning(f"IndicTrans2 ta→en failed for {clean!r}: {e}")

    # 3. Phonetic fallback
    return _phonetic_tamil_to_english(clean)


def _phonetic_tamil_to_english(word: str) -> str:
    """Pure phonetic rule-based Tamil→English transliteration (fallback)."""
    clean = word.strip()
    chars = list(clean)
    out = []
    i = 0
    while i < len(chars):
        c = chars[i]
        if c in TAMIL_VOWELS:
            out.append(TAMIL_VOWELS[c])
            i += 1
        elif c in TAMIL_CONSONANTS:
            prev_is_nasal = (len(out) > 0 and out[-1] in ['ng', 'n', 'm', 'ny'])
            prev_is_vowel = (len(out) > 0 and out[-1] in ['a', 'aa', 'i', 'ee', 'u', 'oo', 'e', 'ai', 'o'])
            use_voiced = prev_is_nasal or (prev_is_vowel and c in ['ட', 'க'])
            cons = TAMIL_CONSONANTS[c][1] if use_voiced else TAMIL_CONSONANTS[c][0]
            if i + 1 < len(chars) and chars[i + 1] in TAMIL_VOWEL_SIGNS:
                v_sign = chars[i + 1]
                v_sound = TAMIL_VOWEL_SIGNS[v_sign]
                out.append(cons + v_sound)
                i += 2
            else:
                out.append(cons + 'a')
                i += 1
        else:
            out.append(c)
            i += 1

    res = "".join(out)
    res = re.sub(r'ngg', 'ng', res)
    res = re.sub(r'ee$', 'i', res)
    res = re.sub(r'aiyoor', 'aiyur', res)
    res = re.sub(r'oo$', 'ur', res)
    return res.capitalize()


def format_bilingual_entity(text: str) -> str:
    """
    Formats any location/entity strictly as:
        English Name (Tamil Name)
    Handles:
        1. 'விழுப்புரம் (Villupuram)' -> 'Villupuram (விழுப்புரம்)'
        2. 'Villupuram (விழுப்புரம்)' -> 'Villupuram (விழுப்புரம்)'
        3. Pure Tamil: 'தஞ்சாவூர்' -> 'Thanjavur (தஞ்சாவூர்)'
        4. Pure English: 'Erode' -> 'Erode (ஈரோடு)'
    """
    if not text or text == "Not Detected":
        return "Not Detected"

    clean = text.strip()
    
    # Strip any residual label noise (e.g. '/ District')
    clean = re.sub(r'^[/:\-\s]*(?:district|taluk|village|revenue|மாவட்டம்|வட்டம்|கிராமம்)[/:\-\s]*', '', clean, flags=re.IGNORECASE).strip()
    if not clean:
        return "Not Detected"

    # 1. Check if Tamil (English) e.g. 'விழுப்புரம் (Villupuram)'
    m1 = re.match(r'^([\u0b80-\u0bff\s,\./\-]+?)\s*\(([A-Za-z0-9\s,\./\-]+)\)$', clean)
    if m1:
        ta_part = m1.group(1).strip()
        en_part = m1.group(2).strip()
        return f"{en_part} ({ta_part})"

    # 2. Check if English (Tamil) e.g. 'Villupuram (விழுப்புரம்)'
    m2 = re.match(r'^([A-Za-z0-9\s,\./\-]+?)\s*\(([\u0b80-\u0bff\s,\./\-]+)\)$', clean)
    if m2:
        en_part = m2.group(1).strip()
        ta_part = m2.group(2).strip()
        return f"{en_part} ({ta_part})"

    has_tamil = any('\u0b80' <= c <= '\u0bff' for c in clean)
    has_english = any('a' <= c.lower() <= 'z' for c in clean)

    if has_tamil and not has_english:
        en_val = (
            CANONICAL_PLACES.get(clean)
            or COMMON_NAMES.get(clean)
            or REAL_ESTATE_TERMS.get(clean)
            or dynamic_transliterate_tamil(clean)
        )
        return f"{en_val} ({clean})"
    elif has_english and not has_tamil:
        # Check whole phrase first
        ta_val = (
            CANONICAL_PLACES.get(clean.lower())
            or COMMON_NAMES.get(clean.lower())
            or REAL_ESTATE_TERMS.get(clean.lower())
        )
        if not ta_val:
            # Special handling for "X Taluk / Jurisdiction" or "X Taluk"
            m_taluk = re.match(r'^(.+?)\s+Taluk(?:\s*/\s*Jurisdiction)?$', clean, re.IGNORECASE)
            if m_taluk:
                base_place = m_taluk.group(1).strip()
                ta_place = dynamic_english_to_tamil(base_place)
                return f"{clean} ({ta_place} வட்டம்)"
            m_dist = re.match(r'^(.+?)\s+District$', clean, re.IGNORECASE)
            if m_dist:
                base_place = m_dist.group(1).strip()
                ta_place = dynamic_english_to_tamil(base_place)
                return f"{clean} ({ta_place} மாவட்டம்)"
            m_sro = re.match(r'^(.+?)\s+S\.?R\.?O\.?$', clean, re.IGNORECASE)
            if m_sro:
                base_place = m_sro.group(1).strip()
                ta_place = dynamic_english_to_tamil(base_place)
                return f"{clean} ({ta_place} சார்பதிவாளர் அலுவலகம்)"

            # Dynamically translate/transliterate words
            words = clean.split()
            ta_words = []
            for w in words:
                w_clean = re.sub(r'^[^\w]+|[^\w]+$', '', w)
                w_ta = (
                    CANONICAL_PLACES.get(w_clean.lower())
                    or COMMON_NAMES.get(w_clean.lower())
                    or REAL_ESTATE_TERMS.get(w_clean.lower())
                    or dynamic_english_to_tamil(w_clean)
                )
                ta_words.append(w_ta if w_ta else w)
            ta_val = " ".join(ta_words)
        return f"{clean} ({ta_val})" if ta_val else clean

    return clean


def format_bilingual_owner(raw_owner_str: str) -> str:
    """
    Translates and formats owner name(s) and kinship strictly as:
        English Name(s) (Tamil Name(s))
    """
    if not raw_owner_str or raw_owner_str == "Not Detected":
        return "Not Detected"

    clean_str = raw_owner_str.strip()

    # 1. Bilingual kinship lines:
    # e.g. "1. முத்துலட்சுமி (Muthulakshmi) கணவர் / Wife of இராமன் (Raman)"
    # e.g. "2. சந்தில்குமார் (Senthilkumar) மகன் / Son of இராமன் (Raman)"
    bi_pat = r'(\d+\.?\s*)?([^\(\n]+?)\s*\(([A-Za-z\s]+)\)\s*(?:(மகன்|மகள்|மனைவி|கணவர்)\s*/\s*)?(?:Son|Wife|Daughter|Husband)\s+of\s+([^\(\n]+?)\s*\(([A-Za-z\s]+)\)'
    bi_matches = list(re.finditer(bi_pat, clean_str, re.IGNORECASE))
    if bi_matches:
        results = []
        for m in bi_matches:
            prefix = m.group(1) or ""
            ta_owner = m.group(2).strip()
            en_owner = m.group(3).strip()
            ta_parent = m.group(5).strip()
            en_parent = m.group(6).strip()

            rel_text = m.group(0).lower()
            rel_en, rel_ta = ("S/o", "மகன்") if 'son' in rel_text or 'மகன்' in rel_text else (
                ("W/o", "மனைவி") if 'wife' in rel_text or 'மனைவி' in rel_text else (
                    ("D/o", "மகள்") if 'daughter' in rel_text or 'மகள்' in rel_text else ("H/o", "கணவர்")
                )
            )
            # In Tamil culture, wife of husband is "கணவர் [Husband]" or "[Husband] மனைவி"
            if 'கணவர்' in rel_text and 'wife of' in rel_text:
                rel_ta = "மனைவி"

            results.append(f"{en_owner} ({rel_en} {en_parent}) ({ta_parent} {rel_ta} {prefix}{ta_owner})")
        return ", ".join(results)

    # 2. Pure Tamil Kinship pattern: [Parent] (மகன்|மகள்|மனைவி|கணவர்) [Owner]
    ta_pat = r'([A-Za-z\u0b80-\u0bff]+)\s+(மகன்|மகள்|மனைவி|கணவர்)\s+([A-Za-z\u0b80-\u0bff]+)'
    ta_matches = list(re.finditer(ta_pat, clean_str))
    if ta_matches:
        results = []
        for m in ta_matches:
            ta_parent = m.group(1).strip()
            ta_rel = m.group(2).strip()
            ta_owner = m.group(3).strip()

            rel_en = "S/o" if ta_rel == "மகன்" else (
                "W/o" if ta_rel == "மனைவி" else (
                    "D/o" if ta_rel == "மகள்" else "H/o"
                )
            )
            en_parent = CANONICAL_PLACES.get(ta_parent) or COMMON_NAMES.get(ta_parent) or dynamic_transliterate_tamil(ta_parent)
            en_owner = CANONICAL_PLACES.get(ta_owner) or COMMON_NAMES.get(ta_owner) or dynamic_transliterate_tamil(ta_owner)

            results.append(f"{en_owner}, {rel_en} {en_parent} ({ta_parent} {ta_rel} {ta_owner})")
        return ", ".join(results)

    # 3. English Kinship / Legal Heirs pattern
    en_pat = r'([A-Za-z\s]+?)\s*(?:,\s*|\s+)(?:(Son of|Wife of|Daughter of|Husband of|W/o|S/o|D/o))\s+(?:Late\s+)?([A-Za-z\s]+)'
    en_matches = list(re.finditer(en_pat, clean_str, re.IGNORECASE))
    if en_matches:
        results = []
        seen = set()
        for m in en_matches:
            p_name = m.group(1).strip()
            rel_raw = m.group(2).strip().lower()
            parent = re.sub(r'\(Legal.*$', '', m.group(3), flags=re.IGNORECASE).strip()
            if p_name.lower() in seen or len(p_name) < 2:
                continue
            seen.add(p_name.lower())

            rel_en = 'W/o' if 'wife' in rel_raw or 'w/o' in rel_raw else (
                'S/o' if 'son' in rel_raw or 's/o' in rel_raw else (
                    'D/o' if 'daughter' in rel_raw or 'd/o' in rel_raw else 'H/o'
                )
            )
            rel_ta = 'மனைவி' if rel_en == 'W/o' else ('மகன்' if rel_en == 'S/o' else ('மகள்' if rel_en == 'D/o' else 'கணவர்'))
            late = "Late " if "late" in clean_str.lower() else ""

            # Tamil equivalents: look up in dict or transliterate dynamically
            def _en_to_ta(name: str) -> str:
                looked = COMMON_NAMES.get(name.lower())
                if looked:
                    return looked
                # word-by-word transliteration
                return " ".join(dynamic_english_to_tamil(w) for w in name.split())

            ta_name = _en_to_ta(p_name)
            ta_parent_name = _en_to_ta(parent)

            rel_ta_label = f"{ta_parent_name} {rel_ta} {ta_name}"
            results.append(f"{p_name} ({rel_en} {late}{parent}) ({rel_ta_label})")

        if results:
            suffix = " — all legal heirs" if "legal heir" in clean_str.lower() else ""
            return ", ".join(results) + suffix

    return format_bilingual_entity(clean_str)


def translate_word_bilingual(word: str) -> str:
    """
    Translates a single word or token dynamically:
    - If Tamil word: translates to English (e.g. வடக்கில் -> North, மனை -> Plot, கிராமம் -> Village)
    - If English word: translates to Tamil (e.g. Property -> சொத்து, Village -> கிராமம்)
    """
    if not word:
        return ""
    clean = re.sub(r'^[^\w\u0b80-\u0bff]+|[^\w\u0b80-\u0bff]+$', '', word).strip()
    if not clean or clean.isdigit() or (len(clean) <= 1 and not ('\u0b80' <= clean <= '\u0bff')):
        return ""

    c_low = clean.lower()
    # 1. Check real estate dictionary
    if clean in REAL_ESTATE_TERMS:
        return REAL_ESTATE_TERMS[clean]
    if c_low in REAL_ESTATE_TERMS:
        return REAL_ESTATE_TERMS[c_low]

    # 2. Check canonical places / common names
    if clean in CANONICAL_PLACES:
        return CANONICAL_PLACES[clean]
    if c_low in CANONICAL_PLACES:
        return CANONICAL_PLACES[c_low]
    if clean in COMMON_NAMES:
        return COMMON_NAMES[clean]
    if c_low in COMMON_NAMES:
        return COMMON_NAMES[c_low]

    # 3. Dynamic translation/transliteration
    has_tamil = any('\u0b80' <= c <= '\u0bff' for c in clean)
    has_english = any('a' <= c.lower() <= 'z' for c in clean)

    if has_tamil:
        return dynamic_transliterate_tamil(clean)
    elif has_english:
        return dynamic_english_to_tamil(clean)

    return ""

