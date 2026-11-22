import json
from pathlib import Path
import unittest
from unittest.mock import patch
from phiage.design_preflight import audit_metadata,run_preflight
from phiage.replication_qc import ReplicationQCError

ROOT=Path(__file__).resolve().parents[1]
PLAN=json.loads((ROOT/"data/design/EXP001_frozen_preflight_v08.json").read_text())
RECEIPT=json.loads((ROOT/"data/receipts/GSE113957_cohort_source_observation_2026-11-22.json").read_text())
OVERLAP=json.loads((ROOT/"data/receipts/GSE113957_GSE307377_overlap_2026-11-22.json").read_text())

def soft(records):
    x=["^SERIES = GSE113957"]
    for i,(age,sex,platform,status,cell) in enumerate(records):
        x.extend([
            f"^SAMPLE = GSM{100+i}",f"!Sample_geo_accession = GSM{100+i}",
            f"!Sample_title = cohort_{i}",f"!Sample_platform_id = {platform}",
            f"!Sample_characteristics_ch1 = age: {age}",
            f"!Sample_characteristics_ch1 = sex: {sex}",
            f"!Sample_characteristics_ch1 = disease: {status}",
            f"!Sample_characteristics_ch1 = cell id: {cell}",
        ])
    return "\n".join(x)+"\n"

class DesignPreflightTests(unittest.TestCase):
    def test_disjoint_platform_ages_block_transport(self):
        data=soft([
            (22,"male","GPL18573","Normal","A"),
            (26,"female","GPL18573","Normal","B"),
            (67,"male","GPL16791","Normal","C"),
            (74,"female","GPL16791","Normal","D"),
            (8,"female","GPL18573","HGPS","E"),
        ])
        r=audit_metadata(data,PLAN)
        self.assertEqual(r["excluded_hgps_samples"],1)
        self.assertEqual(r["eligible_adult_healthy"]["sample_count"],4)
        self.assertIsNone(r["age_range_intersection_years"])
        self.assertFalse(r["exploratory_transport_metadata_gate_passed"])
        self.assertFalse(r["analysis_ready"])

    def test_teenagers_excluded_without_ignoring_hgps(self):
        r=audit_metadata(soft([
            (8,"male","GPL18573","Normal","A"),
            (22,"male","GPL18573","Normal","B"),
            (8,"female","GPL18573","HGPS","C"),
        ]),PLAN)
        self.assertEqual(r["healthy_all_ages"]["sample_count"],2)
        self.assertEqual(r["eligible_adult_healthy"]["sample_count"],1)
        self.assertEqual(r["excluded_hgps_samples"],1)

    def test_cell_id_collision_is_flagged_not_promoted(self):
        r=audit_metadata(soft([
            (30,"female","GPL18573","Normal","A"),
            (35,"female","GPL16791","Normal","A"),
        ]),PLAN)
        self.assertEqual(r["source_cell_id_duplicate_label_excess"],1)
        self.assertIn("Source cell-id label collisions or missing identifiers",
                      r["transport_metadata_gate_blockers"])
        self.assertFalse(r["donor_independence_verified"])

    def test_age_range_overlap_alone_not_transport_authorization(self):
        r=audit_metadata(soft([
            (34,"male","GPL18573","Normal","A"),
            (34,"female","GPL16791","Normal","B"),
        ]),PLAN)
        self.assertEqual(r["age_range_intersection_years"],[34.0,34.0])
        self.assertFalse(r["exploratory_transport_metadata_gate_passed"])
        self.assertFalse(r["training_or_hypothesis_test_performed"])

    def test_reject_changed_population(self):
        plan=dict(PLAN)
        plan["primary_population"]={"explicit_source_label":"hgps_label_explicit","minimum_age_years":1}
        with self.assertRaises(ReplicationQCError):
            audit_metadata(soft([(8,"female","GPL18573","HGPS","A")]),plan)

    def test_no_network_and_pinned_overlap(self):
        with patch("phiage.design_preflight.download_bounded",side_effect=AssertionError("no internet")):
            with self.assertRaisesRegex(ReplicationQCError,"network disabled"):
                run_preflight(PLAN,RECEIPT,OVERLAP)
        overlap=dict(OVERLAP)
        overlap["exact_refseq_identifier_overlap"]=27142
        with self.assertRaisesRegex(ReplicationQCError,"changed"):
            run_preflight(PLAN,RECEIPT,overlap)

if __name__=="__main__":
    unittest.main()
