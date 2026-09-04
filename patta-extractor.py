# -*- coding: utf-8 -*-
"""
Patta Document Extractor (patta-extractor.py).
Exports the PattaExtractor class from app.extractors.patta_extractor.
"""

from app.extractors.patta_extractor import PattaExtractor

__all__ = ["PattaExtractor"]

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print("Patta Extractor module initialized successfully.")
