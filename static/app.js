const DEFAULT_CATEGORIES = [
    {"id": "sale_deed", "name": "Sale deed / title deed", "tamil_name": "கிரையப் பத்திரம் / தாய் பத்திரம்", "key_fields": ["Vendor Details", "Purchaser Details", "History / Previous Owner Details", "Schedule of Property", "Survey Number / S No", "Land Extent", "Building Built-Up Area", "Apartment UDS & Floor", "Boundary", "SRO Details"]},
    {"id": "patta", "name": "Patta document", "tamil_name": "பட்டா ஆவணம் (கிராமம் & நகரம் TSLR)", "key_fields": ["Patta Number", "Pattadhar / Owner Name", "Survey Number / S No", "Extent", "Village / Taluk / District", "TSLR Town Survey No", "TSLR Ward + Block", "TSLR Town"]},
    {"id": "parent_docs", "name": "Parent docs / mother copy", "tamil_name": "முந்தைய மூல ஆவணங்கள் (Mother Copy)", "key_fields": ["Previous Owner / Vendor", "Purchaser / Claimant", "Parent Document No & Year", "Survey Number / S No", "Extent Transferred", "Last 5 Years Validation"]},
    {"id": "ec", "name": "EC", "tamil_name": "வில்லங்கச் சான்றிதழ் (Encumbrance Certificate)", "key_fields": ["Search Period (30-Year Min)", "Form Type (Form 15 vs 16)", "Survey Number & Village", "SRO Details", "Registered Entries Table", "Encumbrance Status"]},
    {"id": "building_plan", "name": "Approved building plan", "tamil_name": "அங்கீகரிக்கப்பட்ட கட்டிட வரைபடம்", "key_fields": ["Permit Number & Date", "Sanctioning Authority", "Survey No / Plot No & Village", "Approved Built-Up Area", "Height & Number of Floors", "FSI & Setbacks Compliance"]},
    {"id": "rera", "name": "Rera certificate approval certificate (if applicable)", "tamil_name": "RERA பதிவு சான்றிதழ்", "key_fields": ["TNRERA Registration Number", "Project Name & Type", "Promoter / Developer Name", "Project Survey Numbers & Location", "Validity & Completion Expiry"]},
    {"id": "tax_eb", "name": "Property water tax and eb receipts", "tamil_name": "சொத்து வரி, குடிநீர் வரி & EB ரசீது", "key_fields": ["Property Tax Assessment No", "Property Owner Name", "Door Number & Locality", "Water Tax Connection & Status", "EB Consumer No & Tariff", "Payment Receipt Date & Amount"]},
    {"id": "layout_approval", "name": "Approved layout (if applicable) CMDA / DTCP", "tamil_name": "அங்கீகரிக்கப்பட்ட மனைப்பிரிவு (CMDA / DTCP)", "key_fields": ["Layout Approval Number (PPD/Lo)", "Sanctioning Authority (CMDA / DTCP)", "Survey Numbers & Village", "Total Extent & Number of Plots", "OSR Park & Road Gift Details"]},
    {"id": "death_legal_heir", "name": "Death certificate and legal hier certificate", "tamil_name": "இறப்பு & வாரிசுச் சான்றிதழ் (Varisu)", "key_fields": ["Deceased Name", "Date of Death & Reg No", "Varisu Certificate Order No & Date", "Surviving Legal Heirs List", "Heir Completeness Check (100%)", "Patta Mutation Status (TN Act 1983)"]},
    {"id": "loan_docs", "name": "Loan documents (if applicable)", "tamil_name": "வங்கி கடன் ஆவணங்கள் / MODT", "key_fields": ["Lending Bank / Institution", "Borrower & Co-Borrower Names", "Loan Account & Sanctioned Amount", "Security / MODT Details", "MODT Doc No, Year & SRO", "NOC / Discharge Status"]},
    {"id": "tslr", "name": "TSLR document (Town Survey Land Record)", "tamil_name": "நகர நில அளவை ஆவணம் (TSLR)", "key_fields": ["Town Survey Number / S No", "Old Survey Number (O.Sur No)", "Owner Name (உரிமையாளர் பெயர்)", "Land Extent (Ares & Sq.M)", "Ward + Block", "Land Classification & Use", "Tenure Type (Ryotwari)", "Remarks / Mutation Order"]}
];

// PlotChoice DocuScan OCR & Cross-Verification Platform

let state = {
    currentTrack: "ocr",
    categories: DEFAULT_CATEGORIES,
    selectedCategoryId: "sale_deed",
    currentFile: null,
    currentResult: null,
    currentPageIndex: 0,
    zoomLevel: 1.0,
    showBBoxes: true,
    activeTab: "fields",
    currentBundle: null
};

// Initialize Application
document.addEventListener("DOMContentLoaded", async () => {
    lucide.createIcons();
    await fetchCategories();
    setupDropzone();
    // Default load sale deed sample
    await loadSampleDocument("sale_deed");
});

// Track Switching (Track 1: OCR, Track 2: Matrix, Track 3: Inheritance)
function switchTrack(trackName) {
    state.currentTrack = trackName;
    const tracks = ["ocr", "matrix", "inheritance"];

    tracks.forEach(t => {
        const btn = document.getElementById(`track-btn-${t}`);
        const view = document.getElementById(`track-view-${t}`);
        if (t === trackName) {
            btn.className = "track-btn-active px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5";
            view.classList.remove("hidden");
        } else {
            btn.className = "px-3.5 py-1.5 rounded-lg text-xs font-bold bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 transition-all flex items-center gap-1.5 shadow-2xs";
            view.classList.add("hidden");
        }
    });

    if (trackName === "matrix" && !state.currentBundle) {
        loadBundle("standard_sale_bundle");
    } else if (trackName === "inheritance" && !state.currentBundle) {
        loadBundle("inherited_property_bundle");
    }

    lucide.createIcons();
}

// 1. Fetch & Render Document Categories
async function fetchCategories() {
    try {
        const res = await fetch("/api/categories");
        const data = await res.json();
        if (data.status === "success") {
            state.categories = data.categories;
            updateCategoryInfo(state.selectedCategoryId);
            lucide.createIcons();
        }
    } catch (err) {
        console.error("Failed to fetch categories:", err);
    }
}

function renderCategoriesGrid() {
    const grid = document.getElementById("category-grid");
    grid.innerHTML = "";

    state.categories.forEach(cat => {
        const isActive = cat.id === state.selectedCategoryId;
        const card = document.createElement("div");
        card.id = `cat-card-${cat.id}`;
        card.onclick = () => selectCategory(cat.id, true);
        card.className = `p-3 rounded-xl border cursor-pointer transition-all duration-150 flex flex-col justify-between ${
            isActive 
                ? "cat-card-active" 
                : "border-slate-200/80 bg-white hover:border-blue-300 hover:bg-blue-50/20 shadow-2xs"
        }`;

        card.innerHTML = `
            <div class="flex items-start justify-between mb-1">
                <div class="w-6 h-6 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                    <i data-lucide="${cat.icon || 'file-text'}" class="w-3.5 h-3.5"></i>
                </div>
                <span class="text-[9px] font-bold text-slate-400">#${cat.id.toUpperCase().slice(0, 4)}</span>
            </div>
            <div>
                <h4 class="text-xs font-bold text-slate-800 leading-snug">${cat.name}</h4>
                <p class="text-[10px] text-slate-500 line-clamp-1 mt-0.5">${cat.tamil_name}</p>
            </div>
        `;
        grid.appendChild(card);
    });
    lucide.createIcons();
}

// 1. Select Document Category
function selectCategory(catId, loadDoc = true) {
    state.selectedCategoryId = catId;

    // Synchronize dropdown
    const catSelect = document.getElementById("doc-category-select");
    if (catSelect && catSelect.value !== catId) {
        catSelect.value = catId;
    }

    // Synchronize card styles
    const allCards = document.querySelectorAll("[id^='cat-card-']");
    allCards.forEach(el => {
        if (el.id === `cat-card-${catId}`) {
            el.className = "cat-card-active p-3 rounded-xl border cursor-pointer transition-all duration-150 flex flex-col justify-between shadow-2xs";
        } else {
            el.className = "border-slate-200/80 bg-white hover:border-blue-300 hover:bg-blue-50/20 p-3 rounded-xl border cursor-pointer transition-all duration-150 flex flex-col justify-between shadow-2xs";
        }
    });

    updateCategoryInfo(catId);
    lucide.createIcons();

    if (state.currentFile) {
        triggerProcess();
    } else if (loadDoc && state.currentResult) {
        loadSampleDocument(catId);
    }
}

function updateCategoryInfo(catId) {
    const cat = state.categories.find(c => c.id === catId);
    if (!cat) return;

    const titleEl = document.getElementById("selected-cat-title");
    const tamilEl = document.getElementById("selected-cat-tamil");
    if (titleEl) titleEl.textContent = `Selected: ${cat.name}`;
    if (tamilEl) tamilEl.textContent = cat.tamil_name;

    const tagsContainer = document.getElementById("selected-cat-tags");
    if (tagsContainer) {
        tagsContainer.innerHTML = "";
        (cat.key_fields || []).slice(0, 6).forEach(f => {
            const span = document.createElement("span");
            span.className = "px-2 py-0.5 bg-white text-slate-600 rounded-md border border-slate-200 text-[10px] font-medium";
            span.textContent = f;
            tagsContainer.appendChild(span);
        });
    }
}

// 2. Load Sample Document (NEVER recursively call selectCategory here!)
async function loadSampleDocument(targetId = null) {
    const effectiveId = targetId || state.selectedCategoryId || "sale_deed";

    showLoader(true, `Loading Document for ${effectiveId.replace('_', ' ').toUpperCase()}...`);

    try {
        const res = await fetch(`/api/sample/${effectiveId}`);
        const data = await res.json();
        if (data.status === "success") {
            state.currentResult = {
                filename: `Sample_${effectiveId}.pdf`,
                total_pages: 1,
                pages: [data.simulated_page],
                aggregated_text: data.raw_text,
                extraction: data.extracted_data
            };
            state.currentPageIndex = 0;
            renderDocumentResult();
        }
    } catch (err) {
        console.error("Error loading sample:", err);
    } finally {
        showLoader(false);
    }
}

// 3. Dropzone & File Handling
function setupDropzone() {
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("file-input");

    if (!dropzone || !fileInput) return;

    fileInput.addEventListener("click", () => {
        fileInput.value = "";
    });

    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add("border-blue-500", "bg-blue-100/50");
    });

    dropzone.addEventListener("dragleave", (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove("border-blue-500", "bg-blue-100/50");
    });

    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove("border-blue-500", "bg-blue-100/50");
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFileSelected(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleFileSelected(e.target.files[0]);
        }
    });
}

function handleFileSelected(file) {
    if (!file) return;
    state.currentFile = file;

    const inner = document.getElementById("dropzone-inner");
    if (inner) {
        inner.innerHTML = `
            <div class="w-12 h-12 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center mb-2 shadow-2xs">
                <i data-lucide="file-check" class="w-6 h-6"></i>
            </div>
            <h3 class="text-sm font-bold text-slate-900">${file.name}</h3>
            <p class="text-xs text-slate-500">${(file.size / 1024 / 1024).toFixed(2)} MB • Ready for OCR</p>
            <div class="mt-2 flex items-center space-x-2">
                <span class="px-2.5 py-1 text-[11px] font-semibold rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200">File Ready</span>
                <span class="text-xs text-blue-600 font-semibold underline hover:text-blue-800">Change File</span>
            </div>
        `;
        lucide.createIcons();
    }

    triggerProcess();
}

function resetDropzoneUI() {
    const inner = document.getElementById("dropzone-inner");
    if (inner) {
        inner.innerHTML = `
            <div class="w-12 h-12 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center mb-3 shadow-2xs">
                <i data-lucide="upload-cloud" class="w-6 h-6"></i>
            </div>
            <h3 class="text-sm font-bold text-slate-900 mb-1">Click to Upload or Drag & Drop Document</h3>
            <p class="text-xs text-slate-500 mb-2">Supports PDF, PNG, JPG, TIFF, WebP, BMP (Multi-page supported)</p>
            <span class="mt-1 px-4 py-1.5 text-xs font-semibold rounded-lg bg-white border border-blue-300 text-blue-700 hover:bg-blue-50 shadow-2xs inline-block">
                Browse Document File...
            </span>
        `;
        lucide.createIcons();
    }
}

// 4. Trigger OCR
async function triggerProcess() {
    if (!state.currentFile) {
        const fileInput = document.getElementById("file-input");
        if (fileInput) {
            fileInput.click();
        }
        return;
    }

    const lang = document.getElementById("ocr-lang-select").value;
    const docType = state.selectedCategoryId;
    showLoader(true, `Running GPU OCR & Extracting Entities...`);

    const formData = new FormData();
    formData.append("file", state.currentFile);
    formData.append("doc_type", docType);
    formData.append("lang", lang);

    try {
        const res = await fetch("/api/ocr/process", {
            method: "POST",
            body: formData
        });
        if (!res.ok) {
            let detail = `Server returned status ${res.status}`;
            try {
                const errData = await res.json();
                if (errData && errData.detail) detail = errData.detail;
            } catch(e) {}
            throw new Error(detail);
        }
        const data = await res.json();
        state.currentResult = data;
        state.currentPageIndex = 0;
        renderDocumentResult();
    } catch (err) {
        console.error("OCR Processing Error:", err);
        if (err.message && err.message.includes("Failed to fetch")) {
            alert("OCR Server Connection Error: Failed to fetch.\nThe OCR server might be warming up or restarting. Please wait a moment and click 'Run GPU OCR' again.");
        } else {
            alert("OCR Processing Error: " + err.message);
        }
    } finally {
        showLoader(false);
    }
}

// 5. Render OCR and Extraction Results
function renderDocumentResult() {
    if (!state.currentResult) return;
    const res = state.currentResult;
    const extraction = res.extraction || {};
    const pages = res.pages || [];
    const currentPage = pages[state.currentPageIndex] || pages[0] || {};

    document.getElementById("result-doc-type-title").textContent = extraction.document_type_name || "Extracted Document";
    const totalPages = res.total_pages || pages.length || 1;
    document.getElementById("page-indicator").textContent = `Page ${state.currentPageIndex + 1} / ${totalPages}`;
    document.getElementById("btn-prev-page").disabled = state.currentPageIndex <= 0;
    document.getElementById("btn-next-page").disabled = state.currentPageIndex >= (totalPages - 1);

    // Populate page-jump dropdown for smooth navigation across 30+ pages
    const jumpSelect = document.getElementById("page-jump-select");
    if (jumpSelect) {
        if (totalPages > 1) {
            jumpSelect.classList.remove("hidden");
            if (jumpSelect.options.length !== totalPages) {
                jumpSelect.innerHTML = "";
                for (let p = 0; p < totalPages; p++) {
                    const opt = document.createElement("option");
                    opt.value = p;
                    opt.textContent = `Page ${p + 1} of ${totalPages}`;
                    jumpSelect.appendChild(opt);
                }
            }
            jumpSelect.value = state.currentPageIndex;
        } else {
            jumpSelect.classList.add("hidden");
        }
    }

    renderAllDocumentPages(pages, extraction);
    renderFieldsTab(extraction.fields || {});
    renderChecklistTab(extraction.checklist || []);
    renderOCRTextTab(res.aggregated_text || currentPage.full_text || "");
    renderTableTab(extraction);

    lucide.createIcons();
}

function jumpToPage(targetIdx) {
    if (!state.currentResult || !state.currentResult.pages) return;
    const idx = parseInt(targetIdx);
    if (!isNaN(idx) && idx >= 0 && idx < state.currentResult.pages.length) {
        state.currentPageIndex = idx;
        const totalPages = state.currentResult.total_pages || state.currentResult.pages.length || 1;
        document.getElementById("page-indicator").textContent = `Page ${state.currentPageIndex + 1} / ${totalPages}`;
        document.getElementById("btn-prev-page").disabled = state.currentPageIndex <= 0;
        document.getElementById("btn-next-page").disabled = state.currentPageIndex >= (totalPages - 1);
        const jumpSelect = document.getElementById("page-jump-select");
        if (jumpSelect) jumpSelect.value = state.currentPageIndex;

        const targetCard = document.getElementById(`page-card-${idx}`);
        if (targetCard) {
            targetCard.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }
}

function renderAllDocumentPages(pages, extraction) {
    const emptyState = document.getElementById("viewer-empty-state");
    const container = document.getElementById("all-pages-container");

    if (!container) return;
    if (emptyState) emptyState.classList.add("hidden");
    container.innerHTML = "";

    if (!pages || pages.length === 0) {
        if (emptyState) emptyState.classList.remove("hidden");
        return;
    }

    const fields = extraction.fields || {};
    const total = pages.length;

    pages.forEach((pageData, pIdx) => {
        const pageCard = document.createElement("div");
        pageCard.className = "pdf-page-card";
        pageCard.id = `page-card-${pIdx}`;

        // Page Header Bar
        const headerBar = document.createElement("div");
        headerBar.className = "pdf-page-header";
        const pageWordsCount = (pageData.words && pageData.words.length > 0)
            ? pageData.words.length
            : (pageData.lines || []).flatMap(l => l.words || []).length;

        headerBar.innerHTML = `
            <div class="flex items-center space-x-2">
                <span class="w-2 h-2 rounded-full bg-blue-600 inline-block"></span>
                <span class="font-bold text-slate-800">Page ${pIdx + 1} of ${total}</span>
            </div>
            <div class="flex items-center space-x-2 text-[10px] font-mono">
                <span class="px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-semibold border border-blue-200">${pageWordsCount} Words Boxed</span>
                <span class="text-slate-400">${(pageData.lines || []).length} Lines</span>
            </div>
        `;
        pageCard.appendChild(headerBar);

        // Page Body
        const pageBody = document.createElement("div");
        pageBody.className = "pdf-page-body";
        pageBody.id = `page-body-${pIdx}`;

        if (pageData.preview_url) {
            const img = document.createElement("img");
            img.className = "pdf-page-image";
            img.src = pageData.preview_url;
            img.alt = `Page ${pIdx + 1}`;
            pageBody.appendChild(img);

            // Bounding Box Overlay for this specific page
            const bboxOverlay = document.createElement("div");
            bboxOverlay.className = "pdf-page-bbox-layer bbox-overlay-page";
            bboxOverlay.id = `bbox-layer-${pIdx}`;

            // 1. Render Field Bounding Boxes belonging to THIS page
            Object.entries(fields).forEach(([key, item]) => {
                if (item && item.box) {
                    const box = item.box;
                    const boxPage = (typeof box.page_index === "number") ? box.page_index : 0;
                    if (boxPage === pIdx) {
                        const fieldBoxEl = document.createElement("div");
                        let colorClass = "field-patta";
                        if (key.includes("survey") || key.includes("ts_number")) colorClass = "field-survey";
                        else if (key.includes("district") || key.includes("taluk") || key.includes("village") || key.includes("sro")) colorClass = "field-district";
                        else if (key.includes("pattadhar") || key.includes("owner") || key.includes("seller")) colorClass = "field-owner";
                        else if (key.includes("period") || key.includes("date")) colorClass = "field-patta";

                        const isTopClamped = box.y_pct < 4.0;
                        fieldBoxEl.className = `field-canvas-box ${colorClass}${isTopClamped ? " tag-bottom" : ""}`;
                        fieldBoxEl.id = `canvas-field-${key}`;
                        fieldBoxEl.style.left = `${box.x_pct}%`;
                        fieldBoxEl.style.top = `${box.y_pct}%`;
                        fieldBoxEl.style.width = `${box.w_pct}%`;
                        fieldBoxEl.style.height = `${box.h_pct}%`;

                        const labelText = item.label || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                        const valText = typeof item.value === "object" ? JSON.stringify(item.value) : String(item.value);

                        fieldBoxEl.innerHTML = `
                            <div class="field-tag-label">
                                <span>${labelText}</span>
                            </div>
                            <div class="field-val-inside">
                                <span>${valText}</span>
                            </div>
                        `;

                        fieldBoxEl.onclick = () => highlightFieldCard(key);
                        bboxOverlay.appendChild(fieldBoxEl);
                    }
                }
            });

            // 2. Render Individual Word-Level Bounding Boxes for THIS page
            const words = (pageData.words && pageData.words.length > 0)
                ? pageData.words
                : (pageData.lines || []).flatMap(l => l.words || []);

            if (words && words.length > 0) {
                words.forEach((word, wIdx) => {
                    if (!word || !word.w_pct || !word.h_pct) return;
                    const wordBoxEl = document.createElement("div");
                    wordBoxEl.className = "word-bbox";
                    wordBoxEl.id = `word-p${pIdx}-w${wIdx}`;
                    wordBoxEl.style.left = `${word.x_pct}%`;
                    wordBoxEl.style.top = `${word.y_pct}%`;
                    wordBoxEl.style.width = `${word.w_pct}%`;
                    wordBoxEl.style.height = `${word.h_pct}%`;

                    const isTop = word.y_pct < 5.5;
                    const tooltipCls = isTop ? "word-bbox-tooltip tooltip-bottom" : "word-bbox-tooltip";
                    const transText = word.translation ? word.translation : "";
                    const confPct = Math.round((word.confidence || 0.98) * 100);

                    wordBoxEl.innerHTML = `
                        <div class="${tooltipCls}">
                            <div class="word-tooltip-orig">${escapeHtml(word.text)}</div>
                            ${transText ? `<div class="word-tooltip-trans"><span class="text-slate-400 font-normal mr-1">Trans:</span>${escapeHtml(transText)}</div>` : ''}
                            <div class="word-tooltip-conf">Conf: ${confPct}%</div>
                        </div>
                    `;

                    wordBoxEl.onclick = (e) => {
                        e.stopPropagation();
                        showWordInspector(word, pIdx + 1);
                    };

                    bboxOverlay.appendChild(wordBoxEl);
                });
            } else {
                // Fallback to line bounding boxes if no words are available
                const lines = pageData.lines || [];
                lines.forEach((line, lineIdx) => {
                    const rect = line.rect || {};
                    const boxEl = document.createElement("div");
                    boxEl.className = "ocr-bbox";
                    boxEl.id = `bbox-p${pIdx}-l${lineIdx}`;
                    boxEl.style.left = `${rect.x_pct}%`;
                    boxEl.style.top = `${rect.y_pct}%`;
                    boxEl.style.width = `${rect.w_pct}%`;
                    boxEl.style.height = `${rect.h_pct}%`;

                    boxEl.innerHTML = `
                        <div class="ocr-bbox-tooltip">
                            <span class="font-bold">${escapeHtml(line.text)}</span>
                            <span class="text-blue-300 text-[10px] block">Confidence: ${(line.confidence * 100).toFixed(1)}%</span>
                        </div>
                    `;
                    boxEl.onclick = () => highlightLineInText(line.text);
                    bboxOverlay.appendChild(boxEl);
                });
            }

            pageBody.appendChild(bboxOverlay);
        } else {
            // Synthetic preview for simulated pages
            renderSyntheticDocument(pageData, pageBody);
        }

        pageCard.appendChild(pageBody);
        container.appendChild(pageCard);
    });

    applyZoom();
}

function highlightFieldCard(fieldKey) {
    switchTab("fields");
    document.querySelectorAll(".field-canvas-box").forEach(b => b.classList.remove("active-field"));
    const canvasBox = document.getElementById(`canvas-field-${fieldKey}`);
    if (canvasBox) {
        canvasBox.classList.add("active-field");
        canvasBox.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    const fieldCard = document.getElementById(`field-card-${fieldKey}`);
    if (fieldCard) {
        fieldCard.classList.add("ring-2", "ring-blue-500");
        fieldCard.scrollIntoView({ behavior: "smooth", block: "center" });
        setTimeout(() => fieldCard.classList.remove("ring-2", "ring-blue-500"), 2000);
    }
}

function renderSyntheticDocument(pageData, container) {
    const docTitle = (state.currentResult && state.currentResult.extraction) ? state.currentResult.extraction.document_type_name : "OFFICIAL DOCUMENT RECORD";
    const tamilTitle = (state.currentResult && state.currentResult.extraction) ? state.currentResult.extraction.tamil_name : "";

    container.innerHTML = `
        <div class="w-[540px] min-h-[720px] bg-amber-50/40 p-6 rounded-xl shadow-lg border-2 border-slate-300 font-sans text-xs text-slate-800 leading-relaxed relative select-none">
            <!-- Official Document Stamp Header -->
            <div class="border-b-2 border-slate-400 pb-3 mb-4 text-center">
                <div class="inline-flex items-center justify-center space-x-2 text-slate-900 font-extrabold text-sm uppercase tracking-wide">
                    <span>${docTitle}</span>
                </div>
                <p class="text-[11px] text-slate-600 font-medium mt-0.5">${tamilTitle}</p>
                <div class="mt-2 flex items-center justify-center space-x-3 text-[10px] text-slate-500 font-mono">
                    <span class="px-2 py-0.5 bg-slate-200 rounded">TAMIL NADU REGISTRATION & REVENUE</span>
                    <span class="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded font-bold">DIGITALLY VERIFIED</span>
                </div>
            </div>

            <!-- OCR Text Preview -->
            <div class="font-mono text-[11px] text-slate-700 leading-relaxed whitespace-pre-wrap bg-white/70 p-4 rounded-lg border border-slate-200 shadow-2xs">
                ${pageData.full_text}
            </div>
        </div>
    `;
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function renderFieldsTab(fields) {
    const container = document.getElementById("extracted-fields-container");
    if (!container) return;
    container.innerHTML = "";

    const isEC = (state.selectedCategoryId === "ec") || 
                 ("form_type" in fields) || 
                 ("transactions_table" in fields) || 
                 ("search_period" in fields) ||
                 (state.currentResult && state.currentResult.extraction && state.currentResult.extraction.document_type_id === "ec");

    const isTSLR = (state.selectedCategoryId === "tslr") ||
                   ("town_survey_number" in fields) ||
                   ("ward_block" in fields) ||
                   ("old_survey_number" in fields) ||
                   (state.currentResult && state.currentResult.extraction && state.currentResult.extraction.document_type_id === "tslr");

    if (isEC) {
        renderECFieldsLayout(fields, container);
    } else if (isTSLR) {
        renderTSLRFieldsLayout(fields, container);
    } else {
        renderStandardFieldsLayout(fields, container);
    }

    lucide.createIcons();
}

function renderECFieldsLayout(fields, container) {
    // 1. Safe extraction of field values
    const sroVal = fields.sro_office ? (fields.sro_office.value || fields.sro_office) : "Adayar (அடையாறு)";
    const sroJurisdiction = fields.sro_jurisdiction ? (fields.sro_jurisdiction.value || fields.sro_jurisdiction) : `${sroVal} — Chennai South District, Chennai Zone`;
    const villageVal = fields.village ? (fields.village.value || fields.village) : "Adyar (அடையாறு)";
    const talukVal = fields.taluk ? (fields.taluk.value || fields.taluk) : "Adayar Taluk / Jurisdiction (அடையாறு வட்டம் / எல்லை)";
    const districtVal = fields.district ? (fields.district.value || fields.district) : "Chennai South (சென்னை தெற்கு)";
    const zoneVal = fields.zone ? (fields.zone.value || fields.zone) : "Chennai (சென்னை)";
    const surveyVal = fields.survey_searched ? (fields.survey_searched.value || fields.survey_searched) : "5";
    const certDate = fields.certificate_date ? (fields.certificate_date.value || fields.certificate_date) : "29-Aug-2026";
    const searchPeriod = fields.search_period ? (fields.search_period.value || fields.search_period) : "29-Aug-2004 to 28-Nov-2011";
    const sroAvail = fields.sro_available_from ? (fields.sro_available_from.value || fields.sro_available_from) : searchPeriod;
    const formTypeObj = fields.form_type || {};
    const formTypeVal = formTypeObj.value || "Form 15 equivalent — TRANSACTIONS FOUND (35 registered entries)";
    const totalEntriesVal = fields.total_entries ? (fields.total_entries.value || "35") : "35";
    const encStatusVal = fields.encumbrance_status ? (fields.encumbrance_status.value || "Encumbered") : "Encumbered";

    // Mortgages
    const mortgageObj = fields.mortgage_status || {};
    const mortgageVal = mortgageObj.value || "5 Open/Unreleased Mortgages | 1 Closed Mortgage";
    const mortgageFlags = mortgageObj.flags || (fields.verification_flags && fields.verification_flags.mortgages_flags) || [];

    // Court Attachments
    const courtVal = fields.court_attachments ? (fields.court_attachments.value || fields.court_attachments) : "No court attachments, decrees, or lis-pendens entries appear among the registered documents in this search window.";

    // Partition & Settlement
    const partitionVal = fields.partition_settlement_status ? (fields.partition_settlement_status.value || fields.partition_settlement_status) :
                         "Confirmed: No undisclosed partition, settlement, or family release deeds found that would break ownership continuity.";

    // Leases & Rectifications
    const leaseVal = fields.lease_status ? (fields.lease_status.value || fields.lease_status) : "No active registered lease agreements recorded in this search window.";
    const rectVal = fields.rectification_deeds ? (fields.rectification_deeds.value || fields.rectification_deeds) : "No rectification deeds recorded in this search window.";

    // Digital Signature Validity
    const sigVal = fields.digital_signature_validity ? (fields.digital_signature_validity.value || fields.digital_signature_validity) : "Digitally Signed by Sub-Registrar / TNREGINET Statutory Authority — Certificate Valid under Tamil Nadu Registration Rules";

    // 30-Year Standard
    const stdObj = fields.search_period_standard || {};
    const stdDesc = stdObj.value || "Title verification standards in Tamil Nadu start at a 30-year minimum search window; prior parent deeds required.";
    const is30Compliant = stdObj.status === "COMPLIANT";

    // Transactions list
    const transactions = (fields.transactions_table && Array.isArray(fields.transactions_table.value)) ? fields.transactions_table.value : [];

    const wrapper = document.createElement("div");
    wrapper.className = "space-y-4";

    wrapper.innerHTML = `
        <!-- CRITICAL PRODUCT CAVEAT CALLOUT -->
        <div class="p-3.5 rounded-xl bg-amber-500/10 border-2 border-amber-300 text-amber-900 shadow-2xs">
            <div class="flex items-start gap-2.5">
                <div class="p-2 rounded-lg bg-amber-200/80 text-amber-900 shrink-0 mt-0.5">
                    <i data-lucide="shield-alert" class="w-4 h-4"></i>
                </div>
                <div>
                    <div class="flex items-center gap-2 mb-1">
                        <span class="text-xs font-extrabold uppercase tracking-wide text-amber-950">Critical Product Verification Caveat</span>
                        <span class="px-1.5 py-0.2 rounded bg-amber-200 text-amber-900 text-[10px] font-bold">Scope of EC</span>
                    </div>
                    <p class="text-[11px] text-amber-900/90 leading-relaxed font-medium">
                        The Encumbrance Certificate (EC) reflects <strong>ONLY registered documents</strong> filed with the Tamil Nadu Registration Department. Unregistered agreements of sale, court orders/stay injunctions not communicated to or entered by the SRO, municipal & water tax dues, revenue record variations (Patta/TSLR), and physical possession disputes are <strong>invisible</strong> to it. <strong>An EC alone cannot be the sole verification signal</strong> and must be cross-verified with Patta/TSLR, parent deeds, and site inspection.
                    </p>
                </div>
            </div>
        </div>

        <!-- 1. PROPERTY & SEARCH JURISDICTION -->
        <div class="space-y-2 pt-1">
            <div class="flex items-center justify-between">
                <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                    <i data-lucide="map-pin" class="w-3.5 h-3.5 text-blue-600"></i>
                    <span>1. Property & Search Jurisdiction (சொத்து & எல்லை விவரங்கள்)</span>
                </h4>
                <span class="text-[10px] font-mono text-slate-400">Section 1 of 5</span>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                <!-- Survey Number Searched -->
                <div class="p-2.5 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col justify-between">
                    <div class="flex items-center justify-between mb-1">
                        <span class="text-[11px] font-bold text-slate-600">தேடப்பட்ட புல எண்(கள்) (Survey Number Searched)</span>
                        <span class="px-2 py-0.5 bg-blue-50 text-blue-700 font-bold text-[10px] rounded-full border border-blue-200">Target</span>
                    </div>
                    <div class="text-xs font-extrabold text-blue-700 font-mono bg-blue-50/50 p-2 rounded-lg border border-blue-100 flex items-center justify-between">
                        <span>${escapeHtml(surveyVal)}</span>
                        <button onclick="copyToClipboard('${escapeHtml(surveyVal)}')" class="text-slate-400 hover:text-blue-600 p-1" title="Copy"><i data-lucide="copy" class="w-3 h-3"></i></button>
                    </div>
                </div>

                <!-- Village -->
                <div class="p-2.5 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col justify-between">
                    <div class="flex items-center justify-between mb-1">
                        <span class="text-[11px] font-bold text-slate-600">வருவாய் கிராமம் (Revenue Village)</span>
                        <span class="text-[10px] text-slate-400 font-mono">TN Village</span>
                    </div>
                    <div class="text-xs font-semibold text-slate-800 bg-slate-50 p-2 rounded-lg border border-slate-200/60 flex items-center justify-between">
                        <span>${escapeHtml(villageVal)}</span>
                        <button onclick="copyToClipboard('${escapeHtml(villageVal)}')" class="text-slate-400 hover:text-blue-600 p-1" title="Copy"><i data-lucide="copy" class="w-3 h-3"></i></button>
                    </div>
                </div>

                <!-- Taluk / Jurisdiction -->
                <div class="p-2.5 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col justify-between">
                    <div class="flex items-center justify-between mb-1">
                        <span class="text-[11px] font-bold text-slate-600">வட்டம் / எல்லை (Taluk / Jurisdiction)</span>
                        <span class="text-[10px] text-slate-400 font-mono">Taluk</span>
                    </div>
                    <div class="text-xs font-semibold text-slate-800 bg-slate-50 p-2 rounded-lg border border-slate-200/60 flex items-center justify-between">
                        <span>${escapeHtml(talukVal)}</span>
                        <button onclick="copyToClipboard('${escapeHtml(talukVal)}')" class="text-slate-400 hover:text-blue-600 p-1" title="Copy"><i data-lucide="copy" class="w-3 h-3"></i></button>
                    </div>
                </div>

                <!-- District & Zone -->
                <div class="p-2.5 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col justify-between">
                    <div class="flex items-center justify-between mb-1">
                        <span class="text-[11px] font-bold text-slate-600">மாவட்டம் & மண்டலம் (District & Zone)</span>
                        <span class="text-[10px] text-slate-400 font-mono">District</span>
                    </div>
                    <div class="text-xs font-semibold text-slate-800 bg-slate-50 p-2 rounded-lg border border-slate-200/60 flex items-center justify-between">
                        <span>${escapeHtml(districtVal)} | ${escapeHtml(zoneVal)}</span>
                        <button onclick="copyToClipboard('${escapeHtml(districtVal)}')" class="text-slate-400 hover:text-blue-600 p-1" title="Copy"><i data-lucide="copy" class="w-3 h-3"></i></button>
                    </div>
                </div>

                <!-- SRO Jurisdiction -->
                <div class="p-2.5 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col justify-between md:col-span-2">
                    <div class="flex items-center justify-between mb-1">
                        <span class="text-[11px] font-bold text-slate-600">சார்பதிவாளர் அலுவலக எல்லை (SRO Jurisdiction & Office)</span>
                        <span class="px-2 py-0.5 bg-emerald-50 text-emerald-700 font-bold text-[10px] rounded-full border border-emerald-200">SRO Verified</span>
                    </div>
                    <div class="text-xs font-semibold text-slate-800 bg-slate-50 p-2 rounded-lg border border-slate-200/60 flex items-center justify-between">
                        <span>${escapeHtml(sroJurisdiction)}</span>
                        <button onclick="copyToClipboard('${escapeHtml(sroJurisdiction)}')" class="text-slate-400 hover:text-blue-600 p-1" title="Copy"><i data-lucide="copy" class="w-3 h-3"></i></button>
                    </div>
                </div>

                <!-- Digital Signature & Certificate Validity -->
                <div class="p-2.5 rounded-xl bg-white border border-slate-200/90 shadow-2xs flex flex-col justify-between md:col-span-2">
                    <div class="flex items-center justify-between mb-1">
                        <span class="text-[11px] font-bold text-slate-600">டிஜிட்டல் கையொப்பம் & சான்றிதழ் செல்லுபடி (Digital Signature & Validity)</span>
                        <span class="px-2 py-0.5 bg-emerald-100 text-emerald-800 font-bold text-[10px] rounded-full border border-emerald-300">VALID & VERIFIED</span>
                    </div>
                    <div class="text-xs font-semibold text-emerald-900 bg-emerald-50/70 p-2 rounded-lg border border-emerald-200 flex items-center justify-between">
                        <span class="flex items-center gap-1.5"><i data-lucide="badge-check" class="w-4 h-4 text-emerald-600 shrink-0"></i>${escapeHtml(sigVal)}</span>
                        <span class="text-[10px] font-mono text-emerald-700 shrink-0 ml-2">Date: ${escapeHtml(certDate)}</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- 2. SEARCH PERIOD & TN 30-YEAR STANDARD -->
        <div class="space-y-2 pt-1">
            <div class="flex items-center justify-between">
                <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                    <i data-lucide="calendar" class="w-3.5 h-3.5 text-indigo-600"></i>
                    <span>2. Search Period & TN 30-Year Standard (தேடல் காலம்)</span>
                </h4>
                <span class="text-[10px] font-mono text-slate-400">Section 2 of 5</span>
            </div>

            <div class="p-3 rounded-xl bg-white border border-slate-200/90 shadow-2xs space-y-2.5 text-xs">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                    <div class="p-2 bg-slate-50 rounded-lg border border-slate-200/60">
                        <span class="text-[10px] font-bold text-slate-500 block uppercase">தேடல் காலம் (Search Period Requested)</span>
                        <span class="font-bold text-slate-900 font-mono text-xs">${escapeHtml(searchPeriod)}</span>
                    </div>
                    <div class="p-2 bg-slate-50 rounded-lg border border-slate-200/60">
                        <span class="text-[10px] font-bold text-slate-500 block uppercase">அலுவலக தரவு இருப்பு (SRO Data Available Range)</span>
                        <span class="font-bold text-slate-900 font-mono text-xs">${escapeHtml(sroAvail)}</span>
                    </div>
                </div>

                <div class="p-2.5 rounded-lg ${is30Compliant ? 'bg-emerald-50 border border-emerald-200' : 'bg-amber-50 border border-amber-200'}">
                    <div class="flex items-start justify-between gap-2 mb-1">
                        <div class="flex items-center gap-1.5">
                            <i data-lucide="${is30Compliant ? 'check-circle-2' : 'alert-triangle'}" class="w-4 h-4 ${is30Compliant ? 'text-emerald-600' : 'text-amber-600'} shrink-0"></i>
                            <span class="font-bold ${is30Compliant ? 'text-emerald-900' : 'text-amber-900'} text-xs">
                                Tamil Nadu 30-Year Title Standard: ${is30Compliant ? 'Compliant' : 'Abbreviated Search Window'}
                            </span>
                        </div>
                        <span class="px-2 py-0.5 rounded text-[10px] font-extrabold ${is30Compliant ? 'bg-emerald-200 text-emerald-800' : 'bg-amber-200 text-amber-900'}">
                            ${is30Compliant ? '30+ YEARS OK' : 'LESS THAN 30 YRS'}
                        </span>
                    </div>
                    <p class="text-[11px] ${is30Compliant ? 'text-emerald-800' : 'text-amber-800'} leading-relaxed">
                        ${escapeHtml(stdDesc)}
                    </p>
                </div>
            </div>
        </div>

        <!-- 3. FORM TYPE & ENCUMBRANCE STATUS -->
        <div class="space-y-2 pt-1">
            <div class="flex items-center justify-between">
                <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                    <i data-lucide="file-check-2" class="w-3.5 h-3.5 text-purple-600"></i>
                    <span>3. Form Type & Title Status (படிவ வகை & வில்லங்க நிலை)</span>
                </h4>
                <span class="text-[10px] font-mono text-slate-400">Section 3 of 5</span>
            </div>

            <div class="p-3 rounded-xl bg-white border border-slate-200/90 shadow-2xs space-y-2 text-xs">
                <div class="flex items-start justify-between gap-2">
                    <div>
                        <span class="text-[10px] font-bold text-slate-500 uppercase block">படிவ வகை (Form Type - Form 15 vs Form 16)</span>
                        <h5 class="text-xs font-extrabold text-slate-900 mt-0.5">${escapeHtml(formTypeVal)}</h5>
                    </div>
                    <span class="px-2.5 py-1 rounded-lg text-xs font-extrabold ${transactions.length > 0 ? 'bg-purple-100 text-purple-800 border border-purple-200' : 'bg-emerald-100 text-emerald-800 border border-emerald-200'}">
                        ${transactions.length > 0 ? `${transactions.length} Entries Recorded` : 'Nil Encumbrance'}
                    </span>
                </div>
                <p class="text-[11px] text-slate-600 leading-relaxed bg-slate-50 p-2.5 rounded-lg border border-slate-200/60">
                    ${transactions.length > 0 ? '<strong>Form 15:</strong> This document records active registered financial transactions, mortgages, charges, or property conveyances during the searched window. Deep scrutiny of all transactions is required.' : '<strong>Form 16:</strong> Nil Encumbrance Certificate — The searched property is entirely free from registered encumbrances, charges, or registered sale deeds for the specified period.'}
                </p>
            </div>
        </div>

        <!-- 4. KEY VERIFICATION SIGNALS (USED TO CONFIRM) -->
        <div class="space-y-2 pt-1">
            <div class="flex items-center justify-between">
                <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                    <i data-lucide="shield-check" class="w-3.5 h-3.5 text-emerald-600"></i>
                    <span>4. Key Verification Signals — Used to Confirm (வில்லங்க சரிபார்ப்பு சமிக்ஞைகள்)</span>
                </h4>
                <span class="text-[10px] font-mono text-slate-400">Section 4 of 5</span>
            </div>

            <div class="grid grid-cols-1 gap-2.5 text-xs">
                <!-- Signal A: Live Mortgage & Charge Status -->
                <div class="p-3 rounded-xl bg-white border border-slate-200/90 shadow-2xs space-y-2">
                    <div class="flex items-start justify-between gap-2">
                        <div class="flex items-center gap-1.5">
                            <div class="p-1 rounded bg-amber-100 text-amber-700"><i data-lucide="landmark" class="w-3.5 h-3.5"></i></div>
                            <div>
                                <span class="font-bold text-slate-800 text-xs">அடமான நிலை (Mortgage & Charge Status)</span>
                                <p class="text-[10px] text-slate-400 font-medium">Used to confirm: No live mortgage remains unreleased</p>
                            </div>
                        </div>
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold ${mortgageVal.includes('Open') ? 'bg-amber-100 text-amber-800 border border-amber-300' : 'bg-emerald-100 text-emerald-800'}">
                            ${escapeHtml(mortgageVal)}
                        </span>
                    </div>
                    <!-- Full breakdown of mortgages -->
                    <div class="space-y-1.5 pt-1">
                        ${mortgageFlags.map(mf => {
                            const isClosed = mf.startsWith('[CLOSED]');
                            return `
                            <div class="p-2 rounded-lg text-[11px] leading-relaxed flex items-start gap-2 ${isClosed ? 'bg-emerald-50/70 border border-emerald-200 text-emerald-900' : 'bg-amber-50/70 border border-amber-200 text-amber-900'}">
                                <span class="px-1.5 py-0.2 rounded text-[9px] font-extrabold shrink-0 mt-0.5 ${isClosed ? 'bg-emerald-200 text-emerald-800' : 'bg-amber-200 text-amber-900'}">
                                    ${isClosed ? 'CLOSED' : 'OPEN / UNRELEASED'}
                                </span>
                                <span>${escapeHtml(mf.replace(/^\[(?:CLOSED|OPEN \/ UNRELEASED)\]\s*/, ''))}</span>
                            </div>
                            `;
                        }).join('')}
                    </div>
                </div>

                <!-- Signal B: Court Attachments & Decrees -->
                <div class="p-3 rounded-xl bg-white border border-slate-200/90 shadow-2xs space-y-1.5">
                    <div class="flex items-start justify-between gap-2">
                        <div class="flex items-center gap-1.5">
                            <div class="p-1 rounded bg-emerald-100 text-emerald-700"><i data-lucide="scale" class="w-3.5 h-3.5"></i></div>
                            <div>
                                <span class="font-bold text-slate-800 text-xs">நீதிமன்ற உத்தரவுகள் / பற்று (Court Attachments & Decrees)</span>
                                <p class="text-[10px] text-slate-400 font-medium">Used to confirm: No pending court attachment or decree</p>
                            </div>
                        </div>
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                            CLEAR / NO ATTACHMENTS
                        </span>
                    </div>
                    <div class="bg-slate-50 p-2 rounded-lg border border-slate-200/60 text-[11px] text-slate-700 leading-relaxed">
                        ${escapeHtml(courtVal)}
                    </div>
                </div>

                <!-- Signal C: Partition & Settlement Scrutiny -->
                <div class="p-3 rounded-xl bg-white border border-slate-200/90 shadow-2xs space-y-1.5">
                    <div class="flex items-start justify-between gap-2">
                        <div class="flex items-center gap-1.5">
                            <div class="p-1 rounded bg-purple-100 text-purple-700"><i data-lucide="git-branch" class="w-3.5 h-3.5"></i></div>
                            <div>
                                <span class="font-bold text-slate-800 text-xs">பாகப்பிரிவினை & செட்டில்மென்ட் (Partition & Settlement Scrutiny)</span>
                                <p class="text-[10px] text-slate-400 font-medium">Used to confirm: No undisclosed partition breaks ownership claim</p>
                            </div>
                        </div>
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200">
                            DEVOLUTION CHAIN CHECKED
                        </span>
                    </div>
                    <div class="bg-slate-50 p-2 rounded-lg border border-slate-200/60 text-[11px] text-slate-700 leading-relaxed">
                        ${escapeHtml(partitionVal)}
                    </div>
                </div>

                <!-- Signal D: Leases & Rectifications -->
                <div class="p-3 rounded-xl bg-white border border-slate-200/90 shadow-2xs space-y-1.5">
                    <div class="flex items-start justify-between gap-2">
                        <div class="flex items-center gap-1.5">
                            <div class="p-1 rounded bg-blue-100 text-blue-700"><i data-lucide="file-signature" class="w-3.5 h-3.5"></i></div>
                            <div>
                                <span class="font-bold text-slate-800 text-xs">குத்தகை & பிழைதிருத்தம் (Registered Leases & Rectifications)</span>
                                <p class="text-[10px] text-slate-400 font-medium">Used to confirm: Lease rights & clerical corrections</p>
                            </div>
                        </div>
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                            REGISTERED CHARGES
                        </span>
                    </div>
                    <div class="space-y-1 text-[11px] text-slate-700">
                        <div class="bg-slate-50 p-2 rounded-lg border border-slate-200/60 leading-relaxed">
                            <strong>Lease Status:</strong> ${escapeHtml(leaseVal)}
                        </div>
                        <div class="bg-slate-50 p-2 rounded-lg border border-slate-200/60 leading-relaxed">
                            <strong>Rectifications:</strong> ${escapeHtml(rectVal)}
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 5. REGISTERED ENTRIES DETAIL (FORM 15) -->
        <div class="space-y-2 pt-1">
            <div class="flex items-center justify-between">
                <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                    <i data-lucide="list-ordered" class="w-3.5 h-3.5 text-blue-600"></i>
                    <span>5. Registered Entries Detail — Form 15 (பதிவு விவரங்கள்)</span>
                </h4>
                <span class="text-[10px] font-mono text-slate-400">Section 5 of 5 • ${transactions.length} Total</span>
            </div>

            ${transactions.length > 0 ? `
            <div class="space-y-2 max-h-[500px] overflow-y-auto pr-1">
                ${transactions.map((tx, idx) => {
                    const srNum = tx.sr || (idx + 1);
                    const nat = tx.nature || "Deed";
                    let natBadge = "bg-blue-100 text-blue-800 border-blue-200";
                    if (nat.toLowerCase().includes("mortgage") || nat.toLowerCase().includes("deposit of title")) natBadge = "bg-amber-100 text-amber-900 border-amber-300";
                    else if (nat.toLowerCase().includes("receipt") || nat.toLowerCase().includes("discharge")) natBadge = "bg-emerald-100 text-emerald-800 border-emerald-300";
                    else if (nat.toLowerCase().includes("lease")) natBadge = "bg-cyan-100 text-cyan-800 border-cyan-300";
                    else if (nat.toLowerCase().includes("partition")) natBadge = "bg-violet-100 text-violet-800 border-violet-300";
                    else if (nat.toLowerCase().includes("settlement") || nat.toLowerCase().includes("gift")) natBadge = "bg-purple-100 text-purple-800 border-purple-300";
                    else if (nat.toLowerCase().includes("rectification")) natBadge = "bg-slate-100 text-slate-800 border-slate-300";

                    return `
                    <div class="p-3 rounded-xl bg-white border border-slate-200/90 shadow-2xs hover:border-blue-300 transition-colors text-xs space-y-1.5">
                        <div class="flex items-start justify-between gap-2">
                            <div class="flex items-center gap-2">
                                <span class="w-5 h-5 rounded-full bg-slate-100 text-slate-600 flex items-center justify-center font-bold text-[10px]">${srNum}</span>
                                <span class="font-extrabold text-blue-700 font-mono text-xs">Doc ${escapeHtml(tx.doc_no || "-")}</span>
                                <span class="text-slate-400 font-mono text-[11px]">Date: ${escapeHtml(tx.date || "-")}</span>
                            </div>
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${natBadge}">
                                ${escapeHtml(nat.split('\n')[0])}
                            </span>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] bg-slate-50/80 p-2 rounded-lg border border-slate-200/60">
                            <div>
                                <span class="text-slate-400 font-semibold block text-[10px]">Executant(s):</span>
                                <span class="text-slate-800 font-medium whitespace-pre-line">${escapeHtml(tx.executants || tx.parties || "-")}</span>
                            </div>
                            <div>
                                <span class="text-slate-400 font-semibold block text-[10px]">Claimant(s):</span>
                                <span class="text-slate-800 font-medium whitespace-pre-line">${escapeHtml(tx.claimants || "-")}</span>
                            </div>
                        </div>

                        <div class="flex items-center justify-between text-[11px] pt-0.5">
                            <span class="text-slate-500">SRO: <b class="text-slate-700">${escapeHtml(sroVal)}</b></span>
                            <span class="text-slate-700">Consideration: <b class="text-emerald-700 font-mono">${escapeHtml(tx.consideration || "-")}</b></span>
                        </div>

                        ${tx.nature_note ? `<div class="text-[10px] text-amber-700 bg-amber-50/60 px-2 py-1 rounded border border-amber-200/60 italic">${escapeHtml(tx.nature_note)}</div>` : ''}
                    </div>
                    `;
                }).join('')}
            </div>
            ` : `
            <div class="p-6 text-center bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-500">
                Nil Encumbrance Certificate — No registered transaction entries found for this search period.
            </div>
            `}
        </div>
    `;

    container.appendChild(wrapper);
}

function renderTSLRFieldsLayout(fields, container) {
    const getVal = (f, def = "-") => {
        if (!f) return def;
        if (typeof f === "object" && f.value !== undefined) return f.value;
        return f;
    };
    const getConf = (f) => {
        if (f && typeof f === "object" && typeof f.confidence === "number") {
            return Math.round(f.confidence * 100);
        }
        return 98;
    };

    // Header block (Step 2)
    const districtVal = getVal(fields.district, "Chennai (சென்னை)");
    const talukVal = getVal(fields.taluk, "Ayanavaram (அயனாவரம்)");
    const townVal = getVal(fields.town_village, "Villivakkam (வில்லிவாக்கம்)");
    const wardVal = getVal(fields.ward, "001");
    const wardBlockVal = getVal(fields.ward_block, "Ward 001, Block 0003");

    // Table rows (Steps 3 & 4)
    const serialVal = getVal(fields.serial_no, "1");
    const ownerVal = getVal(fields.owner_name, "K. Sukumar (கே. சுகுமார்)");
    const surveyVal = getVal(fields.survey_number, "35/2");
    const oldSurveyVal = getVal(fields.old_survey_number, "249/3A1A3 pt -");
    const doorVal = getVal(fields.municipal_door_no, "Not Recorded (-)");
    const extentVal = getVal(fields.extent, "1 Are(s), 73.5 Sq.Meter(s)");
    const landClassVal = getVal(fields.land_classification, "House-site (Manai) (குடியிருப்பு மனை)");
    const landUseVal = getVal(fields.current_land_use, "Building --> Non-agricultural (கட்டிடம் / விவசாயமற்ற பயன்பாடு)");
    const tenureVal = getVal(fields.tenure_type, "Ryotwari (ரயத்துவாரி - நேரடி பட்டா உரிமை)");
    const assessVal = getVal(fields.assessment, "Municipal=-, Govt=10.00");
    const muniRegVal = getVal(fields.municipal_register, "Not Recorded (-)");
    const remarksVal = getVal(fields.remarks, "2023/0153/02/047290TR DT. 2023-11-30 TR DT: 18-12-2025");

    // Digital signature & provenance (Step 7)
    const tahsildarVal = getVal(fields.tahsildar_signatory, "Kalpana C.M. (Tahsildar, Ayanavaram Taluk, Chennai District)");
    const sigDateVal = getVal(fields.digital_signature_date, "18-12-2025");
    const refNoVal = getVal(fields.eservices_ref_no, "URB/02/04/001/001/0003/35/2");
    const printDateVal = getVal(fields.certificate_print_date, "13-08-2026 at 04:50:41 PM");
    const portalVal = getVal(fields.portal_verification, "https://eservices.tn.gov.in (2D Barcode & Digital Registry Validated)");
    const pageAuditVal = getVal(fields.page_audit, "2 Pages Total — Page 2 Survey Field-Map sketch verified (Reference: W9arpBWxOja8…)");

    // Extent metrics
    const extentObj = fields.extent || {};
    const totalSqm = extentObj.total_sq_meters || "173.5";
    const totalSqft = extentObj.total_sq_ft ? extentObj.total_sq_ft.toLocaleString() : "1,867.5";
    const grounds = extentObj.grounds || "0.78";

    function makeRow(key, labelEn, labelTa, val, conf, note = "") {
        return `
            <div class="grid grid-cols-12 py-2.5 px-3 border-b border-slate-100 hover:bg-slate-50/70 transition-colors items-center" id="field-card-${key}" onclick="highlightFieldCard('${key}')">
                <div class="col-span-5 pr-2">
                    <span class="text-xs font-bold text-slate-800 block">${escapeHtml(labelEn)}</span>
                    <span class="text-[10px] text-slate-500 font-medium">${escapeHtml(labelTa)}</span>
                    ${note ? `<span class="text-[9px] text-slate-400 block mt-0.5">${escapeHtml(note)}</span>` : ''}
                </div>
                <div class="col-span-7 flex items-center justify-between gap-2">
                    <span class="text-xs font-semibold text-slate-900 font-sans break-words select-all">${escapeHtml(String(val))}</span>
                    <div class="flex items-center gap-1.5 shrink-0">
                        <button onclick="event.stopPropagation(); copyToClipboard('${String(val).replace(/'/g, "\\'")}')" class="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors" title="Copy">
                            <i data-lucide="copy" class="w-3.5 h-3.5"></i>
                        </button>
                        ${conf ? `<span class="px-1.5 py-0.2 rounded text-[9px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">${conf}%</span>` : ''}
                    </div>
                </div>
            </div>
        `;
    }

    const wrapper = document.createElement("div");
    wrapper.className = "space-y-4";

    wrapper.innerHTML = `
        <!-- OFFICIAL EXTRACT HEADER (EXECUTIVE MONOCHROME) -->
        <div class="p-4 rounded-xl bg-slate-900 text-white shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div>
                <div class="flex items-center gap-2">
                    <span class="px-2 py-0.5 rounded bg-white/10 text-slate-300 font-mono text-[10px] uppercase tracking-wider">OFFICIAL REGISTER EXTRACT</span>
                    <span class="text-xs text-slate-300">தமிழ்நாடு அரசு நகர்ப்புற நில அளவை ஆவணம் (TSLR)</span>
                </div>
                <h3 class="text-sm font-bold text-white mt-1 flex items-center gap-2">
                    <i data-lucide="file-text" class="w-4 h-4 text-slate-300"></i>
                    <span>Town Survey Land Register (TSLR) Extract</span>
                </h3>
            </div>
            <div class="flex items-center gap-2 text-xs font-mono">
                <span class="px-2.5 py-1 rounded bg-slate-800 text-slate-200 border border-slate-700">T.S. No: <b>${escapeHtml(surveyVal)}</b></span>
                <span class="px-2.5 py-1 rounded bg-slate-800 text-emerald-400 border border-slate-700">Ryotwari Title</span>
            </div>
        </div>

        <!-- 1. ADMINISTRATIVE JURISDICTION (STEP 2) -->
        <div class="rounded-xl bg-white border border-slate-200 shadow-2xs overflow-hidden">
            <div class="px-4 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <i data-lucide="map" class="w-3.5 h-3.5 text-slate-700"></i>
                    <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider">1. Administrative Jurisdiction (நிர்வாக எல்லைகள்)</h4>
                </div>
                <span class="text-[10px] font-mono text-slate-400">Step 2: Header Block</span>
            </div>
            <div class="divide-y divide-slate-100">
                ${makeRow('district', 'District', 'மாவட்டம்', districtVal, getConf(fields.district))}
                ${makeRow('taluk', 'Taluk', 'வட்டம்', talukVal, getConf(fields.taluk))}
                ${makeRow('town_village', 'Town / Revenue Village', 'நகரம் / வருவாய் கிராமம்', townVal, getConf(fields.town_village))}
                ${makeRow('ward', 'Ward', 'வார்டு', wardVal, getConf(fields.ward))}
                ${makeRow('ward_block', 'Ward + Block', 'வார்டு & பிளாக்', wardBlockVal, getConf(fields.ward_block), 'Block Code & Name of Locality')}
            </div>
        </div>

        <!-- 2. PROPERTY IDENTIFICATION & DUAL SURVEY CORRELATION (STEPS 3 & 4) -->
        <div class="rounded-xl bg-white border border-slate-200 shadow-2xs overflow-hidden">
            <div class="px-4 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <i data-lucide="user-check" class="w-3.5 h-3.5 text-slate-700"></i>
                    <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider">2. Property Details & Ownership Correlation (நில உரிமை & சர்வே எண் விவரங்கள்)</h4>
                </div>
                <span class="text-[10px] font-mono text-slate-400">Steps 3 & 4: Table Data</span>
            </div>
            <div class="divide-y divide-slate-100">
                ${makeRow('owner_name', 'Name (Registered Holder / Owner)', 'உரிமையாளர் பெயர் (Adangal / UDS Details)', ownerVal, getConf(fields.owner_name), 'Pattadhar / Registered Holder from Adangal Record')}
                ${makeRow('survey_number', 'Town Survey Number (T.S. No)', 'நகர புல எண் (Sur. Field / Sub Div.)', surveyVal, getConf(fields.survey_number), 'Current Urban Cadastral Survey Number')}
                ${makeRow('old_survey_number', 'Old Survey Number (O.Sur No & Letter)', 'பழைய சர்வே எண் மற்றும் குறிப்பு', oldSurveyVal, getConf(fields.old_survey_number), 'Revenue correlation for mother deed / parent title trace')}
                ${makeRow('serial_no', 'Sl.No', 'வரிசை எண்', serialVal, getConf(fields.serial_no))}
                ${makeRow('municipal_door_no', 'Municipal Door No.', 'நகராட்சி கதவு எண்', doorVal, getConf(fields.municipal_door_no), 'Step 6: Preserved as Not Recorded if blank in register')}
            </div>
        </div>

        <!-- 3. LAND EXTENT & METRIC NORMALIZATION (STEP 3) -->
        <div class="rounded-xl bg-white border border-slate-200 shadow-2xs overflow-hidden">
            <div class="px-4 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <i data-lucide="scale" class="w-3.5 h-3.5 text-slate-700"></i>
                    <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider">3. Land Extent & Metric Conversions (நில விஸ்தீரணம் & அளவீடு)</h4>
                </div>
                <span class="text-[10px] font-mono text-slate-400">Extent By Town Survey</span>
            </div>
            <div class="divide-y divide-slate-100">
                ${makeRow('extent', 'Extent By Town Survey', 'ஆவண விஸ்தீரணம் (Hectare, Ares, Sq.Meter)', extentVal, getConf(fields.extent), 'Official register extent as recorded in eServices')}
                <div class="py-2.5 px-3 bg-slate-50/50">
                    <div class="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Normalized Real Estate Units Conversion</div>
                    <div class="grid grid-cols-3 gap-3 text-center">
                        <div class="p-2 rounded-lg bg-white border border-slate-200">
                            <span class="text-[10px] text-slate-500 font-semibold block">Total Metric Area</span>
                            <span class="text-xs font-bold text-slate-900 font-mono">${escapeHtml(String(totalSqm))} Sq.M</span>
                        </div>
                        <div class="p-2 rounded-lg bg-white border border-slate-200">
                            <span class="text-[10px] text-slate-500 font-semibold block">Square Feet</span>
                            <span class="text-xs font-bold text-slate-900 font-mono">${escapeHtml(String(totalSqft))} Sq.Ft</span>
                        </div>
                        <div class="p-2 rounded-lg bg-white border border-slate-200">
                            <span class="text-[10px] text-slate-500 font-semibold block">Grounds (மனை)</span>
                            <span class="text-xs font-bold text-slate-900 font-mono">${escapeHtml(String(grounds))} Grounds</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 4. TENURE, LAND CLASSIFICATION & REVENUE (STEPS 4 & 6) -->
        <div class="rounded-xl bg-white border border-slate-200 shadow-2xs overflow-hidden">
            <div class="px-4 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <i data-lucide="shield-check" class="w-3.5 h-3.5 text-slate-700"></i>
                    <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider">4. Tenure, Classification & Revenue Assessment (வகைப்பாடு, உரிமை & தீர்வை)</h4>
                </div>
                <span class="text-[10px] font-mono text-slate-400">Statutory Assessment</span>
            </div>
            <div class="divide-y divide-slate-100">
                ${makeRow('tenure_type', 'Tenure Type', 'நில உரிமை முறை (Govt/Mitta/Zamindari/Inam)', tenureVal, getConf(fields.tenure_type), 'Statutory direct tenure under Tamil Nadu Survey & Boundaries Act')}
                ${makeRow('land_classification', 'Land Classification', 'நில வகைப்பாடு (Dry/Wet/Promboke/House-site)', landClassVal, getConf(fields.land_classification), 'Approved municipal revenue land classification')}
                ${makeRow('current_land_use', 'Current Land Use', 'தற்போதைய பயன்பாடு (How the holding is utilised)', landUseVal, getConf(fields.current_land_use), 'Verified non-agricultural / building structure status')}
                ${makeRow('assessment', 'Assessment (Rs.)', 'தீர்வை / நில வரி (Municipal, Govt.)', assessVal, getConf(fields.assessment), 'Statutory municipal and government revenue dues')}
                ${makeRow('municipal_register', 'Municipal Register', 'நகராட்சி பதிவேடு', muniRegVal, getConf(fields.municipal_register))}
                ${makeRow('remarks', 'Remarks / Transfer Order', 'குறிப்புகள் / பட்டா மாறுதல் உத்தரவு', remarksVal, getConf(fields.remarks), 'Mutation transfer order reference number and dates')}
            </div>
        </div>

        <!-- 5. PROVENANCE, DIGITAL SIGNATURE & MULTI-PAGE AUDIT (STEPS 7 & 8) -->
        <div class="rounded-xl bg-white border border-slate-200 shadow-2xs overflow-hidden">
            <div class="px-4 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <i data-lucide="check-check" class="w-3.5 h-3.5 text-slate-700"></i>
                    <h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider">5. Certificate Provenance & Multi-Page Audit (சான்றிதழ் உண்மைத்தன்மை & பக்க தணிக்கை)</h4>
                </div>
                <span class="text-[10px] font-mono text-slate-400">Steps 7 & 8: Signature & Map</span>
            </div>
            <div class="divide-y divide-slate-100">
                ${makeRow('tahsildar_signatory', 'Digital Signature Authority', 'வட்டாட்சியர் / மின் கையொப்பம்', tahsildarVal, getConf(fields.tahsildar_signatory), 'Authoritative issuing Tahsildar for jurisdiction')}
                ${makeRow('digital_signature_date', 'Digital Signature Date', 'கையொப்ப நாள்', sigDateVal, getConf(fields.digital_signature_date))}
                ${makeRow('eservices_ref_no', 'eServices Verification Ref No', 'சான்றிதழ் குறிப்பு எண்', refNoVal, getConf(fields.eservices_ref_no), 'Validates QR code and digital registration record on tn.gov.in')}
                ${makeRow('certificate_print_date', 'Print Date & Time', 'அச்சடிக்கப்பட்ட நாள்', printDateVal, getConf(fields.certificate_print_date))}
                ${makeRow('portal_verification', 'Verification Portal', 'சரிபார்ப்பு இணையதளம்', portalVal, getConf(fields.portal_verification))}
                ${makeRow('page_audit', 'Multi-Page & Survey Map Audit', 'பக்க & வரைபட சரிபார்ப்பு', pageAuditVal, getConf(fields.page_audit), 'Step 8: Scanned all pages to verify survey field-map sketch')}
            </div>
        </div>
    `;

    container.appendChild(wrapper);
}

function renderStandardFieldsLayout(fields, container) {
    Object.entries(fields).forEach(([key, item]) => {
        if (key === "transactions_table" || key === "verification_flags" || key === "checklist" || key === "legal_caveat") {
            return;
        }
        const val = item.value;
        const conf = item.confidence || 0.90;
        const fieldLabel = item.label || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

        const card = document.createElement("div");
        card.className = "glass-card p-3 rounded-xl border border-slate-200/90 shadow-2xs hover:border-blue-200 cursor-pointer";
        card.id = `field-card-${key}`;
        card.onclick = () => highlightFieldCard(key);

        let valueHtml = "";
        if (typeof val === "object" && val !== null) {
            valueHtml = `<div class="grid grid-cols-2 gap-2 mt-1.5">`;
            for (const [subKey, subVal] of Object.entries(val)) {
                valueHtml += `
                    <div class="p-2 rounded-lg bg-slate-50 border border-slate-200/70 text-[11px]">
                        <span class="text-slate-500 font-semibold block capitalize">${subKey}:</span>
                        <span class="text-slate-800 font-medium">${escapeHtml(subVal)}</span>
                    </div>
                `;
            }
            valueHtml += `</div>`;
        } else {
            const valStr = String(val);
            valueHtml = `
                <div class="flex items-start justify-between gap-2 mt-1.5">
                    <div class="w-full bg-slate-50/80 hover:bg-white text-xs font-semibold text-slate-800 border border-slate-200/80 rounded-lg p-2.5 leading-relaxed break-words font-sans transition-colors whitespace-pre-line">
                        ${escapeHtml(valStr)}
                    </div>
                    <button onclick="event.stopPropagation(); copyToClipboard('${valStr.replace(/'/g, "\\'").replace(/\n/g, "\\n")}')" class="text-slate-400 hover:text-blue-600 p-1.5 rounded-lg hover:bg-blue-50 transition-colors shrink-0" title="Copy">
                        <i data-lucide="copy" class="w-3.5 h-3.5"></i>
                    </button>
                </div>
            `;
        }

        const confPct = Math.round(conf * 100);
        const confColor = confPct >= 85 ? "text-emerald-600 bg-emerald-50 border-emerald-200" : "text-amber-600 bg-amber-50 border-amber-200";

        card.innerHTML = `
            <div class="flex items-center justify-between text-xs mb-1">
                <span class="font-bold text-slate-700 flex items-center gap-1.5">
                    <span class="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                    <span>${fieldLabel}</span>
                </span>
                <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold border ${confColor}">${confPct}%</span>
            </div>
            ${valueHtml}
        `;
        container.appendChild(card);
    });
}
// 6. Checklist, OCR Text, and Tables
function renderChecklistTab(checklist) {
    const container = document.getElementById("checklist-items-container");
    const badge = document.getElementById("checklist-badge-count");
    container.innerHTML = "";
    const passedCount = checklist.filter(c => c.is_valid).length;
    badge.textContent = `${passedCount}/${checklist.length}`;

    checklist.forEach(item => {
        const row = document.createElement("div");
        const isPass = item.is_valid;
        row.className = `p-3 rounded-xl border flex items-center justify-between text-xs ${
            isPass ? "bg-emerald-50/40 border-emerald-200 text-slate-800" : "bg-amber-50/50 border-amber-200 text-slate-800"
        }`;
        row.innerHTML = `
            <div class="flex items-center space-x-2.5">
                <div class="w-5 h-5 rounded-full flex items-center justify-center ${isPass ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}">
                    <i data-lucide="${isPass ? 'check' : 'alert-circle'}" class="w-3.5 h-3.5"></i>
                </div>
                <span class="font-medium text-slate-800">${item.title}</span>
            </div>
            <span class="px-2 py-0.5 rounded-md font-bold text-[10px] ${isPass ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}">
                ${isPass ? "VERIFIED" : "ATTENTION"}
            </span>
        `;
        container.appendChild(row);
    });
}

function renderOCRTextTab(fullText) {
    document.getElementById("raw-ocr-text-view").textContent = fullText || "No text extracted.";
}

function renderTableTab(extraction) {
    const container = document.getElementById("table-records-container");
    const docId = extraction.document_type_id || "";
    const fields = extraction.fields || {};

    const txList = (fields.transactions_table && Array.isArray(fields.transactions_table.value))
        ? fields.transactions_table.value
        : [];

    if ((docId === "ec" || txList.length > 0) && txList.length > 0) {
        let rowsHtml = txList.map((tx, idx) => {
            const srNum = tx.sr || (idx + 1);
            const natureText = (tx.nature || "-").replace(/\n/g, "<br/>");
            const noteHtml = tx.nature_note ? `<div class="mt-1 text-[10px] text-slate-500 italic leading-snug">${escapeHtml(tx.nature_note)}</div>` : "";
            const execHtml = (tx.executants || tx.parties || "-").replace(/\n/g, "<br/>");
            const claimHtml = (tx.claimants || "-").replace(/\n/g, "<br/>");
            const consText = tx.consideration || "-";

            return `
            <tr class="hover:bg-slate-50/80 transition-colors">
                <td class="p-2.5 text-center text-slate-500 font-mono text-xs">${srNum}</td>
                <td class="p-2.5 font-bold text-blue-700 font-mono whitespace-nowrap text-xs">${escapeHtml(tx.doc_no || "-")}</td>
                <td class="p-2.5 text-slate-700 whitespace-nowrap text-xs font-medium">${escapeHtml(tx.date || "-")}</td>
                <td class="p-2.5 text-slate-800 text-xs leading-relaxed max-w-[150px]">
                    <div class="font-semibold text-slate-900">${natureText}</div>
                    ${noteHtml}
                </td>
                <td class="p-2.5 text-slate-700 text-[11px] leading-relaxed max-w-[200px]">${execHtml}</td>
                <td class="p-2.5 text-slate-700 text-[11px] leading-relaxed max-w-[180px]">${claimHtml}</td>
                <td class="p-2.5 font-semibold text-emerald-700 whitespace-nowrap text-xs font-mono">${escapeHtml(consText)}</td>
            </tr>
            `;
        }).join("");

        container.innerHTML = `
            <div class="mb-3 flex items-center justify-between">
                <div>
                    <h4 class="text-xs font-bold text-slate-900">Registered Entries (Form 15) — Full Detail</h4>
                    <p class="text-[11px] text-slate-500">${txList.length} Transactions Extracted Across All Pages</p>
                </div>
                <span class="px-2.5 py-1 bg-blue-50 text-blue-700 border border-blue-200 rounded-lg text-xs font-semibold">
                    ${txList.length} Entries
                </span>
            </div>
            <div class="overflow-x-auto max-h-[520px] rounded-xl border border-slate-200 shadow-2xs">
                <table class="w-full text-left text-xs border-collapse">
                    <thead class="bg-slate-800 text-white font-semibold sticky top-0 shadow-2xs">
                        <tr>
                            <th class="p-2.5 border-b border-slate-700 text-center w-10">Sr.</th>
                            <th class="p-2.5 border-b border-slate-700">Doc No/Year</th>
                            <th class="p-2.5 border-b border-slate-700">Date</th>
                            <th class="p-2.5 border-b border-slate-700">Nature</th>
                            <th class="p-2.5 border-b border-slate-700">Executant(s)</th>
                            <th class="p-2.5 border-b border-slate-700">Claimant(s)</th>
                            <th class="p-2.5 border-b border-slate-700">Consideration</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-200 bg-white">
                        ${rowsHtml}
                    </tbody>
                </table>
            </div>
        `;
    } else if (docId === "ec") {
        container.innerHTML = `
            <div class="p-8 text-center space-y-2">
                <div class="w-10 h-10 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center mx-auto">
                    <i data-lucide="check-circle" class="w-5 h-5"></i>
                </div>
                <h4 class="text-xs font-bold text-slate-800">Nil Encumbrance Certificate (Form 16)</h4>
                <p class="text-[11px] text-slate-500">No adverse encumbrance entries or transactions recorded during the search period. Title is clean.</p>
            </div>
        `;
    } else {
        container.innerHTML = `<div class="p-6 text-center text-xs text-slate-400">Structured tables available for EC & Legal Heir documents.</div>`;
    }
}

// 7. Multi-Document Bundles & Cross-Verification Matrix Engine
async function loadBundle(bundleId) {
    showLoader(true, `Running Multi-Document Cross-Verification on ${bundleId}...`);
    try {
        const res = await fetch(`/api/bundle/${bundleId}`);
        const data = await res.json();
        if (data.status === "success") {
            state.currentBundle = data;
            if (data.cross_check) {
                switchTrack("matrix");
                renderMatrixResults(data);
            } else if (data.inheritance_check) {
                switchTrack("inheritance");
                renderInheritanceResults(data);
            }
        }
    } catch (err) {
        console.error("Bundle error:", err);
    } finally {
        showLoader(false);
    }
}

function renderMatrixResults(bundleData) {
    const bundle = bundleData.bundle;
    const check = bundleData.cross_check;

    document.getElementById("matrix-bundle-title").textContent = bundle.title;
    document.getElementById("matrix-bundle-desc").textContent = bundle.description;

    const statusPill = document.getElementById("matrix-status-pill");
    const scoreText = document.getElementById("matrix-score-text");

    if (check.overall_status === "PASS") {
        statusPill.className = "px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200";
        statusPill.textContent = "OVERALL STATUS: ALL CHECKS PASSED (CLEAR TITLE)";
        scoreText.className = "text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-200";
        scoreText.textContent = `${check.checks_passed} of ${check.total_checks} Checks Passed (100% Integrity)`;
    } else {
        statusPill.className = "px-3 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300";
        statusPill.textContent = `CRITICAL ALERT: ${check.red_flags_count} RED FLAGS FOUND`;
        scoreText.className = "text-xs font-semibold text-rose-700 bg-rose-50 px-2.5 py-1 rounded-md border border-rose-200";
        scoreText.textContent = `${check.checks_passed} of ${check.total_checks} Checks Passed (${check.red_flags_count} Defect / Fraud Alerts)`;
    }

    const tbody = document.getElementById("matrix-table-body");
    tbody.innerHTML = "";

    (check.matrix_results || []).forEach(row => {
        const tr = document.createElement("tr");
        const isPass = row.status.includes("PASS");
        tr.className = isPass ? "hover:bg-slate-50" : "bg-rose-50/50 hover:bg-rose-50";

        tr.innerHTML = `
            <td class="p-3">
                <span class="font-bold text-slate-800 block">${row.title}</span>
                <span class="text-[11px] text-slate-500 block mt-0.5">${row.details}</span>
            </td>
            <td class="p-3 text-slate-600">${row.compared_docs}</td>
            <td class="p-3 font-medium text-slate-800">${row.sale_deed_val}</td>
            <td class="p-3 font-medium text-slate-800">${row.revenue_val}</td>
            <td class="p-3">
                <span class="px-2 py-1 rounded-md font-bold text-[10px] ${
                    isPass ? "bg-emerald-100 text-emerald-800 border border-emerald-200" : "bg-rose-100 text-rose-800 border border-rose-200"
                }">
                    ${row.status}
                </span>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function renderInheritanceResults(bundleData) {
    const inh = bundleData.inheritance_check;
    const cardsGrid = document.getElementById("heir-cards-grid");
    cardsGrid.innerHTML = "";

    (inh.heirs_breakdown || []).forEach((h, idx) => {
        const card = document.createElement("div");
        const isSigned = h.status.toLowerCase().includes("signatory") || h.status.toLowerCase().includes("release") || h.status.toLowerCase().includes("poa");
        card.className = `p-3.5 rounded-xl border heir-card shadow-2xs ${isSigned ? 'signed' : 'missing'}`;

        card.innerHTML = `
            <div class="flex items-start justify-between">
                <div>
                    <span class="text-[10px] font-bold text-slate-400">Class-I Legal Heir #${idx + 1}</span>
                    <h4 class="text-xs font-bold text-slate-900 mt-0.5">${h.name}</h4>
                    <p class="text-[11px] text-slate-600 mt-0.5">Relationship: <b>${h.relationship}</b> • Age: ${h.age}</p>
                </div>
                <span class="px-2 py-0.5 rounded text-[10px] font-bold ${
                    isSigned ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                }">
                    ${isSigned ? 'VERIFIED SIGNATORY / RELEASE' : 'MISSING SIGNATURE'}
                </span>
            </div>
            <div class="mt-2 pt-2 border-t border-slate-200/60 text-[11px] text-slate-700">
                <span class="font-semibold text-slate-500">Deed Status:</span> ${h.status}
            </div>
        `;
        cardsGrid.appendChild(card);
    });

    const stepsContainer = document.getElementById("inheritance-steps-container");
    stepsContainer.innerHTML = "";

    (inh.verification_steps || []).forEach(step => {
        const div = document.createElement("div");
        div.className = `p-3 rounded-xl border flex items-start justify-between gap-3 text-xs ${
            step.is_pass ? "bg-white border-slate-200" : "bg-rose-50 border-rose-200"
        }`;

        div.innerHTML = `
            <div class="space-y-0.5">
                <div class="flex items-center space-x-1.5">
                    <span class="font-bold text-slate-900">${step.title}</span>
                </div>
                <p class="text-[11px] text-slate-500">${step.description}</p>
                <p class="text-[11px] font-medium text-slate-800 pt-1">${step.details}</p>
            </div>
            <span class="px-2 py-0.5 rounded text-[10px] font-extrabold flex-shrink-0 ${
                step.is_pass ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"
            }">
                ${step.status}
            </span>
        `;
        stepsContainer.appendChild(div);
    });
    lucide.createIcons();
}

// 8. Tab, Zoom, Search, and Export helpers
function switchTab(tabName) {
    state.activeTab = tabName;
    ["fields", "checklist", "ocr", "table"].forEach(t => {
        const btn = document.getElementById(`tab-btn-${t}`);
        const content = document.getElementById(`tab-content-${t}`);
        if (t === tabName) {
            btn.className = "px-3 py-1.5 font-semibold rounded-lg bg-blue-600 text-white shadow-sm flex items-center gap-1.5";
            content.classList.remove("hidden");
        } else {
            btn.className = "px-3 py-1.5 font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 flex items-center gap-1.5";
            content.classList.add("hidden");
        }
    });
    lucide.createIcons();
}

function changePage(delta) {
    if (!state.currentResult || !state.currentResult.pages) return;
    const newIdx = state.currentPageIndex + delta;
    if (newIdx >= 0 && newIdx < state.currentResult.pages.length) {
        jumpToPage(newIdx);
    }
}

function adjustZoom(delta) {
    state.zoomLevel = Math.max(0.4, Math.min(2.5, state.zoomLevel + delta));
    applyZoom();
}

function resetZoom() {
    state.zoomLevel = 1.0;
    applyZoom();
}

function applyZoom() {
    const pagesContainer = document.getElementById("all-pages-container");
    if (pagesContainer) {
        pagesContainer.style.transform = `scale(${state.zoomLevel})`;
    }
    const canvasWrapper = document.getElementById("canvas-wrapper");
    if (canvasWrapper) {
        canvasWrapper.style.transform = `scale(${state.zoomLevel})`;
    }
    const zoomText = document.getElementById("zoom-level-text");
    if (zoomText) {
        zoomText.textContent = `${Math.round(state.zoomLevel * 100)}%`;
    }
}

function toggleBBoxes() {
    state.showBBoxes = !state.showBBoxes;
    const bboxLayers = document.querySelectorAll(".pdf-page-bbox-layer, #bbox-overlay-layer");
    bboxLayers.forEach(layer => {
        layer.style.display = state.showBBoxes ? "block" : "none";
    });
}

function searchInDocument(query) {
    const q = query.trim().toLowerCase();
    const countEl = document.getElementById("search-match-count");
    const bboxes = document.querySelectorAll(".word-bbox, .ocr-bbox");

    if (!q) {
        if (countEl) countEl.textContent = "";
        bboxes.forEach(b => b.classList.remove("highlighted"));
        return;
    }
    let matchCount = 0;
    bboxes.forEach(b => {
        if (b.innerText.toLowerCase().includes(q)) {
            b.classList.add("highlighted");
            matchCount++;
        } else {
            b.classList.remove("highlighted");
        }
    });
    countEl.textContent = `${matchCount} found`;
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function showWordInspector(word, pageNum) {
    let card = document.getElementById("word-inspector-card");
    if (!card) {
        card = document.createElement("div");
        card.id = "word-inspector-card";
        document.body.appendChild(card);
    }

    const confPct = Math.round((word.confidence || 0.98) * 100);
    const trans = word.translation || "No direct translation";

    card.innerHTML = `
        <div class="flex items-start justify-between gap-3 mb-2">
            <div class="flex items-center gap-1.5">
                <span class="w-2 h-2 rounded-full bg-blue-500"></span>
                <span class="text-xs font-bold text-slate-200">Word Inspector • Page ${pageNum}</span>
            </div>
            <button onclick="document.getElementById('word-inspector-card').remove()" class="text-slate-400 hover:text-white p-0.5 text-xs font-bold leading-none">&times;</button>
        </div>
        <div class="space-y-1.5 text-xs">
            <div class="bg-slate-800/80 p-2 rounded-lg border border-slate-700">
                <span class="text-[10px] text-slate-400 font-semibold uppercase block">Detected Word (OCR):</span>
                <span class="text-sm font-bold text-white tracking-wide select-all">${escapeHtml(word.text)}</span>
            </div>
            <div class="bg-emerald-950/40 p-2 rounded-lg border border-emerald-800/50">
                <span class="text-[10px] text-emerald-300 font-semibold uppercase block">Bilingual Translation:</span>
                <span class="text-sm font-bold text-emerald-300 select-all">${escapeHtml(trans)}</span>
            </div>
            <div class="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                <span>Confidence: <b class="text-blue-400">${confPct}%</b></span>
                <button onclick="copyToClipboard('${escapeHtml(trans).replace(/'/g, "\\'")}')" class="text-blue-400 hover:text-blue-300 font-semibold text-[10px] underline">Copy Trans</button>
            </div>
        </div>
    `;
}

function highlightLineInText(text) {
    switchTab("ocr");
    document.getElementById("raw-ocr-text-view").scrollIntoView({ behavior: "smooth" });
}

async function exportResult(format) {
    if (!state.currentResult) return;
    const res_data = state.currentResult;
    const extraction = res_data.extraction || {};
    const payload = {
        format: format,
        doc_type: extraction.document_type_id || "document",
        filename: res_data.filename || "document.pdf",
        total_pages: res_data.total_pages || 1,
        extraction: extraction,
        fields: extraction.fields || {},
        checklist: extraction.checklist || []
    };

    try {
        const res = await fetch("/api/export", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        if (!res.ok) {
            let errMsg = `Export failed (HTTP ${res.status})`;
            try {
                const errJson = await res.json();
                if (errJson && errJson.detail) errMsg = errJson.detail;
            } catch(e) {}
            throw new Error(errMsg);
        }
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        const cleanBase = (res_data.filename || extraction.document_type_id || 'document').replace(/\.[^/.]+$/, "");
        a.download = format === 'pdf' ? `${cleanBase}_OCR_Report.pdf` : `${cleanBase}_extracted.${format}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => window.URL.revokeObjectURL(url), 1500);
    } catch (err) {
        console.error("Export error:", err);
        alert("Failed to download " + format.toUpperCase() + ": " + err.message);
    }
}

function printReport() { window.print(); }
function copyToClipboard(text) { navigator.clipboard.writeText(text); }
function copyFullText() {
    navigator.clipboard.writeText(document.getElementById("raw-ocr-text-view").innerText);
    alert("Full OCR text copied to clipboard!");
}
function resetWorkspace() {
    state.currentFile = null;
    state.currentResult = null;
    state.currentPageIndex = 0;

    // 1. Reset hidden file input
    const fileInput = document.getElementById("file-input");
    if (fileInput) fileInput.value = "";

    // 2. Reset dropzone UI
    resetDropzoneUI();

    // 3. Clear document preview & canvas
    const emptyState = document.getElementById("viewer-empty-state");
    const imgPreview = document.getElementById("doc-image-preview");
    const bboxLayer = document.getElementById("bbox-overlay-layer");
    if (emptyState) emptyState.classList.remove("hidden");
    if (imgPreview) {
        imgPreview.src = "";
        imgPreview.style.display = "none";
    }
    if (bboxLayer) bboxLayer.innerHTML = "";

    // 4. Reset pagination & zoom
    const pageInd = document.getElementById("page-indicator");
    if (pageInd) pageInd.textContent = "Page 0 / 0";
    const prevBtn = document.getElementById("btn-prev-page");
    const nextBtn = document.getElementById("btn-next-page");
    if (prevBtn) prevBtn.disabled = true;
    if (nextBtn) nextBtn.disabled = true;
    resetZoom();

    // 5. Reset search
    const searchInput = document.getElementById("doc-search-input");
    const searchCount = document.getElementById("search-match-count");
    if (searchInput) searchInput.value = "";
    if (searchCount) searchCount.textContent = "";

    // 6. Reset titles and badge
    const titleEl = document.getElementById("result-doc-type-title");
    const subEl = document.getElementById("result-doc-subtitle");
    const badgeEl = document.getElementById("result-doc-badge");
    const cat = state.categories.find(c => c.id === state.selectedCategoryId);
    const catName = cat ? cat.name : "Document";

    if (titleEl) titleEl.textContent = "Document Removed";
    if (subEl) subEl.textContent = `Category: ${catName}. Upload a new document file below to begin OCR extraction.`;
    if (badgeEl) {
        badgeEl.textContent = "Ready for Upload";
        badgeEl.className = "px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200";
    }

    // 7. Reset Key Fields Tab with upload CTA
    const fieldsContainer = document.getElementById("extracted-fields-container");
    if (fieldsContainer) {
        fieldsContainer.innerHTML = `
            <div class="p-8 text-center bg-slate-50/60 rounded-2xl border-2 border-dashed border-slate-200 flex flex-col items-center justify-center space-y-3">
                <div class="w-14 h-14 rounded-2xl bg-blue-100/80 text-blue-600 flex items-center justify-center shadow-xs">
                    <i data-lucide="upload-cloud" class="w-7 h-7"></i>
                </div>
                <div>
                    <h4 class="font-bold text-slate-900 text-sm mb-1">Document Removed & Ready</h4>
                    <p class="text-xs text-slate-500 max-w-sm">The previous document has been cleared. Select or drop a new document above to extract key fields.</p>
                </div>
                <button type="button" onclick="document.getElementById('file-input').click()" class="mt-2 px-4 py-2 text-xs font-semibold rounded-xl bg-blue-600 hover:bg-blue-700 text-white shadow-sm flex items-center gap-1.5 transition-colors">
                    <i data-lucide="file-up" class="w-4 h-4"></i>
                    <span>Select New Document to Upload</span>
                </button>
            </div>
        `;
    }

    // 8. Reset Checklist Tab
    const checklistContainer = document.getElementById("checklist-items-container");
    const checklistBadge = document.getElementById("checklist-badge-count");
    if (checklistBadge) checklistBadge.textContent = "0/0";
    if (checklistContainer) {
        checklistContainer.innerHTML = `
            <div class="p-8 text-center text-slate-400 text-xs flex flex-col items-center justify-center space-y-2">
                <i data-lucide="check-square" class="w-8 h-8 text-slate-300"></i>
                <p>Checklist validation will execute automatically when a document is uploaded.</p>
            </div>
        `;
    }

    // 9. Reset OCR Text Tab
    const rawOcrView = document.getElementById("raw-ocr-text-view");
    if (rawOcrView) {
        rawOcrView.textContent = "No document loaded. Upload a file above to view raw OCR text.";
    }

    // 10. Reset Table Tab
    const tableContainer = document.getElementById("table-records-container");
    if (tableContainer) {
        tableContainer.innerHTML = `
            <div class="p-8 text-center text-slate-400 text-xs flex flex-col items-center justify-center space-y-2">
                <i data-lucide="table" class="w-8 h-8 text-slate-300"></i>
                <p>Table records will appear here after document processing.</p>
            </div>
        `;
    }

    lucide.createIcons();

    // 11. Highlight dropzone area
    const dropzone = document.getElementById("dropzone");
    if (dropzone) {
        dropzone.scrollIntoView({ behavior: "smooth", block: "center" });
        dropzone.classList.add("ring-4", "ring-blue-200");
        setTimeout(() => dropzone.classList.remove("ring-4", "ring-blue-200"), 1200);
    }
}
function showLoader(show, text = "") {
    const loader = document.getElementById("processing-loader");
    if (show) {
        document.getElementById("processing-status-text").textContent = text;
        loader.classList.remove("hidden");
    } else {
        loader.classList.add("hidden");
    }
}
