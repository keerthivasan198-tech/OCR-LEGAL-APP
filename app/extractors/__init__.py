# -*- coding: utf-8 -*-
"""
Modular Extractors Package for Real Estate Document Intelligence.
Contains dedicated document-specific extractor modules:
1. SaleDeedExtractor (sale_deed_extractor.py)
2. PattaExtractor (patta_extractor.py / patta-extractor.py)
3. ParentDocsExtractor (parent_docs_extractor.py)
4. ECExtractor (ec_extractor.py)
5. BuildingPlanExtractor (building_plan_extractor.py)
6. RERAExtractor (rera_extractor.py)
7. TaxReceiptsExtractor (tax_receipts_extractor.py)
8. LayoutApprovalExtractor (layout_approval_extractor.py)
9. DeathLegalHeirExtractor (death_legal_heir_extractor.py)
10. LoanDocsExtractor (loan_docs_extractor.py)
"""

from .patta_extractor import PattaExtractor
from .sale_deed_extractor import SaleDeedExtractor
from .parent_docs_extractor import ParentDocsExtractor
from .ec_extractor import ECExtractor
from .building_plan_extractor import BuildingPlanExtractor
from .rera_extractor import RERAExtractor
from .tax_receipts_extractor import TaxReceiptsExtractor
from .layout_approval_extractor import LayoutApprovalExtractor
from .death_legal_heir_extractor import DeathLegalHeirExtractor
from .loan_docs_extractor import LoanDocsExtractor
from .tslr_extractor import TSLRExtractor

__all__ = [
    "PattaExtractor",
    "SaleDeedExtractor",
    "ParentDocsExtractor",
    "ECExtractor",
    "BuildingPlanExtractor",
    "RERAExtractor",
    "TaxReceiptsExtractor",
    "LayoutApprovalExtractor",
    "DeathLegalHeirExtractor",
    "LoanDocsExtractor",
    "TSLRExtractor"
]
