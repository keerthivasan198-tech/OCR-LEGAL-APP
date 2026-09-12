# PlotChoice Legal Document OCR & Cross-Verification Platform

An AI-powered, bilingual (Tamil & English) document intelligence and cross-verification platform built specifically for Indian and Tamil Nadu real estate and property title scrutiny.

---

## 🌟 Key Features

### 1. Dual-Pipeline Vision-Language OCR Engine
- **PaddleOCR VL-1.6 Architecture**:
  - **Tamil Pipeline**: PP-LCNet doc orientation + textline orientation + server detection (PP-OCRv5_server_det) + mobile recognition (	a_PP-OCRv5_mobile_rec).
  - **English Pipeline**: Server detection (PP-OCRv6_medium_det) + recognition (PP-OCRv6_medium_rec).
  - **Bilingual Coordinate Merger**: Spatial intersection matching to align and merge bilingual Tamil/English lines and words with precise bounding boxes.

### 2. Deep Key-Value Extractors (11 Document Types)
Supports automated extraction, parsing, and structured verification across 11 key land and legal document categories:
1. **Sale Deed / Title Deed** (*கிரையப் பத்திரம் / தாய் பத்திரம்*)
2. **Patta Document** (*பட்டா ஆவணம் — கிராமம் & நகரம்*)
3. **Town Survey Land Register (TSLR)** (*நகர நில அளவை ஆவணம்*)
4. **Encumbrance Certificate (EC - Form 15 / 16)** (*வில்லங்கச் சான்றிதழ்*)
5. **Parent Documents / Mother Copy** (*முந்தைய மூல ஆவணங்கள்*)
6. **Approved Building Plan** (*அங்கீகரிக்கப்பட்ட கட்டிட வரைபடம்*)
7. **RERA Certificate** (*TNRERA பதிவு சான்றிதழ்*)
8. **Property Tax, Water Tax & EB Receipts** (*சொத்து வரி, குடிநீர் வரி & EB ரசீது*)
9. **Approved Layout (CMDA / DTCP)** (*அங்கீகரிக்கப்பட்ட மனைப்பிரிவு*)
10. **Death Certificate & Legal Heir Certificate** (*இறப்பு & வாரிசுச் சான்றிதழ்*)
11. **Loan Documents & MODT** (*வங்கி கடன் & அடமான ஆவணங்கள்*)

### 3. Encumbrance Certificate (EC) Deep Scrutiny Engine
- Dynamic transaction segmenter capturing all registered deeds, conveyances, mortgages, receipts, and leases.
- Institutional name resolution (*Bank of India, ICICI Bank, State Bank of India, CMDA, TIIC, etc.*).
- Automatic Tamil-English transliteration for individual party names.
- Verification signals: Open/Unreleased Mortgages, Closed Mortgages, Court Attachments & Decrees, 30-Year Search Period Compliance.

### 4. Cross-Verification Matrix & Inherited Property Track
- Automated cross-referencing of vendor names, survey numbers, extent measurements, and SRO details across multiple documents.
- Dedicated **Inherited Property (Varisu) Gate**: Checks 100% legal heir execution and mandatory Patta mutation under the Tamil Nadu Patta Pass Book Act, 1983.

---

## 🛠 Tech Stack

- **Backend**: Python 3.11, FastAPI, Uvicorn, PyPDFium2, Pillow, OpenCV
- **OCR Engine**: PaddlePaddle (GPU/CPU), PaddleOCR 2.8+ / PaddleX, IndicTrans2
- **Frontend**: Single Page Application (HTML5, Tailwind CSS, Lucide Icons, Canvas bounding-box overlay)

---

## 🚀 Easy Installation & Setup Guide

### Step 1: Open PowerShell
Open PowerShell.

### Step 2: Clone the Repository
```powershell
git clone https://github.com/keerthivasan198-tech/OCR-LEGAL-APP.git
cd OCR-LEGAL-APP
```

### Step 3: Create Virtual Environment
```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Step 4: Install Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Fix Hugging Face Download
```powershell
$env:HF_HUB_DISABLE_XET="1"
```

### Step 6: Download Qwen Model & llama.cpp
```powershell
python setup_qwen_service.py
```

### Step 7: Start Qwen AI Service
```powershell
.\start_llama_server.bat
```

### Step 8: Open a New PowerShell
```powershell
cd OCR-LEGAL-APP
.venv\Scripts\activate
```

### Step 9: Start Web Application
```powershell
python run.py
```

### Step 10: Open Browser
http://localhost:8000

1. Select your document type (e.g., Patta document or Sale deed).
2. Upload any PDF or scanned image (or click Load Sample for instant demonstration).
3. Click Run GPU OCR to view bounding boxes, full OCR text, extracted entities, and legal checklists!

---

## 📁 Project Structure

`
├── app/
│   ├── extractors/            # Specialized document type extractors
│   │   ├── ec_extractor.py    # Encumbrance Certificate extractor
│   │   ├── patta_extractor.py # Rural Patta extractor
│   │   ├── tslr_extractor.py  # Town Survey Land Register extractor
│   │   └── ...
│   ├── cross_checker.py       # Cross-verification matrix engine
│   ├── extractor.py           # Master DocumentExtractor router
│   ├── ocr_engine.py          # Dual-pipeline PaddleOCR engine
│   ├── samples.py             # Sample documents and bundles
│   ├── server.py              # FastAPI REST endpoints
│   └── translator.py          # Bilingual Tamil/English transliterator
├── static/
│   ├── app.js                 # Frontend SPA logic
│   ├── index.html             # UI layout and viewers
│   └── style.css              # Custom styling
├── run.py                     # Application startup entry point
└── README.md
`

---

## 📄 License

This project is developed for Indian & Tamil Nadu property verification and legal document intelligence.
