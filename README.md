# PlotChoice Legal Document OCR & AI Intelligence Platform

An AI-powered, bilingual (**Tamil & English**) document extraction, verification, and property title scrutiny platform built specifically for Indian and Tamil Nadu real estate legal records (Patta/Chitta, Sale Deeds, EC, TSLR, Parent Deeds, and more).

---

## 🌟 Key Features

1. **Dual-Pipeline OCR (PaddleOCR VL-1.6)**:
   - **Tamil + English**: Server detection and recognition with high precision on complex Indic scripts.
   - **Native PDF Support**: Instant sub-second digital PDF vector parsing via PyPDFium2 and pdfplumber.
   - **Word-Level Bounding Boxes**: Interactive visual canvas highlighting extracted values and translations.
2. **Dual-Engine Entity Extraction**:
   - **Instant Rule & Gazette Engine**: Instantaneous (<0.01s) regex extraction with Tamil Nadu Gazette district/taluk/village dictionary normalization.
   - **Local AI Engine (Qwen 2.5 7B Instruct GGUF)**: Privacy-preserving local LLM on llama.cpp providing context-aware entity extraction and typo correction.
   - **Optional Cloud Acceleration**: Supports Google Gemini 2.5 Flash for ultra-fast 1.2-second extraction if an API key is configured.
3. **100% In-Memory Privacy (Zero-Disk Retention)**:
   - Uploaded documents and extraction outputs are processed strictly in RAM (`io.BytesIO`) and **never permanently stored** on the server disk or folders. Fully DPDP Act compliant.
4. **11 Supported Legal Document Categories**:
   - Patta / Chitta (Form 10(1))
   - Sale Deed / Title Deed (*கிரையப் பத்திரம்*)
   - Encumbrance Certificate (EC Form 15 & 16) (*வில்லங்கச் சான்றிதழ்*)
   - Town Survey Land Register (TSLR) (*நகர நில அளவை ஆவணம்*)
   - Parent / Mother Documents (*தாய் பத்திரம்*)
   - Approved Building Plan (CMDA / DTCP)
   - TNRERA Registration Certificate
   - Property Tax, Water Tax & EB (TANGEDCO) Receipts
   - Layout Approvals (PPD/LO)
   - Death Certificate & Legal Heir Certificate (*வாரிசுச் சான்றிதழ்*)
   - Bank Loan / MODT Documents
5. **Cross-Document Verification & Legal Checklist**:
   - Verifies owner name continuity, survey number consistency, extent parity, and SRO jurisdiction across document sets.
   - Dedicated **Inherited Property (Varisu) Gate**: Validates 100% legal heir execution and mandatory Patta mutation under the Tamil Nadu Patta Pass Book Act, 1983.
6. **Multi-Format Export**:
   - Download formal audit reports as **PDF**, **CSV**, **JSON**, or structured **TXT**.

---

## 💻 System Requirements

- **Operating System**: Windows 10/11 (64-bit) or Linux (Ubuntu 20.04+)
- **Python**: Python 3.10 or 3.11 (Python 3.11.9 recommended)
- **Memory (RAM)**:
  - Minimum: 8 GB RAM (for OCR + Rule Engine)
  - Recommended: 16 GB RAM (for running the local Qwen 2.5 7B AI model)
- **GPU (Optional)**: NVIDIA GPU with CUDA support for accelerated OCR and inference. (Runs 100% smoothly on CPU as well).

---

## 🚀 Easy Installation & Setup Guide

### Step 1: Clone the Repository

Open Command Prompt, PowerShell, or Terminal:

```bash
git clone https://github.com/keerthivasan198-tech/OCR-LEGAL-APP.git
cd OCR-LEGAL-APP
```

---

### Step 2: Create and Activate Virtual Environment

**On Windows (PowerShell / Command Prompt):**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### Step 3: Install Python Dependencies

Make sure pip is up to date, then install the required packages:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 4: Download the AI Model & Binaries (Turnkey Setup)

We provide an automated setup script that automatically downloads the pre-built `llama-server.exe` engine and the **Qwen 2.5 7B Instruct GGUF** model (4.68 GB) directly from Hugging Face:

```bash
python setup_qwen_service.py
```

This will automatically create:
- `bin/llama-cpp/` containing the optimized `llama-server` engine.
- `models/Qwen2.5-7B-Instruct-Q4_K_M.gguf` for local offline AI extraction.

*(Note: The model download requires an active internet connection once. After download, everything runs 100% offline without internet).*

---

### Step 5: Run the Application

You can launch the full system using **1-Click Launchers** or manually in terminal windows.

#### Option A: 1-Click Launchers (Windows)

- **Option 1**: Double-click `start_full_stack.bat` in File Explorer.
- **Option 2**: Run via PowerShell:
  ```powershell
  .\start_full_stack.ps1
  ```

This automatically opens two synchronized services:
1. `start_llama_server.bat` $\rightarrow$ Local AI Service on port **8080**
2. `start_app.bat` $\rightarrow$ Web Application on port **8000**

---

#### Option B: Manual Two-Terminal Launch

If you prefer starting each service manually:

**Terminal 1 (AI Service):**
```powershell
start_llama_server.bat
```
*(Runs on `http://127.0.0.1:8080/v1`)*

**Terminal 2 (Web Server):**
```powershell
.venv\Scripts\activate
python run.py
```
*(Runs on `http://127.0.0.1:8000`)*

---

### Step 6: Access the Web App

Open your browser and navigate to:
```
http://localhost:8000
```

1. Select your document type (e.g., **Patta document** or **Sale deed**).
2. Upload any PDF or scanned image (or click **Load Sample** for instant demonstration).
3. Click **Run GPU OCR** to view bounding boxes, full OCR text, extracted entities, and legal checklists!

---

## ⚡ Optional: 1.2-Second Cloud Acceleration (Google Gemini Flash)

If you have a Google Gemini API Key and want lightning-fast 1.2-second extractions:
1. Create a file named `.env` in the root project folder.
2. Add your API key:
   ```env
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```
3. Restart the web server (`python run.py`).
4. The system will automatically use Gemini 2.5 Flash for instant extractions and fall back to local Qwen 2.5 7B when offline.

---

## 📁 Project Structure

```
OCR-LEGAL-APP/
├── app/
│   ├── extractors/                 # Modular document extractors
│   │   ├── patta_extractor.py      # Patta/Chitta extraction & bilingual logic
│   │   ├── sale_deed_extractor.py  # Sale deed & property schedule parsing
│   │   ├── ec_extractor.py         # Encumbrance certificate transaction parser
│   │   ├── tslr_extractor.py       # Town survey register extractor
│   │   └── ...
│   ├── cross_checker.py            # Cross-document verification matrix
│   ├── extractor.py                # Master entity extractor router & gazette tables
│   ├── llm_engine.py               # Local Qwen 2.5 7B & Gemini Flash interface
│   ├── ocr_engine.py               # Dual-pipeline PaddleOCR & native PDF engine
│   ├── pdf_generator.py            # Formal PDF audit report generator
│   ├── samples.py                  # Realistic Tamil Nadu sample datasets
│   ├── server.py                   # FastAPI REST API endpoints
│   ├── translator.py               # Bilingual Tamil/English transliteration layer
│   └── validator.py                # Survey number, date & DPDP Aadhaar validation
├── bin/llama-cpp/                  # (Auto-downloaded) llama.cpp server binaries
├── models/                         # (Auto-downloaded) Qwen2.5-7B-Instruct GGUF
├── static/
│   ├── app.js                      # Interactive frontend application logic
│   ├── index.html                  # Responsive UI layout & canvas viewer
│   └── style.css                   # Modern dashboard styling
├── requirements.txt                # Python runtime dependencies
├── run.py                          # FastAPI server startup entry point
├── setup_qwen_service.py           # Automated model & binary installer
├── start_app.bat                   # Web app launcher script
├── start_llama_server.bat          # llama-server optimized startup script
├── start_full_stack.bat            # 1-click batch launcher for Windows
├── start_full_stack.ps1            # 1-click PowerShell launcher
└── README.md
```

---

## 🛡️ Privacy & Security (DPDP Act Compliance)

- **Zero-Disk Retention**: All uploaded documents, scanned pages, and extracted text operate strictly in transient memory (`io.BytesIO`) and are immediately purged after processing.
- **Aadhaar Masking**: Aadhaar numbers are automatically masked (`XXXX-XXXX-1234`) according to Indian UIDAI and DPDP compliance standards.
- **Local Private Inference**: By default, all AI inferences run completely on your own machine offline via `llama.cpp`. No customer data leaves your computer.

---

## 📄 License & Attribution

Developed for Indian Real Estate legal scrutiny, title verification, and document intelligence. Built with FastAPI, PaddleOCR, and Qwen 2.5.
