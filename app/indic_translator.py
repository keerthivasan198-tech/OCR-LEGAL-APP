# -*- coding: utf-8 -*-
"""
IndicTrans2 Neural Translation Engine for Tamil ↔ English.

Uses AI4Bharat/IndicTrans2 via HuggingFace — the best-in-class
open-source model for Indian language translation.

Models used (downloaded automatically on first call from HuggingFace Hub):
    en → ta  :  ai4bharat/indictrans2-en-indic-dist-200M  (faster, ~800MB)
    ta → en  :  ai4bharat/indictrans2-indic-en-dist-200M  (faster, ~800MB)

Language codes used by IndicTrans2:
    English  → eng_Latn
    Tamil    → tam_Taml
"""

import logging
import sys
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# IndicTrans2 HuggingFace model IDs
# Using the 200M distilled variants — fast enough on CPU, good quality
_EN_INDIC_MODEL = "ai4bharat/indictrans2-en-indic-dist-200M"
_INDIC_EN_MODEL = "ai4bharat/indictrans2-indic-en-dist-200M"

# Add IndicTrans2 huggingface_interface to path so we can import custom modeling files
_HF_IFACE_DIR = Path(__file__).parent.parent / "IndicTrans2" / "huggingface_interface"
if str(_HF_IFACE_DIR) not in sys.path:
    sys.path.insert(0, str(_HF_IFACE_DIR))

# Try importing IndicTransToolkit (compiled Cython version)
# Fall back to our minimal pure-Python version if not available (e.g., no MSVC on Windows)
try:
    from IndicTransToolkit.processor import IndicProcessor
    logger.info("IndicTransToolkit loaded (compiled version)")
    _TOOLKIT_AVAILABLE = True
except ImportError:
    try:
        from app.minimal_indic_processor import IndicProcessor
        logger.info("IndicTransToolkit not available — using minimal pure-Python IndicProcessor fallback")
        _TOOLKIT_AVAILABLE = True
    except ImportError:
        _TOOLKIT_AVAILABLE = False
        logger.warning("No IndicProcessor available")

# Lazy-loaded singletons (None until first translate call)
_en_ta_model = None
_en_ta_tokenizer = None
_ta_en_model = None
_ta_en_tokenizer = None
_ip = None          # IndicProcessor
_DEVICE = None
_models_available = None  # True / False after first load attempt


def _check_deps() -> bool:
    """Return True if all required packages are importable."""
    if not _TOOLKIT_AVAILABLE:
        logger.warning("IndicProcessor not available")
        return False
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
        return True
    except ImportError as e:
        logger.warning(f"IndicTrans2 core dependencies not available: {e}")
        return False


def _load_models():
    """Lazily load both translation models into memory (called once)."""
    global _en_ta_model, _en_ta_tokenizer, _ta_en_model, _ta_en_tokenizer
    global _ip, _DEVICE, _models_available

    if _models_available is not None:
        return  # already attempted

    if not _check_deps():
        _models_available = False
        return

    # If no HF token and no local cache, avoid network 401 client error
    if not os.environ.get("HF_TOKEN") and not os.environ.get("HUGGING_FACE_HUB_TOKEN"):
        hf_cache = os.path.expanduser("~/.cache/huggingface/hub")
        has_cached = os.path.isdir(hf_cache) and any("indictrans2" in d.lower() for d in os.listdir(hf_cache) if os.path.isdir(os.path.join(hf_cache, d)))
        if not has_cached:
            logger.info("IndicTrans2 models not locally cached. Using optimized rule-based & phonetic bilingual engine.")
            _models_available = False
            return

    try:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        _DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading IndicTrans2 models on device: {_DEVICE}")

        # Use the IndicProcessor already imported at module level
        _ip = IndicProcessor(inference=True)

        # English → Tamil
        logger.info(f"Loading {_EN_INDIC_MODEL} ...")
        _en_ta_tokenizer = AutoTokenizer.from_pretrained(
            _EN_INDIC_MODEL, trust_remote_code=True
        )
        _en_ta_model = AutoModelForSeq2SeqLM.from_pretrained(
            _EN_INDIC_MODEL,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        ).to(_DEVICE).eval()

        # Tamil → English
        logger.info(f"Loading {_INDIC_EN_MODEL} ...")
        _ta_en_tokenizer = AutoTokenizer.from_pretrained(
            _INDIC_EN_MODEL, trust_remote_code=True
        )
        _ta_en_model = AutoModelForSeq2SeqLM.from_pretrained(
            _INDIC_EN_MODEL,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        ).to(_DEVICE).eval()

        _models_available = True
        logger.info("IndicTrans2 models loaded successfully ✓")

    except Exception as e:
        logger.error(f"Failed to load IndicTrans2 models: {e}")
        _models_available = False


def _batch_translate(sentences: list[str], src_lang: str, tgt_lang: str,
                     model, tokenizer) -> list[str]:
    """Run batch translation through IndicTrans2."""
    import torch
    BATCH_SIZE = 8

    all_translations = []
    for i in range(0, len(sentences), BATCH_SIZE):
        batch = sentences[i: i + BATCH_SIZE]
        batch_proc = _ip.preprocess_batch(batch, src_lang=src_lang, tgt_lang=tgt_lang)

        inputs = tokenizer(
            batch_proc,
            truncation=True,
            padding="longest",
            return_tensors="pt",
            return_attention_mask=True,
        ).to(_DEVICE)

        with torch.no_grad():
            generated = model.generate(
                **inputs,
                use_cache=True,
                min_length=0,
                max_length=256,
                num_beams=5,
                num_return_sequences=1,
            )

        decoded = tokenizer.batch_decode(
            generated,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )
        all_translations += _ip.postprocess_batch(decoded, lang=tgt_lang)

    return all_translations


def translate_to_tamil(text: str) -> Optional[str]:
    """
    Translate English text → Tamil using IndicTrans2.
    Returns None if model is unavailable or translation fails.
    """
    _load_models()
    if not _models_available:
        return None
    try:
        results = _batch_translate([text.strip()], "eng_Latn", "tam_Taml",
                                   _en_ta_model, _en_ta_tokenizer)
        return results[0].strip() if results else None
    except Exception as e:
        logger.error(f"translate_to_tamil failed: {e}")
        return None


def translate_to_english(text: str) -> Optional[str]:
    """
    Translate Tamil text → English using IndicTrans2.
    Returns None if model is unavailable or translation fails.
    """
    _load_models()
    if not _models_available:
        return None
    try:
        results = _batch_translate([text.strip()], "tam_Taml", "eng_Latn",
                                   _ta_en_model, _ta_en_tokenizer)
        return results[0].strip() if results else None
    except Exception as e:
        logger.error(f"translate_to_english failed: {e}")
        return None


def is_available() -> bool:
    """Return True if IndicTrans2 models are ready."""
    _load_models()
    return bool(_models_available)
