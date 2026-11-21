"""Bounded, read-only GEO Series Matrix metadata probe.

No data downloaded until CLI receives explicit --allow-network.
GEO's meta-record can describe samples, but never certifies independent donors
or analysis eligibility. This module does NOT run expression statistics.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import re
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

ACCESSION = re.compile(r"^GSE[1-9][0-9]{0,8}$")
MAX_COMPRESSED = 12 * 1024 * 1024
MAX_UNCOMPRESSED = 80 * 1024 * 1024
GEO_HOST = "ftp.ncbi.nlm.nih.gov"
FIXED_SUPPLEMENT = {
    "GSE307377": {
        "raw": "GSE307377_raw.txt.gz",
        "tpm": "GSE307377_tpm.txt.gz",
    },
}
ACCEPTED = frozenset({"GSE307377", "GSE226189", "GSE275846", "GSE262619"})

class GEOProbeError(ValueError):
    """A GEO metadata integrity or network safety gate failed."""

def geo_matrix_url(accession: str) -> str:
    if not isinstance(accession, str) or not ACCESSION.fullmatch(accession):
        raise GEOProbeError("invalid GSE accession: use uppercase GSE and digits")
    family = accession[:-3] + "nnn"
    return f"https://{GEO_HOST}/geo/series/{family}/{accession}/matrix/{accession}_series_matrix.txt.gz"

def geo_supplement_url(accession: str, kind: str = "raw") -> str:
    if accession not in FIXED_SUPPLEMENT or kind not in FIXED_SUPPLEMENT[accession]:
        raise GEOProbeError("no vetted supplementary filename configured for accession/kind")
    family = accession[:-3] + "nnn"
    name = FIXED_SUPPLEMENT[accession][kind]
    return f"https://{GEO_HOST}/geo/series/{family}/{accession}/suppl/{name}"

class GEOOnlyRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        u = urlsplit(newurl)
        if u.scheme != "https" or u.hostname != GEO_HOST or u.port not in (None, 443):
            raise GEOProbeError("redirect outside approved NCBI GEO host refused")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def download_bounded(url: str, *, max_bytes: int = MAX_COMPRESSED) -> bytes:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != GEO_HOST or parts.username or parts.password or parts.port not in (None, 443):
        raise GEOProbeError("only pinned NCBI GEO HTTPS host is permitted")
    if not parts.path.startswith("/geo/series/") or parts.query or parts.fragment:
        raise GEOProbeError("unexpected GEO URL structure")
    opener = build_opener(GEOOnlyRedirect())
    req = Request(url, headers={"User-Agent": "PhiAge-research-prototype/0.3 (public GEO metadata read-only)"})
    with opener.open(req, timeout=35) as response:
        declared = response.headers.get("Content-Length")
        if declared and int(declared) > max_bytes:
            raise GEOProbeError("compressed GEO file exceeds download limit")
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise GEOProbeError("compressed GEO response exceeds limit")
    if not data.startswith(b"\x1f\x8b"):
        raise GEOProbeError("GEO response is not gzip; potentially an error document")
    return data

def decompress_bounded(blob: bytes) -> str:
    if not isinstance(blob, bytes) or len(blob) > MAX_COMPRESSED:
        raise GEOProbeError("invalid or oversized gzip payload")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(blob)) as gz:
            raw = gz.read(MAX_UNCOMPRESSED + 1)
    except (OSError, EOFError) as exc:
        raise GEOProbeError("invalid compressed GEO content") from exc
    if len(raw) > MAX_UNCOMPRESSED:
        raise GEOProbeError("decompressed GEO content exceeds limit")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise GEOProbeError("GEO content is not valid UTF-8") from exc

def parse_series_matrix(text: str, accession: str) -> dict:
    """Parse sample-level header rows without inferring donors from cell lines."""
    if not isinstance(text, str):
        raise GEOProbeError("series matrix must be text")
    fields = {}
    for line in text.splitlines():
        if line.startswith("!series_matrix_table_begin"):
            break
        if not line.startswith("!Sample_"):
            continue
        try:
            columns = next(csv.reader([line], delimiter="\t"))
        except csv.Error as exc:
            raise GEOProbeError("invalid GEO metadata row") from exc
        if len(columns) < 2:
            continue
        key = columns[0]
        fields.setdefault(key, []).append(columns[1:])
    accessions = fields.get("!Sample_geo_accession", [])
    if len(accessions) != 1:
        raise GEOProbeError("expected one GEO sample accession row")
    ids = accessions[0]
    if not ids or not all(re.fullmatch(r"GSM[1-9][0-9]+", s or "") for s in ids):
        raise GEOProbeError("missing/invalid GEO sample IDs")
    if len(ids) != len(set(ids)):
        raise GEOProbeError("duplicate GSM IDs")
    sample_count = len(ids)
    for key, rows in fields.items():
        if any(len(row) != sample_count for row in rows):
            raise GEOProbeError(f"metadata cardinality mismatch: {key}")
    age_fields = 0
    for row in fields.get("!Sample_characteristics_ch1", []):
        age_fields += sum(bool(re.search(r"(?:^|[\s;])age[\s_:]", value, re.I)) for value in row)
    titles = fields.get("!Sample_title", [])
    source_names = fields.get("!Sample_source_name_ch1", [])
    characteristic_rows = fields.get("!Sample_characteristics_ch1", [])
    files = fields.get("!Sample_supplementary_file_1", [])
    catalog = []
    for i, identifier in enumerate(ids):
        age_labels = [row[i][:120] for row in characteristic_rows
                      if re.search(r"(?:^|[\s;])age[\s_:]", row[i], re.I)]
        catalog.append({
            "gsm_id": identifier,
            "title": titles[0][i][:120] if titles else None,
            "source_name": source_names[0][i][:120] if source_names else None,
            "public_age_labels": age_labels,
            "supplementary_basename": files[0][i].rsplit("/", 1)[-1][:120] if files else None,
        })
    return {
        "accession": accession,
        "sample_catalog": catalog,
        "sample_count": sample_count,
        "unique_GSM_count": len(set(ids)),
        "metadata_row_types": sorted(fields),
        "age_field_cells": age_fields,
        "donor_identity_verified": False,
        "age_annotation_validated": False,
        "note": "A GSM is a deposited sample, not necessarily one independent human donor.",
    }

def inspect_supplement_header(text: str) -> dict:
    nonempty = [line for line in text.splitlines() if line.strip()][:2]
    if not nonempty:
        raise GEOProbeError("empty supplementary table")
    first = nonempty[0]
    delimiter = "\t" if "\t" in first else ","
    columns = next(csv.reader([first], delimiter=delimiter))
    if len(columns) < 2:
        raise GEOProbeError("supplementary table has fewer than 2 columns")
    return {
        "delimiter": "tab" if delimiter == "\t" else "comma",
        "column_count": len(columns),
        "first_column_label": columns[0][:100],
        "GSM_columns": sum(bool(re.fullmatch(r"GSM[1-9][0-9]+", s)) for s in columns),
        "column_labels": [s[:130] for s in columns],
        "table_contents_analysed": False,
        "note": "Structural inspection only; expression values not analyzed and no donor mapping implied.",
    }

def probe(accession: str, *, allow_network: bool = False, with_counts: bool = False,
          with_tpm: bool = False) -> dict:
    if accession not in ACCEPTED:
        raise GEOProbeError("accession not in read-only EXP-001 allowlist")
    if not allow_network:
        raise GEOProbeError("network disabled by default; supply --allow-network to fetch public GEO files")
    matrix_url = geo_matrix_url(accession)
    matrix_blob = download_bounded(matrix_url)
    matrix = parse_series_matrix(decompress_bounded(matrix_blob), accession)
    artifact = {
        "source_url": matrix_url,
        "sha256": hashlib.sha256(matrix_blob).hexdigest(),
        "compressed_bytes": len(matrix_blob),
        "metadata": matrix,
    }
    result = {
        "schema_version": "phiage-geo-probe/v0.3",
        "accession": accession,
        "series_matrix": artifact,
        "analysis_ready": False,
        "dataset_license_reviewed": False,
        "donor_overlap_checked": False,
        "research_claim": "NONE: structural metadata verification only",
    }
    if with_counts:
        supplemental_url = geo_supplement_url(accession)
        blob = download_bounded(supplemental_url)
        result["supplementary_table"] = {
            "sample_column_crosswalk_verified": False,
            "mapping_instruction": "Compare sample_catalog titles and supplementary basenames with column_labels; do not infer a donor mapping merely from column position.",
            "source_url": supplemental_url,
            "sha256": hashlib.sha256(blob).hexdigest(),
            "compressed_bytes": len(blob),
            "structure": inspect_supplement_header(decompress_bounded(blob)),
        }
    if with_tpm:
        tpm_url = geo_supplement_url(accession, "tpm")
        tpm_blob = download_bounded(tpm_url)
        result["normalized_table"] = {
            "source_url": tpm_url,
            "sha256": hashlib.sha256(tpm_blob).hexdigest(),
            "compressed_bytes": len(tpm_blob),
            "sample_column_crosswalk_verified": False,
            "normalization_type_reported": "TPM",
            "normalization_validated": False,
            "structure": inspect_supplement_header(decompress_bounded(tpm_blob)),
            "note": "TPM as named by depositor. No independent normalization verification, donor mapping, or age-effect analysis.",
        }
    return result
