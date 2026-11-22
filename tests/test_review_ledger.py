"""Deterministic safety tests; no web, individual records or age modeling."""
import copy
import json
from pathlib import Path
import unittest

from phiage.review_ledger import audit_review
from phiage.replication_qc import ReplicationQCError

ROOT=Path(__file__).resolve().parents[1]
LEDGER=json.loads((ROOT/"data/evidence/EXP001_provenance_review_v11.json").read_text())
OBS=json.loads((ROOT/"data/receipts/GSE113957_GSE307377_provenance_gate_2026-11-22.json").read_text())

class ReviewLedgerTests(unittest.TestCase):
    def test_verified_source_counts_but_never_donor_independence(self):
        r=audit_review(LEDGER,OBS)
        self.assertEqual(r["cohort_sample_counts"],{"GSE113957":143,"GSE307377":9})
        self.assertEqual(r["explicit_subject_id_field_count"],0)
        self.assertEqual(r["geo_sample_level_passage_field_count"],0)
        self.assertEqual(r["blocked_review_gate_count"],8)
        self.assertFalse(r["analysis_ready"])
        self.assertFalse(r["linked_supplement_sample_level_join_verified"])
        self.assertNotIn("GSM9222986",str(r))

    def test_cannot_open_research_gate(self):
        bad=copy.deepcopy(LEDGER)
        bad["review_gates"][0]["status"]="verified"
        with self.assertRaisesRegex(ReplicationQCError,"blocked"):
            audit_review(bad,OBS)

    def test_cannot_infer_supplement_join_from_published_means(self):
        bad=copy.deepcopy(LEDGER)
        bad["policies"]["supplement_sample_level_verified"]=True
        with self.assertRaisesRegex(ReplicationQCError,"unsafe"):
            audit_review(bad,OBS)
        bad=copy.deepcopy(LEDGER)
        target=next(c for c in bad["claims"] if c["id"]=="fleischer-supplement-uninspected")
        target["level"]="sample-metadata"
        with self.assertRaisesRegex(ReplicationQCError,"cannot be promoted"):
            audit_review(bad,OBS)

    def test_cannot_treat_biomaterial_mta_as_expression_license(self):
        bad=copy.deepcopy(LEDGER)
        source=next(s for s in bad["sources"] if s["id"]=="coriell-mta")
        source["url"]="https://bad-untrusted.example/terms"
        with self.assertRaisesRegex(ReplicationQCError,"approved original host"):
            audit_review(bad,OBS)

    def test_required_source_refs_cannot_be_fabricated(self):
        bad=copy.deepcopy(LEDGER)
        bad["claims"][0]["source_ids"]=["not-a-source"]
        with self.assertRaisesRegex(ReplicationQCError,"absent source"):
            audit_review(bad,OBS)

    def test_duplicates_and_missing_gate_rejected(self):
        bad=copy.deepcopy(LEDGER);bad["sources"][1]["id"]=bad["sources"][0]["id"]
        with self.assertRaisesRegex(ReplicationQCError,"duplicate source"):
            audit_review(bad,OBS)
        bad=copy.deepcopy(LEDGER);bad["review_gates"].pop()
        with self.assertRaisesRegex(ReplicationQCError,"safety gates"):
            audit_review(bad,OBS)

    def test_source_receipt_drift_rejected(self):
        bad=copy.deepcopy(OBS)
        bad["source_cohorts"][0]["identity"]["subject_identifier_field_present"]=1
        with self.assertRaisesRegex(ReplicationQCError,"counts drifted"):
            audit_review(LEDGER,bad)
        bad=copy.deepcopy(OBS);bad["source_matrix_sha256"]="a"*64
        with self.assertRaisesRegex(ReplicationQCError,"source hash"):
            audit_review(LEDGER,bad)

if __name__=="__main__":
    unittest.main()
