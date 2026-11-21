"""Immutable observational receipt sanity checks (not a scientific analysis)."""
import json
from pathlib import Path
import re
import unittest

REC = Path(__file__).resolve().parents[1] / "data" / "receipts" / "GSE307377_geo_probe_2026-11-21.json"

class GEOReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = json.loads(REC.read_text(encoding="utf-8"))

    def test_expected_observation(self):
        r = self.receipt
        self.assertFalse(r["analysis_ready"])
        self.assertFalse(r["dataset_license_reviewed"])
        self.assertFalse(r["donor_overlap_checked"])
        self.assertFalse(r["supplementary_table"]["sample_column_crosswalk_verified"])
        self.assertFalse(r["supplementary_table"]["structure"]["table_contents_analysed"])

    def test_sample_and_header_cardinality(self):
        r = self.receipt
        sample = r["series_matrix"]["metadata"]
        sup = r["supplementary_table"]["structure"]
        self.assertEqual(sample["sample_count"], 9)
        self.assertEqual(sample["unique_GSM_count"], 9)
        self.assertEqual(len(sample["sample_catalog"]), 9)
        self.assertEqual(sample["age_field_cells"], 9)
        self.assertEqual(sup["column_count"], 17)
        self.assertEqual(sup["GSM_columns"], 0)
        self.assertEqual(len(sup["column_labels"]), 17)

    def test_hashes_and_source_urls_recorded(self):
        r = self.receipt
        for key in ("series_matrix", "supplementary_table"):
            artifact = r[key]
            self.assertRegex(artifact["sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(artifact["source_url"].startswith("https://ftp.ncbi.nlm.nih.gov/geo/series/"))

    def test_unique_public_sample_catalog(self):
        rows = self.receipt["series_matrix"]["metadata"]["sample_catalog"]
        ids = [x["gsm_id"] for x in rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(re.fullmatch(r"GSM[0-9]+", s) for s in ids))

if __name__ == "__main__":
    unittest.main()
