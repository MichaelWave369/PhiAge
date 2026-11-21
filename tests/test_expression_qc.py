
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from phiage.expression_qc import ExpressionQCError, inspect_table, run_qc
from phiage.crosswalk import validate_crosswalk

ROOT = Path(__file__).resolve().parents[1]
def data(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

class ExpressionQCTests(unittest.TestCase):
    def setUp(self):
        self.mapping = data("data/crosswalks/GSE307377_gsm_to_library.json")
        self.geo = data("data/receipts/GSE307377_geo_probe_2026-11-21.json")
        self.tpm = data("data/receipts/GSE307377_tpm_2026-11-21.json")
        self.r = validate_crosswalk(self.mapping, self.geo, self.tpm)
        self.headers = ["Transcript/RepeatID", "chr", "start", "end",
                        "strand", "Length", "Copies", "Annotation/Divergence"]
        self.headers += [x["raw_header"] for x in sorted(self.r["mapped_samples"],
                         key=lambda e: e["raw_index"])]

    def fake_text(self, rows=None):
        rows = rows or [
            ["RE_A", "chr1", "1", "100", "+", "100", "2", "x"] + ["0"] * 9,
            ["RE_B", "chr2", "2", "101", "-", "99", "1", "y"] + ["2"] * 9,
        ]
        return "\t".join(self.headers) + "\n" + "\n".join("\t".join(r) for r in rows)

    def test_clean_synthetic_example(self):
        report = inspect_table(self.fake_text(), self.headers, kind="raw")
        self.assertEqual(report["feature_rows"], 2)
        self.assertEqual(report["sample_columns"], 9)
        self.assertTrue(report["structural_numeric_qc_pass"])
        self.assertEqual(report["duplicate_feature_ids"], 0)
        self.assertFalse(report["feature_semantics_verified"])

    def test_missing_cells_reported(self):
        text = self.fake_text().replace("\t2\t2\t2\t2\t2\t2\t2\t2\t2", "\t2\t2\t2\tNA\t2\t2\t2\t2\t2")
        report = inspect_table(text, self.headers, kind="raw")
        self.assertFalse(report["structural_numeric_qc_pass"])
        self.assertEqual(report["missing_numeric_cells"], 1)

    def test_nan_and_negative_reported(self):
        row = ["RE_BAD", "chr1", "1", "2", "+", "1", "1", "x"] + [
            "nan", "-5", "3.4"] + ["0"] * 6
        report = inspect_table(self.fake_text([row]), self.headers, kind="raw")
        self.assertEqual(report["non_numeric_or_nonfinite_cells"], 1)
        self.assertEqual(report["negative_cells"], 1)
        self.assertEqual(report["non_integer_raw_cells"], 1)

    def test_duplicate_feature_ids_are_reported(self):
        row = ["RE_A", "chr1", "1", "2", "+", "1", "1", "x"] + ["1"] * 9
        report = inspect_table(self.fake_text([row,row]), self.headers, kind="raw")
        self.assertEqual(report["duplicate_feature_ids"], 1)

    def test_mismatched_header_stops(self):
        with self.assertRaisesRegex(ExpressionQCError, "header"):
            inspect_table(self.fake_text().replace("RE_A", "RE_A"), self.headers[:-1], kind="raw")

    def test_wrong_column_count_stops(self):
        text = self.fake_text().replace("\t" + self.headers[-1], "", 1)
        with self.assertRaisesRegex(ExpressionQCError, "header"):
            inspect_table(text, self.headers, kind="raw")

    def test_no_network_by_default(self):
        with self.assertRaisesRegex(ExpressionQCError, "network disabled"):
            run_qc(self.mapping, self.geo, self.tpm)
        with patch("phiage.expression_qc.download_bounded", side_effect=AssertionError("must not fetch")):
            with self.assertRaises(ExpressionQCError):
                run_qc(self.mapping, self.geo, self.tpm)

if __name__ == "__main__":
    unittest.main()
