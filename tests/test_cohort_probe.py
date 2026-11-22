"""Synthetic test fixtures: never assume unverified GEO sample grouping."""
import unittest
from unittest.mock import patch

from phiage.cohort_probe import (
    CohortProbeError, probe_candidate, summarize_matrix,
)

SYNTHETIC = (
    '!Series_title\t"FICTIONAL cohort"\n'
    '!Sample_geo_accession\t"GSM111"\t"GSM222"\t"GSM333"\n'
    '!Sample_title\t"Healthy fibroblast"\t"HGPS fibroblast"\t"Anonymous donor"\n'
    '!Sample_characteristics_ch1\t"age: 22"\t"age: 8"\t"age: 65"\n'
    '!Sample_characteristics_ch1\t"disease: healthy"\t"disease: HGPS"\t"disease: unknown"\n'
    '!series_matrix_table_begin\n'
    '"ID_REF"\t"GSM111"\t"GSM222"\t"GSM333"\n'
)

class CohortProbeTests(unittest.TestCase):
    def test_synthetic_group_is_not_automatically_verified(self):
        result = summarize_matrix(SYNTHETIC)
        self.assertEqual(result["public_gsm_sample_count"], 3)
        self.assertEqual(result["observed_sample_label_counts"],
                         {"healthy_label_explicit": 1, "hgps_label_explicit": 1, "unknown": 1})
        self.assertEqual(result["parsed_sample_age_count"], 3)
        self.assertEqual(result["parsed_age_decade_bins"], {"0-9": 1, "20-29": 1, "60-69": 1})
        self.assertFalse(result["claimed_split_verified_from_metadata"])
        self.assertFalse(result["donor_independence_verified"])
        self.assertFalse(result["analysis_ready"])

    def test_no_network_default(self):
        with patch("phiage.cohort_probe.download_bounded", side_effect=AssertionError("no fetch")):
            with self.assertRaisesRegex(CohortProbeError, "network disabled"):
                probe_candidate()

    def test_invalid_accession_rejected(self):
        with self.assertRaisesRegex(CohortProbeError, "allowed"):
            probe_candidate("GSE307377", allow_network=True)

    def test_age_contradiction_rejected(self):
        altered = SYNTHETIC.replace('!series_matrix_table_begin',
             '!Sample_characteristics_ch1\t"age: 23"\t"other: text"\t"other: text"\n'
             '!series_matrix_table_begin')
        with self.assertRaisesRegex(CohortProbeError, "contradictory"):
            summarize_matrix(altered)

    def test_duplicate_gsm_rejected(self):
        altered = SYNTHETIC.replace('"GSM333"', '"GSM222"')
        with self.assertRaisesRegex(Exception, "duplicate GSM"):
            summarize_matrix(altered)

    def test_missing_age_does_not_become_age_zero(self):
        altered = SYNTHETIC.replace('"age: 65"', '"age: unknown"')
        with self.assertRaisesRegex(CohortProbeError, "age characteristic"):
            summarize_matrix(altered)

    def test_unsupported_characteristic_does_not_prove_healthy(self):
        altered = SYNTHETIC.replace('"disease: unknown"', '"cell passage: 3"')
        result = summarize_matrix(altered)
        self.assertEqual(result["observed_sample_label_counts"]["unknown"], 1)

    def test_conflicting_status_not silently_resolved(self):
        altered = SYNTHETIC.replace('"disease: HGPS"', '"disease: healthy, HGPS"')
        result = summarize_matrix(altered)
        self.assertEqual(result["observed_sample_label_counts"]["conflicting"], 1)

    def test_metadata_cardinality_rejected(self):
        altered = SYNTHETIC.replace('\t"disease: unknown"', '')
        with self.assertRaisesRegex(Exception, "cardinality"):
            summarize_matrix(altered)

if __name__ == "__main__":
    unittest.main()
