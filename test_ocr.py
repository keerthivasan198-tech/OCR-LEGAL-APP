# -*- coding: utf-8 -*-
"""
Automated unit tests for the 10 real estate document categories,
strict field extraction, cross-check matrix, and inheritance track.
"""

import unittest
from fastapi.testclient import TestClient
from app.server import app
from app.samples import DOCUMENT_CATEGORIES, SAMPLE_DOCUMENTS, MULTI_DOC_BUNDLES
from app.extractor import DocumentExtractor
from app.cross_checker import CrossVerificationEngine

class TestPropertyDocumentOCR(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.extractor = DocumentExtractor()
        self.cross_engine = CrossVerificationEngine()

    def test_categories_integrity(self):
        """Verify exact 10 document categories requested by user are registered."""
        expected_10 = [
            "sale_deed", "patta", "parent_docs", "ec", "building_plan",
            "rera", "tax_eb", "layout_approval", "death_legal_heir", "loan_docs"
        ]
        cat_ids = [c["id"] for c in DOCUMENT_CATEGORIES]
        self.assertEqual(len(cat_ids), 10)
        for expected in expected_10:
            self.assertIn(expected, cat_ids)

    def test_deep_sale_deed_extraction(self):
        """Verify strict extraction of Sale deed: Vendor, Purchaser, Schedule, Boundary, SRO."""
        sample = SAMPLE_DOCUMENTS["sale_deed"]
        extracted = self.extractor.extract(sample["raw_text"], doc_type="sale_deed")
        fields = extracted["fields"]

        self.assertIn("vendor_details", fields)
        self.assertIn("purchaser_details", fields)
        self.assertIn("schedule_property_type", fields)
        self.assertIn("survey_number", fields)
        self.assertIn("land_extent", fields)
        self.assertIn("boundary", fields)
        self.assertIn("sro_details", fields)
        self.assertIn("XXXX-XXXX-4512", fields["vendor_details"]["value"])

    def test_cross_verification_standard_bundle(self):
        """Verify standard cross-check matrix passes all 7 checks on genuine bundle."""
        bundle = MULTI_DOC_BUNDLES["standard_sale_bundle"]["documents"]
        matrix_res = self.cross_engine.run_standard_cross_check(bundle)

        self.assertEqual(matrix_res["overall_status"], "PASS")
        self.assertEqual(matrix_res["red_flags_count"], 0)
        self.assertEqual(matrix_res["checks_passed"], 7)

    def test_poramboke_fraud_detection(self):
        """Verify Poramboke Fraud bundle triggers Critical Alert."""
        fraud_bundle = MULTI_DOC_BUNDLES["fraud_alert_bundle"]["documents"]
        matrix_res = self.cross_engine.run_standard_cross_check(fraud_bundle)

        self.assertEqual(matrix_res["overall_status"], "ACTION REQUIRED")
        self.assertGreaterEqual(matrix_res["red_flags_count"], 1)

    def test_inheritance_track_verification(self):
        """Verify Death Certificate & Legal Heir Certificate (Varisu) verification track."""
        bundle = MULTI_DOC_BUNDLES["inherited_property_bundle"]["inheritance_data"]
        inh_res = self.cross_engine.run_inheritance_track_check(bundle)

        self.assertEqual(inh_res["overall_status"], "PASS")
        self.assertTrue(inh_res["hard_gate_passed"])
        self.assertEqual(inh_res["total_heirs_count"], 4)
        self.assertEqual(inh_res["accounted_heirs_count"], 4)

    def test_api_bundles_endpoint(self):
        """Test /api/bundles and /api/bundle/{id}."""
        res = self.client.get("/api/bundles")
        self.assertEqual(res.status_code, 200)

        b_res = self.client.get("/api/bundle/standard_sale_bundle")
        self.assertEqual(b_res.status_code, 200)
        b_data = b_res.json()
        self.assertEqual(b_data["cross_check"]["overall_status"], "PASS")

if __name__ == "__main__":
    unittest.main()
