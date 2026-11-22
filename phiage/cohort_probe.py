"""Fail-closed, read-only candidate cohort metadata census from NCBI GEO.

For GSE113957 only. This is a *source-discovery* census, not a human health
analysis or evidence of donor independence. Does not fetch protected data.
"""
from __future__ import annotations

from collections import Counter
import csv
import io
import hashlib
import json
import math
import re

from .geo_probe import (
    GEOProbeError, download_bounded, decompress_bounded, inspect_supplement_header,
    parse_series_matrix,
)

SCHEMA = "phiage-cohort-census/v0.6"
TARGET = "GSE113957"
AGE_FIELD = re.compile(r"^\s*age(?:\s*\(\s*years?\s*\))?\s*(?::|=)\s*(\d{1,3})(?:\s*(?:years?|yrs?))?\s*$", re.I)
AGE_KEY = re.compile(r"^\s*age(?:\s*\(\s*years?\s*\))?\s*$", re.I)
HGPS_EXPLICIT = re.compile(r"\b(?:hutchinson[- ]gilford|progeria|HGPS)\b", re.I)
HEALTHY_EXPLICIT = re.compile(r"\b(?:healthy|unaffected|normal control)\b", re.I)
DIAGNOSIS_KEY = re.compile(r"\b(?:diagnosis|disease|phenotype|condition|health status|donor status|patient status)\b", re.I)
MAX_META_LINES = 500

class CohortProbeError(ValueError):
    """Unreliable GEO cohort metadata or prohibited network access."""

def require(condition: bool, message: str) -> None:
    if not condition:
        raise CohortProbeError(message)

def _metadata_rows(text: str) -> dict[str, list[list[str]]]:
    require(isinstance(text, str) and bool(text), "GEO matrix content is empty")
    rows: dict[str, list[list[str]]] = {}
    seen = 0
    for line in text.splitlines():
        if line.startswith("!series_matrix_table_begin"):
            break
        if not line.startswith("!Sample_"):
            continue
        seen += 1
        require(seen <= MAX_META_LINES, "too many GEO sample-metadata rows")
        try:
            cells = next(csv.reader([line], delimiter="\t", strict=True))
        except csv.Error as exc:
            raise CohortProbeError("malformed sample-metadata TSV") from exc
        require(len(cells) >= 2, "GEO sample-metadata row has no samples")
        rows.setdefault(cells[0], []).append(cells[1:])
    return rows

def _characteristic(value: str) -> tuple[str, str] | None:
    if not isinstance(value, str) or ":" not in value:
        return None
    key, raw = value.split(":", 1)
    key = key.strip()
    return (key, raw.strip()) if key else None

def _sample_status(title: str, characteristics: list[str]) -> str:
    # Only explicit sample-level disease/healthy text, never GEO ID or title
    # patterns such as HGADFN. Contradictions and missing labels are unresolved.
    statements = []
    for char in characteristics:
        parsed = _characteristic(char)
        if parsed and DIAGNOSIS_KEY.search(parsed[0]):
            statements.append(parsed[1])
    statements.append(title)
    possible_hgps = any(HGPS_EXPLICIT.search(value) for value in statements)
    possible_healthy = any(HEALTHY_EXPLICIT.search(value) for value in statements)
    if possible_hgps and possible_healthy:
        return "conflicting"
    if possible_hgps:
        return "hgps_label_explicit"
    if possible_healthy:
        return "healthy_label_explicit"
    return "unknown"

def _sample_age(chars: list[str]) -> int | None:
    observed = set()
    for char in chars:
        if not isinstance(char, str):
            continue
        parsed = _characteristic(char)
        if not parsed or not AGE_KEY.fullmatch(parsed[0]):
            continue
        match = AGE_FIELD.fullmatch(char)
        if match is None:
            # Unparseable public age is missing, never converted to 0 or guessed.
            return None
        value = int(match.group(1))
        require(0 <= value <= 120, "out-of-range sample age")
        observed.add(value)
    require(len(observed) <= 1, "contradictory public age annotations for one sample")
    return next(iter(observed)) if observed else None

def summarize_matrix(text: str, *, accession: str = TARGET) -> dict:
    require(accession == TARGET, "only vetted candidate GSE113957 is supported")
    # Uses the existing parser's sample uniqueness and cardinality checks.
    catalog = parse_series_matrix(text, accession)
    rows = _metadata_rows(text)
    gsm = catalog["sample_catalog"]
    n = len(gsm)
    require(n >= 1 and n <= 500, "unreasonable sample count")
    require(len(gsm) == len({s["gsm_id"] for s in gsm}), "repeated GSM accession")
    for key, r in rows.items():
        for values in r:
            require(len(values) == n, f"sample-metadata cardinality mismatch: {key}")
    title_rows = rows.get("!Sample_title", [])
    require(len(title_rows) == 1, "expected one sample-title row")
    char_rows = rows.get("!Sample_characteristics_ch1", [])
    summary = Counter()
    age_values = []
    age_missing = 0
    keys = Counter()
    no_chars = 0
    age_bin_labels = Counter()
    for i in range(n):
        char = [row[i] for row in char_rows]
        if not char:
            no_chars += 1
        for field in char:
            parsed = _characteristic(field)
            if parsed:
                keys[parsed[0].strip().lower()] += 1
        status = _sample_status(title_rows[0][i], char)
        summary[status] += 1
        age = _sample_age(char)
        if age is None:
            age_missing += 1
        else:
            age_values.append(age)
            lo = 10 * (age // 10)
            age_bin_labels[f"{lo}-{lo+9}"] += 1
    return {
        "schema_version": SCHEMA,
        "accession": accession,
        "public_gsm_sample_count": n,
        "unique_gsm_sample_count": catalog["unique_GSM_count"],
        "study_claims_healthy_donors": 133,
        "study_claims_hgps_donors": 10,
        "claimed_split_verified_from_metadata": False,
        "observed_sample_label_counts": dict(sorted(summary.items())),
        "sample_characteristic_key_counts": dict(sorted(keys.items())),
        "samples_without_characteristics": no_chars,
        "parsed_sample_age_count": len(age_values),
        "unparsed_or_absent_age_count": age_missing,
        "parsed_age_min": min(age_values) if age_values else None,
        "parsed_age_max": max(age_values) if age_values else None,
        "parsed_age_decade_bins": dict(sorted(age_bin_labels.items())),
        "metadata_row_type_count": len(rows),
        "sample_metadata_field_names": sorted(rows),
        "donor_independence_verified": False,
        "healthy_hgps_grouping_verified": False,
        "processed_matrix_sample_crosswalk_verified": False,
        "normalization_harmonization_verified": False,
        "reuse_rights_reviewed": False,
        "analysis_ready": False,
        "claim_level": "COHORT_METADATA_DISCOVERY_ONLY",
        "caveat": (
            "GSM sample accessions are not necessarily unique donors. "
            "Study paper group counts are reported separately from source-observed labels; "
            "unknowns are not silently assigned to the healthy group. "
            "No expression values, aging association, intervention, or medical conclusion."
        ),
    }


def geo_soft_url(accession: str) -> str:
    require(accession == TARGET, "only verified GSE113957 SOFT family is allowed")
    return ("https://ftp.ncbi.nlm.nih.gov/geo/series/GSE113nnn/"
            "GSE113957/soft/GSE113957_family.soft.gz")

def geo_fpkm_url(accession: str) -> str:
    require(accession == TARGET, "only verified GSE113957 processed FPKM is allowed")
    return ("https://ftp.ncbi.nlm.nih.gov/geo/series/GSE113nnn/"
            "GSE113957/suppl/GSE113957_fpkm.txt.gz")

def summarize_soft(text: str, *, accession: str = TARGET) -> dict:
    """Read public SOFT family metadata, not sample expression tables.

    SOFT uses one ^SAMPLE block per GSM, unlike Series Matrix's column schema.
    For consistent auditing, its sample fields are transposed into an in-memory
    metadata-only Series Matrix and handed to the same strict census logic.
    """
    require(accession == TARGET, "unsupported SOFT source")
    require(isinstance(text, str) and bool(text), "SOFT file must contain text")
    require(f"^SERIES = {accession}" in text, "SOFT family has wrong accession")
    samples = []
    active = None
    for line in text.splitlines():
        if line.startswith("^SAMPLE = "):
            identifier = line[len("^SAMPLE = "):].strip()
            require(re.fullmatch(r"GSM[1-9][0-9]+", identifier) is not None,
                    "invalid GSM sample block identifier")
            require(len(samples) < 500, "too many SOFT sample blocks")
            active = {"gsm_id": identifier, "title": "", "characteristics": []}
            samples.append(active)
            continue
        if line.startswith("^"):
            active = None
            continue
        if active is None or not line.startswith("!Sample_") or " = " not in line:
            continue
        key, value = line.split(" = ", 1)
        value = value.strip()
        if key == "!Sample_geo_accession":
            require(value == active["gsm_id"], "SOFT sample block/accession mismatch")
        elif key == "!Sample_title":
            require(not active["title"], "duplicate SOFT sample title field")
            active["title"] = value
        elif key == "!Sample_characteristics_ch1":
            require(len(active["characteristics"]) < 80,
                    "too many characteristics for one sample")
            active["characteristics"].append(value)
    require(samples, "SOFT family did not contain any ^SAMPLE blocks")
    require(len(samples) == len({s["gsm_id"] for s in samples}), "duplicate SOFT GSM identifiers")
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter="\t", lineterminator="\n")
    writer.writerow(["!Sample_geo_accession"] + [s["gsm_id"] for s in samples])
    writer.writerow(["!Sample_title"] + [s["title"] for s in samples])
    n = max(len(s["characteristics"]) for s in samples)
    for index in range(n):
        writer.writerow(["!Sample_characteristics_ch1"] +
                        [s["characteristics"][index] if index < len(s["characteristics"])
                         else "" for s in samples])
    buf.write("!series_matrix_table_begin\n")
    report = summarize_matrix(buf.getvalue(), accession=accession)
    report["observed_source_format"] = "SOFT_family"
    report["sample_record_count"] = len(samples)
    report["expression_data_analysed"] = False
    return report

def probe_candidate(accession: str = TARGET, *, allow_network: bool = False,
                    with_fpkm: bool = False) -> dict:
    require(accession == TARGET, "accession not allowed for candidate census")
    if not allow_network:
        raise CohortProbeError("network disabled by default; pass --allow-network")
    url = geo_soft_url(accession)
    blob = download_bounded(url)
    summary = summarize_soft(decompress_bounded(blob), accession=accession)
    summary.update({
        "source_url": url,
        "source_gzip_sha256": hashlib.sha256(blob).hexdigest(),
        "source_gzip_bytes": len(blob),
    })
    if with_fpkm:
        fpkm_url = geo_fpkm_url(accession)
        processed = download_bounded(fpkm_url)
        structure = inspect_supplement_header(decompress_bounded(processed))
        summary["processed_fpkm_header"] = {
            "url": fpkm_url,
            "source_gzip_sha256": hashlib.sha256(processed).hexdigest(),
            "compressed_bytes": len(processed),
            "structure": structure,
            "sample_column_mapping_verified": False,
            "quantification_verified": False,
            "expression_values_analysed": False,
            "note": "Header only; inferred GSM mappings and FPKM values not validated.",
        }
    return summary
