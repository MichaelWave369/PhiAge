import io
import struct
import unittest
from unittest.mock import patch
from zipfile import ZipFile
from phiage.supplement_probe import summarize_docx,probe_supplement
from phiage.replication_qc import ReplicationQCError

def small_docx(contents):
    paragraphs="".join(
        f'<w:p><w:r><w:t>{item}</w:t></w:r></w:p>' for item in contents
    )
    xml=(
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body>'+paragraphs+'<w:tbl><w:tr><w:tc/></w:tr></w:tbl></w:body></w:document>'
    )
    f=io.BytesIO()
    with ZipFile(f,'w') as z:
        z.writestr('word/document.xml',xml)
    return f.getvalue()

class SupplementProbeTests(unittest.TestCase):
    def test_caption_detection_never_licenses_join(self):
        d=summarize_docx(small_docx(["Supplementary Table S2 Population doubling","Table S3 HGPS passages"]))
        self.assertTrue(d["supplement_caption_mention_flags"]["table_s2_mentioned"])
        self.assertTrue(d["supplement_caption_mention_flags"]["table_s3_mentioned"])
        self.assertEqual(d["word_table_count"],1)
        self.assertEqual(d["word_table_row_count_total"],1)
        self.assertFalse(d["table_to_gsm_join_verified"])
        self.assertFalse(d["analysis_ready"])
        self.assertNotIn("passages",str(d))

    def test_missing_caption_is_not_fabricated(self):
        d=summarize_docx(small_docx(["Other supplementary text"]))
        self.assertFalse(d["supplement_caption_mention_flags"]["table_s2_mentioned"])
        self.assertFalse(d["supplement_caption_mention_flags"]["table_s3_mentioned"])

    def test_non_docx_rejected(self):
        with self.assertRaisesRegex(ReplicationQCError,"not an OOXML"):
            summarize_docx(b"hello")

    def test_default_off_no_network(self):
        with patch("phiage.supplement_probe.urlopen",side_effect=AssertionError("network call")):
            with self.assertRaisesRegex(ReplicationQCError,"network disabled"):
                probe_supplement()
