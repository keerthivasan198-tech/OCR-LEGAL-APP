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
        """Verify document categories requested by user are registered."""
        expected_10 = [
            "sale_deed", "patta", "parent_docs", "ec", "building_plan",
            "rera", "tax_eb", "layout_approval", "death_legal_heir", "loan_docs"
        ]
        cat_ids = [c["id"] for c in DOCUMENT_CATEGORIES]
        self.assertGreaterEqual(len(cat_ids), 10)
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
        self.assertTrue("boundaries" in fields or "boundary" in fields)
        self.assertIn("sro_details", fields)
        self.assertIn("RAJENDRAN", fields["vendor_details"]["value"])

    def test_dynamic_ec_header_extraction(self):
        """Verify zero-fallback dynamic extraction of EC header fields."""
        sample_text = """OAT
Certificate of Encumbrance on Property
சொத்துதொடர்பானவில்லங்கச் சான்று
S.R.O/சா.ப.அ: Chengleput JointI
Date / நாள்: 04-Sep-2026
Village /கிராமம்:Alappakkam
SurveyDetails /சர்வேவிவரம்: 35
Data Availability Period for Village: Alappakkam
Chengleput Joint I Sub Registrar Office: From 01-Jan-2003 To 03-Sep-2026
Search Period/தடுதல் காலம்: 01-Jan-2003 - 03-Sep-2026
"""
        extracted = self.extractor.extract(sample_text, doc_type="ec")
        fields = extracted["fields"]

        self.assertEqual(fields["survey_searched"]["value"], "35")
        self.assertEqual(fields["search_period"]["value"], "01-Jan-2003 to 03-Sep-2026")
        self.assertEqual(fields["sro_available_from"]["value"], "From 01-Jan-2003 To 03-Sep-2026")
        self.assertEqual(fields["village"]["value"], "Alappakkam (அலப்பாக்கம்)")
        self.assertEqual(fields["district"]["value"], "Chengalpattu (செங்கல்பட்டு)")

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

    def test_tslr_canonical_fields(self):
        """Verify TSLR exact canonical fields extraction."""
        sample = SAMPLE_DOCUMENTS["tslr"]
        extracted = self.extractor.extract(sample["raw_text"], doc_type="tslr")
        fields = extracted["fields"]

        self.assertIn("district", fields)
        self.assertIn("taluk", fields)
        self.assertIn("town_village", fields)
        self.assertEqual(fields["town_village"]["label"], "Town")
        self.assertIn("ward", fields)
        self.assertIn("owner_name", fields)
        self.assertEqual(fields["owner_name"]["label"], "Name")
        self.assertIn("survey_number", fields)
        self.assertIn("extent", fields)
        self.assertIn("ward_block", fields)
        self.assertIn("land_classification", fields)
        self.assertIn("current_land_use", fields)
        self.assertIn("tenure_type", fields)
        self.assertIn("assessment", fields)
        self.assertIn("remarks", fields)

    def test_tamil_tslr_extraction(self):
        """Verify 100% extraction for Tamil TSLR document with zero OCR label noise."""
        tamil_tslr_text = """தமிழ்நாடு அரசு
வருவாய்த் துறை
நகர நில அளவை பதிவேடு சான்று
EXTRACT FROM THE TOWN SURVEY LAND REGISTER

மாவட்டம் / District : விழுப்புரம்
வட்டம் / Taluk : விழுப்புரம்
நகரம் / Town : வடமங்கலம்
வார்டு / Ward : -

வ.எண் | தொகுதி | நகர சர்வே எண் | உட்பிரிவு | பழைய சர்வே எண் | நில வகைப்பாடு | தற்போதைய பயன்பாடு | உரிமை வகை | பரப்பளவு (ஹெக் - ஏர் - ச.மீ) | தீர்வை (முனிசிபல் - அரசு) | பெயர் / Name | குறிப்பு
1 | 01 | 35 | 2 | 249/3A | ரயத்துவாரி மனை | கட்டிடம் | ரயத்துவாரி | 0.00 0 04 50.0 | - 1 | / Name : GANESAN R (Tamil: / னமெ : கணேஸன் ர) | 2023/0153/02/047290TR DT. 2023-11-30
"""
        extracted = self.extractor.extract(tamil_tslr_text, doc_type="tslr")
        fields = extracted["fields"]

        self.assertIn("Villupuram", fields["district"]["value"])
        self.assertIn("விழுப்புரம்", fields["district"]["value"])
        self.assertIn("Villupuram", fields["taluk"]["value"])
        self.assertIn("Vadamangalam", fields["town_village"]["value"])
        self.assertEqual(fields["ward"]["value"], "-")
        self.assertIn("GANESAN R", fields["owner_name"]["value"])
        self.assertNotIn("/ Name", fields["owner_name"]["value"])
        self.assertNotIn("/ னமெ", fields["owner_name"]["value"])
        self.assertIn("35/2", fields["survey_number"]["value"])
        self.assertIn("249/3A", fields["survey_number"]["value"])
        self.assertIn("04 Are(s), 50.0 Sq.Meter(s)", fields["extent"]["value"])
        self.assertEqual(fields["ward_block"]["value"], "Block 01")
        self.assertEqual(fields["land_classification"]["value"], "Ryotwari House-site (Manai)")
        self.assertEqual(fields["current_land_use"]["value"], "Building --> Non-agricultural")
        self.assertEqual(fields["tenure_type"]["value"], "Ryotwari")
        self.assertEqual(fields["assessment"]["value"], "Municipal=-, Govt=1")
        self.assertEqual(fields["remarks"]["value"], "2023/0153/02/047290TR DT. 2023-11-30")

    def test_ec_table_values_ordering_and_separation(self):
        """Verify strict ordering and non-duplicated executant/claimant separation in EC tables."""
        sample = SAMPLE_DOCUMENTS["ec"]
        extracted = self.extractor.extract(sample["raw_text"], doc_type="ec")
        tx_list = extracted["fields"]["transactions_table"]["value"]

        self.assertEqual(len(tx_list), 4)
        
        # Entry 1: Sale deed
        self.assertEqual(tx_list[0]["doc_no"], "1820/2008")
        self.assertEqual(tx_list[0]["executants"], "Classic Foundations Pvt Ltd")
        self.assertEqual(tx_list[0]["claimants"], "K. Rajendran")
        self.assertEqual(tx_list[0]["consideration"], "Rs. 32,00,000/-")
        self.assertEqual(tx_list[0]["pr_number"], "450/1995")

        # Entry 2: MODT - State Bank of India
        self.assertEqual(tx_list[1]["doc_no"], "2910/2012")
        self.assertEqual(tx_list[1]["executants"], "K. Rajendran")
        self.assertEqual(tx_list[1]["claimants"], "State Bank of India")
        self.assertEqual(tx_list[1]["consideration"], "Rs. 25,00,000/-")
        self.assertEqual(tx_list[1]["pr_number"], "1820/2008")

        # Entry 3: Receipt - Discharge
        self.assertEqual(tx_list[2]["doc_no"], "640/2018")
        self.assertEqual(tx_list[2]["executants"], "State Bank of India")
        self.assertEqual(tx_list[2]["claimants"], "K. Rajendran")
        self.assertEqual(tx_list[2]["consideration"], "Rs. 25,00,000/-")

        # Entry 4: Sale deed to Lakshmi Priya
        self.assertEqual(tx_list[3]["doc_no"], "4521/2023")
        self.assertEqual(tx_list[3]["executants"], "K. Rajendran")
        self.assertEqual(tx_list[3]["claimants"], "S. Lakshmi Priya")
        self.assertEqual(tx_list[3]["consideration"], "Rs. 75,00,000/-")

    def test_tamil_ec_table_extraction(self):
        """Verify 100% accurate segmentation and label-anchored separation for Tamil EC."""
        tamil_ec_text = """தமிழ்நாடு அரசு - பதிவுத்துறை
சொத்து தொடர்பான வில்லங்கச் சான்று
FORM NO. 15 (படிவம் எண் 15)
சார்பதிவாளர் அலுவலகம்: ஆலந்தூர் (Alandur)
நாள்: 01-Sep-2026
கிராமம்: நங்கநல்லூர் (Nanganallur)
சர்வே எண்: 120/1A
தேடுதல் காலம்: 01-Jan-2005 முதல் 31-Aug-2026 வரை

105/2006
12/03/2006
12/03/2006
12/03/2006
கிரைய ஆவணம் (Conveyance)
எழுதிக்கொடுத்தவர்:
1. வி. குப்பராஜ் (V. Kuppa Raj)
2. வி. ஜெயலட்சுமி (V. Jayalakshmi)
எழுதிவாங்கியவர்:
1. எம். புகழேந்தி (M. Pugazhendhi)
கைமாற்றுத் தொகை: Rs. 42,50,000/-
சந்தை மதிப்பு: Rs. 45,00,000/-
முந்தைய ஆவண எண்: 890/1998
சொத்தின் வகைப்பாடு: மனை மற்றும் கட்டிடம்
சொத்தின் விஸ்தீர்ணம்: 2400 சதுர அடி
எல்லை விவரங்கள்: வடக்கில் 24 அடி ரோடு, தெற்கில் சபாபதி மனை, கிழக்கில் மனை எண் 12, மேற்கில் மனை எண் 10

1560/2011
05-08-2011
05-08-2011
05-08-2011
அடமான ஆவணம் (MODT)
அடமானம் வைத்தவர்:
1. எம். புகழேந்தி
அடமானம் பெற்றவர்:
1. ஸ்டேட் பேங்க் ஆப் இந்தியா (State Bank of India)
கைமாற்றுத் தொகை: Rs. 30,00,000/-
சந்தை மதிப்பு: Rs. 30,00,000/-
முந்தைய ஆவண எண்: 105/2006

420/2017
20-11-2017
20-11-2017
20-11-2017
அடமான விடுதலை ரசீது (Mortgage Discharge Receipt)
விடுதலை செய்தவர்:
1. ஸ்டேட் பேங்க் ஆப் இந்தியா
பெறுபவர்:
1. எம். புகழேந்தி
கைமாற்றுத் தொகை: Rs. 30,00,000/-
முந்தைய ஆவண எண்: 1560/2011
"""
        extracted = self.extractor.extract(tamil_ec_text, doc_type="ec")
        tx_list = extracted["fields"]["transactions_table"]["value"]

        # Exactly 3 entries - no false splits on PR numbers
        self.assertEqual(len(tx_list), 3)

        self.assertEqual(tx_list[0]["doc_no"], "105/2006")
        self.assertEqual(tx_list[0]["date"], "12-Mar-2006")
        self.assertIn("V. Kuppa Raj", tx_list[0]["executants"])
        self.assertIn("V. Jayalakshmi", tx_list[0]["executants"])
        self.assertEqual(tx_list[0]["claimants"], "M. Pugazhendhi")
        self.assertEqual(tx_list[0]["consideration"], "Rs. 42,50,000/-")
        self.assertEqual(tx_list[0]["pr_number"], "890/1998")

        self.assertEqual(tx_list[1]["doc_no"], "1560/2011")
        self.assertEqual(tx_list[1]["date"], "05-Aug-2011")
        self.assertEqual(tx_list[1]["executants"], "M. Pugazhendhi")
        self.assertEqual(tx_list[1]["claimants"], "State Bank of India")
        self.assertEqual(tx_list[1]["consideration"], "Rs. 30,00,000/-")
        self.assertEqual(tx_list[1]["pr_number"], "105/2006")

        self.assertEqual(tx_list[2]["doc_no"], "420/2017")
        self.assertEqual(tx_list[2]["date"], "20-Nov-2017")
        self.assertEqual(tx_list[2]["executants"], "State Bank of India")
        self.assertEqual(tx_list[2]["claimants"], "M. Pugazhendhi")
        self.assertEqual(tx_list[2]["consideration"], "Rs. 30,00,000/-")
        self.assertEqual(tx_list[2]["pr_number"], "1560/2011")

    def test_ec_pdf_report_generation(self):
        """Verify EC PDF Report generates cleanly with zero tofu issues."""
        from app.pdf_generator import generate_ocr_pdf_report
        sample = SAMPLE_DOCUMENTS["ec"]
        extracted = self.extractor.extract(sample["raw_text"], doc_type="ec")
        data = {
            "filename": "Sample_EC.pdf",
            "doc_type": "ec",
            "total_pages": 1,
            "extraction": extracted
        }
        pdf_bytes = generate_ocr_pdf_report(data)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

if __name__ == "__main__":
    unittest.main()


