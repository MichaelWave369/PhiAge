"""Source discovery tests: candidates are leads, not independent verified datasets."""
import copy
import json
from pathlib import Path
import unittest

from phiage.sources import (
    RegistryError, audit_registry, canonical_sha256, review_blockers, validate_registry,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "source_registry.json"

class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_sources_exist_but_not_approved(self):
        audit = audit_registry(self.registry)
        self.assertEqual(audit["source_count"], 6)
        self.assertEqual(audit["analysis_ready_count"], 0)
        self.assertEqual(audit["review_counts"], {"candidate": 6})
        self.assertTrue(all(s["blockers"] for s in audit["sources"]))

    def test_ui_snapshot_is_exact_duplicate(self):
        self.assertEqual(REGISTRY.read_bytes(), (ROOT / "docs" / "sources.json").read_bytes())

    def test_duplicate_identifier_rejected(self):
        self.registry["sources"].append(copy.deepcopy(self.registry["sources"][0]))
        with self.assertRaisesRegex(RegistryError, "duplicate source"):
            validate_registry(self.registry)

    def test_unknown_overlap_reference_rejected(self):
        self.registry["sources"][0]["overlap_with"] = ["made-up-source"]
        with self.assertRaisesRegex(RegistryError, "unknown source"):
            validate_registry(self.registry)

    def test_missing_reuse_review_remains_blocked(self):
        source = self.registry["sources"][0]
        source.update(
            review_state="approved", sample_overlap_status="documented_nonoverlap",
            metadata_complete=True, curated_file_sha256="0" * 64,
        )
        self.assertIn("license-unreviewed", review_blockers(source))

    def test_protected_or_age_unknown_rejected_even_if_approved(self):
        source = self.registry["sources"][0]
        source.update(
            review_state="approved", license_status="reviewed", metadata_complete=True,
            sample_overlap_status="documented_nonoverlap",
            curated_file_sha256="f" * 64, access_scope="controlled_access",
            age_resolution="unverified",
        )
        self.assertIn("processed-data-not-cleared", review_blockers(source))
        self.assertIn("age-metadata-unverified", review_blockers(source))

    def test_sha_deterministic_independent_of_key_order(self):
        reversed_keys = dict(reversed(list(self.registry.items())))
        self.assertEqual(canonical_sha256(self.registry), canonical_sha256(reversed_keys))

    def test_metadata_claims_not_measured_results(self):
        for item in self.registry["sources"]:
            self.assertTrue(item["source_url"].startswith("https://"))
            self.assertEqual(item["review_state"], "candidate")
            self.assertEqual(item["license_status"], "unreviewed")
            self.assertEqual(item["sample_overlap_status"], "unknown")

if __name__ == "__main__":
    unittest.main()
