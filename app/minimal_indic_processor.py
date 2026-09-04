# -*- coding: utf-8 -*-
"""
Minimal pure-Python IndicProcessor compatible with IndicTransToolkit API.
This is a lightweight implementation for use when IndicTransToolkit cannot be 
installed (e.g., no MSVC compiler on Windows).

Provides the preprocess_batch() and postprocess_batch() methods needed by the
IndicTrans2 HuggingFace inference pipeline.

Reference: https://github.com/AI4Bharat/IndicTransToolkit
"""

import re
from typing import List


# FLORES-200 language codes used by IndicTrans2
FLORES_CODES = {
    "eng_Latn": "en",
    "tam_Taml": "ta",
    "hin_Deva": "hi",
    "ben_Beng": "bn",
    "tel_Telu": "te",
    "kan_Knda": "kn",
    "mal_Mlym": "ml",
    "mar_Deva": "mr",
    "guj_Gujr": "gu",
    "pan_Guru": "pa",
    "ory_Orya": "or",
}


class IndicProcessor:
    """
    Minimal IndicProcessor for preprocessing/postprocessing IndicTrans2 inputs.
    Compatible with the IndicTransToolkit API.
    """

    def __init__(self, inference: bool = True):
        self.inference = inference
        # Regex to normalize multiple spaces
        self._multispace = re.compile(r"\s+")

    def preprocess_batch(
        self,
        batch: List[str],
        src_lang: str,
        tgt_lang: str,
        show_progress_bar: bool = False,
    ) -> List[str]:
        """
        Preprocess a batch of sentences for IndicTrans2 model input.
        For our use case (short names/places), minimal cleaning is sufficient.
        """
        processed = []
        for sentence in batch:
            # Basic normalization
            s = sentence.strip()
            s = self._multispace.sub(" ", s)
            # Remove control characters
            s = "".join(c for c in s if ord(c) >= 32 or c in "\t\n")
            processed.append(s)
        return processed

    def postprocess_batch(
        self,
        batch: List[str],
        lang: str,
        show_progress_bar: bool = False,
    ) -> List[str]:
        """
        Postprocess the model output batch.
        For our use case, minimal postprocessing (strip + normalize space).
        """
        processed = []
        for sentence in batch:
            s = sentence.strip()
            s = self._multispace.sub(" ", s)
            processed.append(s)
        return processed
