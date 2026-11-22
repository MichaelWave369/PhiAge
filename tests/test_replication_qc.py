"""Fictional synthetic inputs only. No age-effect statistical modeling."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from phiage.replication_qc import (
    ReplicationQCError, metadata_rows, summarize_source, inspect_fpkm, run_replication_qc,
)
BASE = Path(__file__).resolve().parents[1]
RECEIPT = json.loads((BASE/"data/receipts/GSE113957_cohort_source_observation_2026-11-22.json").read_text())

def soft(sample2_cell="CELL_B", sample2_platform="GPL222", disease2="HGPS"):
    return (
        "^SERIES = GSE113957\n"
        "^SAMPLE = GSM111\n"
        "!Sample_geo_accession = GSM111\n"
        "!Sample_title = DONOR_A\n"
        "!Sample_platform_id = GPL111\n"
        "!Sample_characteristics_ch1 = cell id: CELL_A\n"
        "!Sample_characteristics_ch1 = age: 22\n"
        "!Sample_characteristics_ch1 = sex: male\n"
        "!Sample_characteristics_ch1 = disease: Normal\n"
        "^SAMPLE = GSM222\n"
        "!Sample_geo_accession = GSM222\n"
        "!Sample_title = DONOR_B\n"
        f"!Sample_platform_id = {sample2_platform}\n"
        f"!Sample_characteristics_ch1 = cell id: {sample2_cell}\n"
        "!Sample_characteristics_ch1 = age: 6ys11mos\n"
        "!Sample_characteristics_ch1 = sex: female\n"
        f"!Sample_characteristics_ch1 = disease: {disease2}\n"
        "^PLATFORM = GPL111\n"
    )

def matrix(values=None):
    headers=["Transcript ID","chr","start","end","strand","Length","Copies","Annotation/Divergence",
             "DONOR_B","DONOR_A"]
    return ("\t".join(headers)+"\n" +
            "\t".join(["NM_001.2","chr1","1","20","+","19","1","protein-coding"] + (values or ["0","4.5"]))+"\n"+
            "\t".join(["NR_002.1","chr1","21","30","-","9","1","ncRNA","0","0"])+"\n")

class ReplicationTests(unittest.TestCase):
    def test_source_metadata_platform_and_cell_id(self):
        data=summarize_source(soft())
        self.assertEqual(data["observed_gsm_count"],2)
        self.assertEqual(data["cell_id_label"]["unique_labels"],2)
        self.assertEqual(data["platform_count"],2)
        self.assertEqual(data["platform_group_counts"]["GPL111"]["healthy_label_explicit"],1)
        self.assertEqual(data["platform_group_counts"]["GPL222"]["hgps_label_explicit"],1)
        self.assertFalse(data["donor_independence_verified"])

    def test_duplicate_cell_line_label_is_flagged(self):
        data=summarize_source(soft(sample2_cell="CELL_A"))
        self.assertEqual(data["cell_id_label"]["duplicate_label_excess"],1)
        self.assertTrue(data["metadata_has_unresolved_issues"])

    def test_source_title_must_be_unique(self):
        with self.assertRaisesRegex(ReplicationQCError,"duplicate sample title"):
            metadata_rows(soft().replace("!Sample_title = DONOR_B","!Sample_title = DONOR_A"))

    def test_hgps_vs_normal_not_equated(self):
        data=summarize_source(soft())
        self.assertEqual(data["public_source_label_counts"],
                         {"healthy_label_explicit":1,"hgps_label_explicit":1})

    def test_matrix_values_and_fractional_fpkm(self):
        q=inspect_fpkm(matrix(),["DONOR_A","DONOR_B"])
        self.assertEqual(q["feature_rows"],2)
        self.assertEqual(q["refseq_transcript_accession_syntax_count"],2)
        self.assertEqual(q["all_sample_zero_feature_rows"],1)
        self.assertEqual(q["sample_nonzero_feature_min"],0)
        self.assertEqual(q["sample_nonzero_feature_max"],1)
        self.assertTrue(q["numeric_structure_pass"])
        self.assertFalse(q["normalization_validated"])

    def test_nonfinite_must_fail_numeric_cleanliness(self):
        q=inspect_fpkm(matrix(["nan","-1"]),["DONOR_A","DONOR_B"])
        self.assertFalse(q["numeric_structure_pass"])
        self.assertEqual(q["invalid_or_nonfinite_numeric_cells"],1)
        self.assertEqual(q["negative_numeric_cells"],1)

    def test_mismatched_columns_rejected(self):
        with self.assertRaisesRegex(ReplicationQCError,"map one-to-one"):
            inspect_fpkm(matrix(),["DONOR_X","DONOR_B"])

    def test_bad_row_cardinality_rejected(self):
        with self.assertRaisesRegex(ReplicationQCError,"length"):
            inspect_fpkm(matrix().replace("\t0\t0\n","\t0\n"),["DONOR_A","DONOR_B"])

    def test_no_network_default(self):
        with patch("phiage.replication_qc.download_bounded",side_effect=AssertionError("no fetch")):
            with self.assertRaisesRegex(ReplicationQCError,"network disabled"):
                run_replication_qc(RECEIPT)

    def test_tampered_or_wrong_receipt_refused(self):
        corrupt=dict(RECEIPT)
        corrupt["source"]="GSE000000"
        with self.assertRaisesRegex(ReplicationQCError,"different series"):
            run_replication_qc(corrupt)
        corrupt=dict(RECEIPT)
        corrupt["source_soft_sha256"]="bad"
        with self.assertRaisesRegex(ReplicationQCError,"malformed"):
            run_replication_qc(corrupt)

if __name__=="__main__":
    unittest.main()
