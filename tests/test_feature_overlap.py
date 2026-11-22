"""Synthetic cross-cohort transcript-ID compatibility tests."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from phiage.feature_overlap import compare_transcripts, run_overlap
from phiage.replication_qc import ReplicationQCError

ROOT = Path(__file__).resolve().parents[1]
PRIMARY=json.loads((ROOT/"data/receipts/GSE113957_cohort_source_observation_2026-11-22.json").read_text())
SECOND=json.loads((ROOT/"data/receipts/GSE307377_tpm_2026-11-21.json").read_text())

def mock_table(cohort, ids):
    width=151 if cohort=="GSE113957" else 17
    first="Transcript ID" if cohort=="GSE113957" else "Transcript/RepeatID"
    head=[first,"chr","start","end","strand","Length","Copies","Annotation/Divergence"]
    head += ["sample"+str(i) for i in range(width-8)]
    rows=["\t".join(head)]
    for feature in ids:
        rows.append("\t".join([feature,"chr1","1","2","+","1","1","x"]+["0"]*(width-8)))
    return "\n".join(rows)+"\n"

class FeatureOverlapTests(unittest.TestCase):
    def test_all_exact_matches(self):
        ids=["NM_001.2","NR_002.3","XM_003.1"]
        r=compare_transcripts(mock_table("GSE113957",ids),mock_table("GSE307377",ids))
        self.assertEqual(r["exact_refseq_identifier_overlap"],3)
        self.assertTrue(r["exact_identifier_set_equal"])
        self.assertTrue(r["identical_transcript_row_order"])
        self.assertFalse(r["analysis_ready"])
        self.assertFalse(r["expression_scale_harmonized"])

    def test_disjoint_and_version_changed(self):
        a=["NM_001.1","NR_002.5"]
        b=["NM_001.2","NR_002.5"]
        r=compare_transcripts(mock_table("GSE113957",a),mock_table("GSE307377",b))
        self.assertEqual(r["exact_refseq_identifier_overlap"],1)
        self.assertEqual(r["unversioned_identifier_overlap"],2)
        self.assertFalse(r["exact_identifier_set_equal"])

    def test_reversed_order_does_not_infer_equal_rows(self):
        a=["NM_001.1","NR_002.1"]
        r=compare_transcripts(mock_table("GSE113957",a),mock_table("GSE307377",list(reversed(a))))
        self.assertTrue(r["exact_identifier_set_equal"])
        self.assertFalse(r["identical_transcript_row_order"])

    def test_duplicate_refseq_record_not_silently_merged(self):
        a=["NM_001.1","NM_001.1"]
        r=compare_transcripts(mock_table("GSE113957",a),mock_table("GSE307377",["NM_001.1"]))
        self.assertEqual(r["GSE113957_duplicate_source_accessions"],1)
        self.assertTrue(r["exact_identifier_set_equal"])  # equal unique sets, duplicates separately visible

    def test_wrong_header_fails(self):
        a=mock_table("GSE113957",["NM_001.1"]).replace("Transcript ID","Gene Identifier")
        with self.assertRaisesRegex(ReplicationQCError,"heading"):
            compare_transcripts(a,mock_table("GSE307377",["NM_001.1"]))

    def test_network_disabled_by_default(self):
        with patch("phiage.feature_overlap.download_bounded", side_effect=AssertionError("network")):
            with self.assertRaisesRegex(ReplicationQCError,"network disabled"):
                run_overlap(PRIMARY,SECOND)

if __name__=="__main__":
    unittest.main()
