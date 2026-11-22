"""Only synthetic metadata. Never fits a model or exports donor identifiers."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from phiage.common_support import audit_common_support,run_common_support
from phiage.replication_qc import ReplicationQCError

BASE=Path(__file__).resolve().parents[1]
PLAN=json.loads((BASE/"data/design/EXP001_common_support_v09.json").read_text())
SOURCE=json.loads((BASE/"data/receipts/GSE113957_cohort_source_observation_2026-11-22.json").read_text())
OVERLAP=json.loads((BASE/"data/receipts/GSE113957_GSE307377_overlap_2026-11-22.json").read_text())

def fixture(rows):
    out=["^SERIES = GSE113957"]
    for i,(age,sex,platform,status,cell) in enumerate(rows):
        out+= [
            f"^SAMPLE = GSM{100+i}",
            f"!Sample_geo_accession = GSM{100+i}",
            f"!Sample_title = sample_{i}",
            f"!Sample_platform_id = {platform}",
            f"!Sample_characteristics_ch1 = disease: {status}",
            f"!Sample_characteristics_ch1 = age: {age}",
            f"!Sample_characteristics_ch1 = sex: {sex}",
            f"!Sample_characteristics_ch1 = cell id: {cell}",
        ]
    return "\n".join(out)+"\n"

class CommonSupportTests(unittest.TestCase):
    def test_30_49_excludes_hgps_children_and_age_50(self):
        metadata=fixture([
            (30,"female","GPL18573","Normal","A"),
            (49,"female","GPL16791","Normal","B"),
            (50,"female","GPL16791","Normal","C"),
            (20,"female","GPL18573","Normal","D"),
            (40,"male","GPL18573","HGPS","E"),
        ])
        result=audit_common_support(metadata,PLAN)
        self.assertEqual(result["primary_metadata"]["n"],1)
        self.assertEqual(result["comparison_metadata"]["n"],1)
        self.assertEqual(result["excluded_source_status_hgps"],1)
        self.assertFalse(result["analysis_ready"])
        self.assertFalse(result["sample_matching_performed"])

    def test_no_cross_platform_sex_support_blocks(self):
        r=audit_common_support(fixture([
            (35,"female","GPL18573","Normal","A"),
            (35,"male","GPL16791","Normal","B"),
        ]),PLAN)
        self.assertIn("30-39/female",r["missing_strata"])
        self.assertIn("30-39/male",r["missing_strata"])
        self.assertEqual(r["maximum_balanced_pair_capacity"],0)
        self.assertFalse(r["metadata_balance_thresholds_passed"])

    def test_exact_sex_age_pair_capacity_only_counts_metadata(self):
        groups=[]
        for sex in ("female","male"):
            for age in (32,42):
                for i in range(3):
                    groups.append((age,sex,"GPL18573","Normal",f"A_{sex}_{age}_{i}"))
                for i in range(2):
                    groups.append((age,sex,"GPL16791","Normal",f"B_{sex}_{age}_{i}"))
        r=audit_common_support(fixture(groups),PLAN)
        self.assertEqual(r["maximum_balanced_pair_capacity"],8)
        self.assertEqual(r["maximum_balanced_samples_total"],16)
        self.assertTrue(all(s["at_least_two_each"] for s in r["sex_by_age_decade_strata"]))
        self.assertFalse(r["metadata_balance_thresholds_passed"])  # synthetic source has not 143 records
        self.assertNotIn("A_female_32_0",str(r))
        self.assertFalse(r["donor_independence_verified"])

    def test_cell_label_collision_stops(self):
        r=audit_common_support(fixture([
            (34,"female","GPL18573","Normal","SAME"),
            (36,"female","GPL16791","Normal","same"),
        ]),PLAN)
        self.assertEqual(r["source_cell_id_duplicate_label_excess"],1)
        self.assertTrue(any("cell-id" in x for x in r["metadata_blockers"]))

    def test_frozen_design_cannot_change_age_or_allow_fitting(self):
        p=dict(PLAN);p["lower_age_years"]=18
        with self.assertRaisesRegex(ReplicationQCError,"30"):
            audit_common_support(fixture([]),p)
        p=dict(PLAN);p["allow_age_model_fitting"]=True
        with self.assertRaisesRegex(ReplicationQCError,"disabled"):
            audit_common_support(fixture([]),p)

    def test_network_off_and_receipt_changes_stop(self):
        with patch("phiage.common_support.download_bounded", side_effect=AssertionError("must not fetch")):
            with self.assertRaisesRegex(ReplicationQCError,"network disabled"):
                run_common_support(PLAN,SOURCE,OVERLAP)
        o=dict(OVERLAP);o["exact_refseq_identifier_overlap"]=27142
        with self.assertRaises(ReplicationQCError):
            run_common_support(PLAN,SOURCE,o)
        s=dict(SOURCE);s["source_soft_sha256"]="0"*64
        with self.assertRaises(ReplicationQCError):
            run_common_support(PLAN,s,OVERLAP)

if __name__=="__main__":
    unittest.main()
