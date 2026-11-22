"""Read-only bounded DOCX *structure* probe of the original public supplement.

Only reports table/heading presence and an archive checksum, never sample rows,
cell-line identifiers, patient data or unverified table-to-GSM joins.
"""
from __future__ import annotations
from io import BytesIO
import hashlib
import re
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree as ET

from .replication_qc import ReplicationQCError

SOURCE_URL = (
    "https://static-content.springer.com/esm/"
    "art%3A10.1186%2Fs13059-018-1599-6/MediaObjects/"
    "13059_2018_1599_MOESM1_ESM.docx"
)
MAX_DOWNLOAD_BYTES = 7_000_000
MAX_TOTAL_UNCOMPRESSED = 36_000_000
MAX_DOCUMENT_XML = 20_000_000
MAX_ZIP_MEMBERS = 400
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
TABLE_PATTERNS = {
    "table_s2_mentioned": re.compile(r"\bTable\s*S[\s-]*2\b", re.I),
    "table_s3_mentioned": re.compile(r"\bTable\s*S[\s-]*3\b", re.I),
}
SCHEMA="phiage-fleischer-supplement-structure/v1.1"

def require(condition, message):
    if not condition:
        raise ReplicationQCError(message)

def summarize_docx(blob: bytes) -> dict:
    require(isinstance(blob,bytes) and 0 < len(blob) <= MAX_DOWNLOAD_BYTES,
            "DOCX not present or exceeds source download bound")
    require(blob.startswith(b"PK\x03\x04"),"not an OOXML DOCX archive")
    try:
        with ZipFile(BytesIO(blob)) as archive:
            members=archive.infolist()
            require(len(members) <= MAX_ZIP_MEMBERS,"excessive OOXML file count")
            require(sum(x.file_size for x in members) <= MAX_TOTAL_UNCOMPRESSED,
                    "OOXML total uncompressed bytes exceeded")
            for x in members:
                require(not x.filename.startswith("/") and
                        ".." not in x.filename.split("/"),
                        "unsafe OOXML archive path")
                require(x.file_size <= MAX_DOCUMENT_XML,
                        "large OOXML member")
            require("word/document.xml" in archive.namelist(),"missing Word document")
            doc=archive.read("word/document.xml")
            require(len(doc)<=MAX_DOCUMENT_XML,"Word XML exceeds limit")
    except (BadZipFile,OSError,RuntimeError) as error:
        raise ReplicationQCError("unreadable DOCX source") from error
    require(b"<!DOCTYPE" not in doc and b"<!ENTITY" not in doc,
            "unexpected XML DTD/entity declaration")
    try:
        root=ET.fromstring(doc)
    except ET.ParseError as error:
        raise ReplicationQCError("malformed Word document XML") from error
    paragraphs=[]
    tables=[]
    # Keep text in memory only: output contains no participant-level passages.
    for element in root.iter():
        if element.tag == W+"p":
            text="".join(t.text or "" for t in element.iter(W+"t")).strip()
            if text:
                paragraphs.append(text)
        elif element.tag == W+"tbl":
            rows=list(element.findall(W+"tr"))
            tables.append(len(rows))
    text="\n".join(paragraphs)
    mentions={key:bool(regex.search(text)) for key,regex in TABLE_PATTERNS.items()}
    return {
        "schema_version":SCHEMA,
        "document_gzip":False,
        "compressed_source_bytes":len(blob),
        "source_docx_sha256":hashlib.sha256(blob).hexdigest(),
        "word_paragraph_count":len(paragraphs),
        "word_table_count":len(tables),
        "word_table_row_count_total":sum(tables),
        "supplement_caption_mention_flags":mentions,
        "original_paper_reports_s2_population_doubling":True,
        "original_paper_reports_s3_hgps_passage":True,
        "supplement_sample_level_values_released":False,
        "table_to_gsm_join_verified":False,
        "cohort_donor_uniqueness_verified":False,
        "culture_batch_equivalence_verified":False,
        "analysis_ready":False,
        "claim_level":"SUPPLEMENT_STRUCTURE_ONLY",
        "caveat":"Caption detection confirms text presence only, never sample lineage linkage, donor identity or individual passage records.",
    }

def probe_supplement(*,allow_network=False):
    if not allow_network:
        raise ReplicationQCError("network disabled by default; pass --allow-network")
    request=Request(SOURCE_URL,headers={
        "User-Agent":"PhiAge/1.1 (open nonclinical bibliographic source audit)",
        "Accept":"application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/octet-stream",
    })
    try:
        with urlopen(request, timeout=18) as response:
            require(response.status==200,"publisher supplement HTTP status is not 200")
            length=response.headers.get("Content-Length")
            if length:
                require(int(length)<=MAX_DOWNLOAD_BYTES,"publisher DOCX exceeds download bound")
            blob=response.read(MAX_DOWNLOAD_BYTES+1)
    except (OSError,ValueError) as error:
        raise ReplicationQCError("public publisher DOCX unavailable; not a source-code error") from error
    result=summarize_docx(blob)
    result["source_url"]=SOURCE_URL
    return result
