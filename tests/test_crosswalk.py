import copy
import json
from pathlib import Path
import unittest
from phiage.crosswalk import CrosswalkError, validate_crosswalk

ROOT = Path(__file__).resolve().parents[1]
def fixture(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))

class CrosswalkTests(unittest.TestCase):
    def setUp(self):
        self.mapping = fixture("data/crosswalks/GSE307377_gsm_to_library.json")
        self.geo = fixture("data/receipts/GSE307377_geo_probe_2026-11-21.json")
        self.tpm = fixture("data/receipts/GSE307377_tpm_2026-11-21.json")

    def audit(self):
        return validate_crosswalk(self.mapping, self.geo, self.tpm)

    def test_exact_bijection_nine(self):
        r = self.audit()
        self.assertEqual(len(r["mapped_samples"]), 9)
        self.assertEqual(r["group_counts"], {"young": 4, "old": 5})
        self.assertTrue(r["sample_to_column_verified"])
        self.assertFalse(r["analysis_ready"])
        self.assertFalse(r["donor_independence_verified"])
        self.assertEqual(len({x["raw_index"] for x in r["mapped_samples"]}), 9)

    def test_reject_missing_record(self):
        self.mapping["samples"].pop()
        with self.assertRaises(CrosswalkError):
            self.audit()

    def test_reject_duplicate_gsm(self):
        self.mapping["samples"][1]["gsm_id"] = self.mapping["samples"][0]["gsm_id"]
        with self.assertRaisesRegex(CrosswalkError, "duplicate"):
            self.audit()

    def test_reject_duplicate_library(self):
        self.mapping["samples"][1]["library_id"] = self.mapping["samples"][0]["library_id"]
        with self.assertRaisesRegex(CrosswalkError, "duplicate"):
            self.audit()

    def test_reject_wrong_age(self):
        self.mapping["samples"][0]["age_years"] = 29
        with self.assertRaisesRegex(CrosswalkError, "age"):
            self.audit()

    def test_reject_swapped_old_young(self):
        self.mapping["samples"][0]["library_id"], self.mapping["samples"][2]["library_id"] = (
            self.mapping["samples"][2]["library_id"], self.mapping["samples"][0]["library_id"])
        with self.assertRaisesRegex(CrosswalkError, "group"):
            self.audit()

    def test_reject_wrong_source_url(self):
        self.mapping["samples"][0]["source_url"] = "https://untrusted.example/GSM9222986"
        with self.assertRaisesRegex(CrosswalkError, "source"):
            self.audit()

    def test_reject_modified_expression_column(self):
        self.tpm["normalized_table"]["structure"]["column_labels"][8] = "tags/MALFORMED"
        with self.assertRaisesRegex(CrosswalkError, "unrecognized"):
            self.audit()

    def test_reject_mismatched_suffix(self):
        self.tpm["normalized_table"]["structure"]["column_labels"][8] = (
            self.tpm["normalized_table"]["structure"]["column_labels"][8].replace("_S15", "_S90"))
        with self.assertRaisesRegex(CrosswalkError, "suffixes"):
            self.audit()

    def test_original_receipt_unmodified(self):
        self.assertTrue(self.geo["analysis_ready"] is False)
        self.assertTrue(self.tpm["analysis_ready"] is False)

if __name__ == "__main__":
    unittest.main()
