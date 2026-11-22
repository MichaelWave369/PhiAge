"""Synthetic public metadata only: never identifies private human donors."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from phiage.provenance_gate import audit_provenance,run_provenance,parse_soft_samples,parse_matrix_samples
from phiage.replication_qc import ReplicationQCError

ROOT=Path(__file__).resolve().parents[1]
SOURCE=json.loads((ROOT/"data/receipts/GSE113957_cohort_source_observation_2026-11-22.json").read_text())
GEO=json.loads((ROOT/"data/receipts/GSE307377_geo_probe_2026-11-21.json").read_text())
MAPPING=json.loads((ROOT/"data/crosswalks/GSE307377_gsm_to_library.json").read_text())

def soft(cell_a="GM123",cell_b="GM124",passage_a=None):
    rows=["^SERIES = GSE113957"]
    for i,(gsm,cell) in enumerate((("GSM111",cell_a),("GSM222",cell_b))):
        rows.extend([
            "^SAMPLE = "+gsm,
            "!Sample_geo_accession = "+gsm,
            "!Sample_title = cellline_"+str(i),
            "!Sample_growth_protocol_ch1 = public biobank culture",
            "!Sample_platform_id = GPL111",
            "!Sample_source_name_ch1 = fibroblasts",
            "!Sample_characteristics_ch1 = cell id: "+cell,
            "!Sample_characteristics_ch1 = disease: Normal",
        ])
        if passage_a is not None and i==0:
            rows.append("!Sample_characteristics_ch1 = passage: "+str(passage_a))
    rows.append("^PLATFORM = GPL123")
    return "\n".join(rows)+"\n"

def matrix():
    gsm=[row["gsm_id"] for row in MAPPING["samples"]]
    rows=[
        "!Series_geo_accession\tGSE307377",
        "!Sample_geo_accession\t"+"\t".join(gsm),
        "!Sample_title\t"+"\t".join('"label_'+str(i)+'"' for i in range(9)),
        "!Sample_characteristics_ch1\t"+"\t".join('"age: '+str(row["age_years"])+'"' for row in MAPPING["samples"]),
        "!Sample_growth_protocol_ch1\t"+"\t".join('"one lab shared protocol"' for _ in gsm),
        "!series_matrix_table_begin",
    ]
    return "\n".join(rows)+"\n"

class ProvenanceGateTests(unittest.TestCase):
    def test_flags_missing_cross_source_subject_identity(self):
        x=audit_provenance(soft(),matrix(),MAPPING)
        self.assertEqual(x["source_cohorts"][0]["geo_sample_records"],2)
        self.assertEqual(x["source_cohorts"][1]["geo_sample_records"],9)
        self.assertEqual(x["source_cohorts"][0]["identity"]["cell_id_field_present"],2)
        self.assertEqual(x["source_cohorts"][1]["identity"]["cell_id_field_present"],0)
        self.assertFalse(x["cross_cohort_same_person_linkage_evaluable"])
        self.assertIsNone(x["cross_cohort_common_subject_ids"])
        self.assertFalse(x["analysis_ready"])
        self.assertNotIn("GM123",str(x))

    def test_duplicate_cell_label_never_proves_donor(self):
        x=audit_provenance(soft(cell_b="gm123"),matrix(),MAPPING)
        self.assertEqual(x["source_cohorts"][0]["identity"]["cell_id_duplicate_label_excess"],1)
        self.assertFalse(x["donor_independence_verified"])

    def test_protocol_text_count_and_passage_coverage(self):
        x=audit_provenance(soft(passage_a=3),matrix(),MAPPING)
        one=x["source_cohorts"][0]
        self.assertEqual(one["identity"]["sample_level_passage_field_present"],1)
        self.assertEqual(one["public_protocol_metadata"]["growth"]["distinct_text_versions"],1)
        self.assertFalse(one["public_protocol_metadata"]["growth"]["text_validated"])

    def test_matrix_source_mismatch_fails(self):
        text=matrix().replace("GSM9222986","GSM999111")
        with self.assertRaisesRegex(ReplicationQCError,"crosswalk GSM mismatch"):
            audit_provenance(soft(),text,MAPPING)

    def test_soft_duplicates_fail(self):
        x=soft().replace("GSM222","GSM111")
        with self.assertRaisesRegex(ReplicationQCError,"duplicate GSM"):
            audit_provenance(x,matrix(),MAPPING)


    def test_protocol_fingerprint_by_platform_without_raw_text(self):
        text=soft().replace(
            "!Sample_growth_protocol_ch1 = public biobank culture\n"
            "!Sample_platform_id = GPL111\n"
            "!Sample_source_name_ch1 = fibroblasts\n"
            "!Sample_characteristics_ch1 = cell id: GM124",
            "!Sample_growth_protocol_ch1 = other culture source\n"
            "!Sample_platform_id = GPL222\n"
            "!Sample_source_name_ch1 = fibroblasts\n"
            "!Sample_characteristics_ch1 = cell id: GM124",
        )
        result=audit_provenance(text,matrix(),MAPPING)
        per=result["source_cohorts"][0]["protocol_vs_platform"]
        self.assertEqual(per["platform_sample_counts"],{"GPL111":1,"GPL222":1})
        self.assertNotIn("public biobank culture",str(per))
        self.assertNotIn("other culture source",str(per))
        self.assertFalse(result["cross_cohort_same_person_linkage_evaluable"])

    def test_network_default_off_and_checksum_fail_closed(self):
        with patch("phiage.provenance_gate.download_bounded",side_effect=AssertionError("network")):
            with self.assertRaisesRegex(ReplicationQCError,"network disabled"):
                run_provenance(SOURCE,GEO,MAPPING)
        a=dict(SOURCE);a["source_soft_sha256"]="bad"
        with self.assertRaisesRegex(ReplicationQCError,"checksum"):
            run_provenance(a,GEO,MAPPING)

if __name__=="__main__":
    unittest.main()
