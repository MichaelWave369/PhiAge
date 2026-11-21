import gzip
import unittest

from phiage.geo_probe import (
    GEOProbeError, decompress_bounded, geo_matrix_url, geo_supplement_url,
    inspect_supplement_header, parse_series_matrix, probe,
)

SYNTHETIC_MATRIX = (
    '!Series_title\t"FICTIONAL dataset"\n'
    '!Sample_geo_accession\t"GSM1234567"\t"GSM1234568"\n'
    '!Sample_title\t"young"\t"old"\n'
    '!Sample_characteristics_ch1\t"age: 25"\t"age: 75"\n'
    '!series_matrix_table_begin\n'
    '"ID_REF"\t"GSM1234567"\t"GSM1234568"\n'
    '"FAKE_GENE"\t"10"\t"20"\n'
)

class GEOProbeTests(unittest.TestCase):
    def test_known_urls(self):
        self.assertEqual(
            geo_matrix_url("GSE307377"),
            "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE307nnn/GSE307377/matrix/GSE307377_series_matrix.txt.gz",
        )
        self.assertEqual(
            geo_supplement_url("GSE307377"),
            "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE307nnn/GSE307377/suppl/GSE307377_raw.txt.gz",
        )
        self.assertEqual(
            geo_supplement_url("GSE307377", "tpm"),
            "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE307nnn/GSE307377/suppl/GSE307377_tpm.txt.gz",
        )
        with self.assertRaises(GEOProbeError):
            geo_supplement_url("GSE307377", "invented")

    def test_metadata_cardinality(self):
        parsed = parse_series_matrix(SYNTHETIC_MATRIX, "GSE307377")
        self.assertEqual(parsed["sample_count"], 2)
        self.assertEqual(parsed["age_field_cells"], 2)
        self.assertEqual(len(parsed["sample_catalog"]), 2)
        self.assertEqual(parsed["sample_catalog"][0]["public_age_labels"], ["age: 25"])
        self.assertFalse(parsed["donor_identity_verified"])

    def test_gzip(self):
        blob = gzip.compress(SYNTHETIC_MATRIX.encode(), mtime=0)
        self.assertEqual(decompress_bounded(blob), SYNTHETIC_MATRIX)

    def test_duplicate_GSM_refused(self):
        text = SYNTHETIC_MATRIX.replace('"GSM1234568"', '"GSM1234567"')
        with self.assertRaisesRegex(GEOProbeError, "duplicate GSM"):
            parse_series_matrix(text, "GSE307377")

    def test_wrong_sample_count_refused(self):
        text = SYNTHETIC_MATRIX.replace('!Sample_title\t"young"\t"old"',
                                        '!Sample_title\t"young"')
        with self.assertRaisesRegex(GEOProbeError, "cardinality"):
            parse_series_matrix(text, "GSE307377")

    def test_supplement_structure_only(self):
        x = inspect_supplement_header("Gene\tGSM1234567\tGSM1234568\nA\t1\t2\n")
        self.assertEqual(x["GSM_columns"], 2)
        self.assertEqual(x["column_labels"], ["Gene", "GSM1234567", "GSM1234568"])
        self.assertFalse(x["table_contents_analysed"])

    def test_no_network_without_explicit_opt_in(self):
        with self.assertRaisesRegex(GEOProbeError, "network disabled"):
            probe("GSE307377")

    def test_unknown_accession_refused(self):
        with self.assertRaises(GEOProbeError):
            probe("GSE100")
        with self.assertRaises(GEOProbeError):
            geo_matrix_url("GSE111/../../etc/passwd")

    def test_non_gzip_refused(self):
        with self.assertRaises(GEOProbeError):
            decompress_bounded(b"arbitrary")

if __name__ == "__main__":
    unittest.main()
