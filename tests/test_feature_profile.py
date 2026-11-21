"""Synthetic and archived-metadata tests for structural feature inspection."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from phiage.crosswalk import validate_crosswalk
from phiage.expression_qc import ExpressionQCError
from phiage.feature_profile import classify_feature_id, inspect_profile, run_profile

ROOT = Path(__file__).resolve().parents[1]
def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))

class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.mapping = load("data/crosswalks/GSE307377_gsm_to_library.json")
        self.geo = load("data/receipts/GSE307377_geo_probe_2026-11-21.json")
        self.tpm = load("data/receipts/GSE307377_tpm_2026-11-21.json")
        self.crosswalk = validate_crosswalk(self.mapping, self.geo, self.tpm)
        self.labels = self.tpm["normalized_table"]["structure"]["column_labels"]
        self.meta = ["Transcript/RepeatID annotation" + "x" * 170,
                     "chr", "start", "end", "strand", "Length", "Copies", "Annotation/Divergence"]
        self.headers = self.meta + self.labels[8:]

    def sample(self, values):
        return "\t".join(self.headers) + "\n" + "\n".join(
            "\t".join([fid, "chr1", str(i), str(i+50), "+", "50", "1", ann]
                      + [str(v) for v in vals])
            for i, (fid, ann, vals) in enumerate(values, 1)
        ) + "\n"

    def test_patterns_syntactic_only(self):
        self.assertEqual(classify_feature_id("NM_00123.1"), "RefSeq_transcript_accession_syntax")
        self.assertEqual(classify_feature_id("ENST00000000001"), "Ensembl_transcript_accession_syntax")
        self.assertEqual(classify_feature_id("BRCA1"), "other_unclassified_syntax")

    def test_technical_profile_on_synthetic_fixtures(self):
        text = self.sample([
            ("NM_001.1", "GENE|protein-coding", [1,2,3,4,5,6,7,8,9]),
            ("NR_020.1", "GENE|noncoding", [3,2,5,4,7,6,9,8,1]),
            ("RPT_1", "OTHER|repeat", [0]*9),
            ("ENST00000000001", "GENE|protein-coding", [4,1,4,2,2,5,8,1,8]),
        ])
        report = inspect_profile(text, self.labels, self.crosswalk)
        self.assertEqual(report["feature_rows"],4)
        self.assertEqual(report["all_sample_zero_rows"],1)
        self.assertEqual(len(report["per_sample_descriptives"]),9)
        self.assertEqual(len(report["sample_similarity_pairs"]),36)
        self.assertEqual(report["feature_id_syntax_counts"]["RefSeq_transcript_accession_syntax"],2)
        self.assertFalse(report["analysis_ready"])
        self.assertEqual(report["claim_level"],"TECHNICAL_QC_ONLY")
        self.assertTrue(all(p["correlation"] is None or -1<=p["correlation"]<=1 for p in report["sample_similarity_pairs"]))

    def test_all_constant_profiles_have_null_correlation(self):
        text=self.sample([
            ("NM_1.1","code|x",[0]*9),
            ("NM_2.1","code|x",[0]*9),
            ("NM_3.1","code|x",[0]*9),
        ])
        report=inspect_profile(text,self.labels,self.crosswalk)
        self.assertTrue(all(p["correlation"] is None for p in report["sample_similarity_pairs"]))

    def test_invalid_numeric_refused(self):
        text=self.sample([("NM_1.1","a|b",[float("nan")]+[1]*8)])
        with self.assertRaises(ExpressionQCError):
            inspect_profile(text,self.labels,self.crosswalk)

    def test_duplicate_feature_refused(self):
        text=self.sample([("NM_1.1","a|b",[1]*9),("NM_1.1","a|b",[2]*9)])
        with self.assertRaises(ExpressionQCError):
            inspect_profile(text,self.labels,self.crosswalk)

    def test_no_network_by_default(self):
        with patch("phiage.feature_profile.download_bounded",side_effect=AssertionError("no network")):
            with self.assertRaisesRegex(ExpressionQCError,"network disabled"):
                run_profile(self.mapping,self.geo,self.tpm)

if __name__=="__main__":
    unittest.main()
