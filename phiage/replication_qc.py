"""Bounded, read-only GSE113957 replication-readiness audit.

Uses official NCBI GEO public SOFT/FPKM artifacts pinned by archived SHA-256.
Only aggregate quality and metadata are emitted. No age effect, model fit,
treatment, clinical utility or independent biological replication is inferred.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import csv
import hashlib
import io
import math
import re

from .cohort_probe import (
    CohortProbeError, geo_fpkm_url, geo_soft_url, _sample_age, _sample_status,
)
from .geo_probe import download_bounded, decompress_bounded

SCHEMA = "phiage-replication-readiness/v0.7"
MAX_ROWS = 250000
EXPECTED_ANNOTATION = [
    "Transcript ID", "chr", "start", "end", "strand", "Length",
    "Copies", "Annotation/Divergence",
]
REFSEQ = re.compile(r"^(?:NM|NR|XM|XR)_[0-9]+(?:\.[0-9]+)?$")
GSM = re.compile(r"^GSM[1-9][0-9]+$")
PLATFORM = re.compile(r"^GPL[1-9][0-9]+$")
HASH = re.compile(r"^[0-9a-f]{64}$")

class ReplicationQCError(ValueError):
    """Source evidence or downloaded FPKM content violates QC contract."""

def require(test, message):
    if not test:
        raise ReplicationQCError(message)

def metadata_rows(soft_text: str) -> list[dict]:
    """Parse per-sample, per-field SOFT records without guessing donor identity."""
    rows = []
    current = None
    require("^SERIES = GSE113957" in soft_text, "wrong GEO series SOFT")
    for line in soft_text.splitlines():
        if line.startswith("^SAMPLE = "):
            ident = line[len("^SAMPLE = "):].strip()
            require(GSM.fullmatch(ident) is not None, "invalid GSM block")
            require(len(rows) < 500, "excessive SOFT GSM blocks")
            current = {"gsm_id": ident, "titles": [], "platforms": [],
                       "characteristics": [], "record_accessions": []}
            rows.append(current)
        elif line.startswith("^"):
            current = None
        elif current is not None and line.startswith("!Sample_") and " = " in line:
            key, value = line.split(" = ", 1)
            value = value.strip()
            if key == "!Sample_title":
                current["titles"].append(value)
            elif key == "!Sample_platform_id":
                current["platforms"].append(value)
            elif key == "!Sample_characteristics_ch1":
                require(len(current["characteristics"]) < 100, "too many sample characteristics")
                current["characteristics"].append(value)
            elif key == "!Sample_geo_accession":
                current["record_accessions"].append(value)
    require(rows, "SOFT file has no sample blocks")
    require(len({r["gsm_id"] for r in rows}) == len(rows), "duplicate GSM identifier")
    for sample in rows:
        require(len(sample["titles"]) == 1 and bool(sample["titles"][0]),
                "missing or duplicated sample title")
        require(len(sample["platforms"]) <= 1, "duplicate sample platform")
        if sample["platforms"]:
            require(PLATFORM.fullmatch(sample["platforms"][0]) is not None, "invalid platform ID")
        require(not sample["record_accessions"] or sample["record_accessions"] == [sample["gsm_id"]],
                "GSM block/accession mismatch")
    require(len({r["titles"][0] for r in rows}) == len(rows), "duplicate sample title")
    return rows

def _characteristic_value(characteristics: list[str], label: str):
    matched = []
    for field in characteristics:
        if ":" not in field:
            continue
        key, value = field.split(":", 1)
        if key.strip().casefold() == label:
            if value.strip():
                matched.append(value.strip())
    require(len(set(matched)) <= 1, f"conflicting {label} metadata")
    return matched[0] if matched else None

def summarize_source(soft_text: str) -> dict:
    samples = metadata_rows(soft_text)
    n = len(samples)
    cell_ids = Counter()
    cell_missing = 0
    status = Counter()
    platforms = Counter()
    platform_status = defaultdict(Counter)
    sex_status = defaultdict(Counter)
    age_per_status = defaultdict(list)
    platforms_missing = 0
    malformed_ages = 0
    for sample in samples:
        chars = sample["characteristics"]
        group = _sample_status(sample["titles"][0], chars)
        status[group] += 1
        age = _sample_age(chars)
        if age is None:
            malformed_ages += 1
        else:
            age_per_status[group].append(age)
        cell = _characteristic_value(chars, "cell id")
        if cell is None:
            cell_missing += 1
        else:
            cell_ids[cell.casefold()] += 1
        sex = (_characteristic_value(chars, "sex") or "unreported").casefold()
        sex_status[group][sex] += 1
        platform = sample["platforms"][0] if sample["platforms"] else "(missing)"
        platforms[platform] += 1
        platform_status[platform][group] += 1
        if platform == "(missing)":
            platforms_missing += 1
    duplicates = sum(v - 1 for v in cell_ids.values() if v > 1)
    ambiguous = (cell_missing > 0 or duplicates > 0 or platforms_missing > 0 or
                 malformed_ages > 0 or any(k in status for k in ("conflicting", "unknown")))
    return {
        "accession": "GSE113957",
        "observed_gsm_count": n,
        "unique_sample_title_count": n,
        "public_source_label_counts": dict(sorted(status.items())),
        "cell_id_label": {
            "reported_nonempty": sum(cell_ids.values()),
            "unique_labels": len(cell_ids),
            "duplicate_label_excess": duplicates,
            "missing": cell_missing,
            "donor_identity_proven": False,
        },
        "platform_count": len([k for k in platforms if k != "(missing)"]),
        "platform_group_counts": {k: dict(sorted(platform_status[k].items())) for k in sorted(platforms)},
        "group_sex_counts": {k: dict(sorted(v.items())) for k, v in sorted(sex_status.items())},
        "group_age_ranges_years": {
            key: {"count": len(vals), "min": min(vals), "max": max(vals)}
            for key, vals in sorted(age_per_status.items()) if vals
        },
        "unparsed_age_count": malformed_ages,
        "metadata_has_unresolved_issues": ambiguous,
        "donor_independence_verified": False,
        "batch_effects_excluded": False,
    }

def inspect_fpkm(fpkm_text: str, expected_titles: list[str]) -> dict:
    """Scan complete data table but release aggregate QC only."""
    reader = csv.reader(io.StringIO(fpkm_text), delimiter="\t", strict=True)
    try:
        header = next(reader)
    except StopIteration as exc:
        raise ReplicationQCError("empty FPKM file") from exc
    require(len(header) == len(expected_titles) + 8, "FPKM header column count mismatch")
    require(header[:8] == EXPECTED_ANNOTATION, "unexpected FPKM annotation fields")
    titles = header[8:]
    require(len(titles) == len(set(titles)), "repeated FPKM sample column")
    require(len(expected_titles) == len(set(expected_titles)) and set(titles) == set(expected_titles),
            "SOFT titles do not map one-to-one to FPKM columns")
    count = 0
    unique_features = set()
    duplicates = 0
    empty_ids = 0
    invalid = 0
    missing = 0
    negative = 0
    all_zero = 0
    refseq_syntax = 0
    sample_nonzero = [0] * len(titles)
    for cells in reader:
        if not cells or not any(part.strip() for part in cells):
            continue
        count += 1
        require(count <= MAX_ROWS, "FPKM feature count exceeds bounded scan limit")
        require(len(cells) == len(header),
                f"FPKM row {count}: length {len(cells)} mismatches header")
        name = cells[0].strip()
        if not name:
            empty_ids += 1
        elif name in unique_features:
            duplicates += 1
        else:
            unique_features.add(name)
        refseq_syntax += bool(REFSEQ.fullmatch(name))
        expressed = False
        for i, raw in enumerate(cells[8:]):
            value = raw.strip()
            if not value or value.upper() in {"NA", "N/A", "NULL"}:
                missing += 1
                continue
            try:
                number = float(value)
            except ValueError:
                invalid += 1
                continue
            if not math.isfinite(number):
                invalid += 1
                continue
            if number < 0:
                negative += 1
                continue
            if number > 0:
                expressed = True
                sample_nonzero[i] += 1
        if not expressed:
            all_zero += 1
    require(count > 0, "FPKM file contained no expression rows")
    clean = not (missing or invalid or negative or duplicates or empty_ids)
    return {
        "feature_rows": count,
        "expression_sample_columns": len(titles),
        "unique_feature_ids": len(unique_features),
        "refseq_transcript_accession_syntax_count": refseq_syntax,
        "duplicate_feature_ids": duplicates,
        "blank_feature_ids": empty_ids,
        "missing_numeric_cells": missing,
        "invalid_or_nonfinite_numeric_cells": invalid,
        "negative_numeric_cells": negative,
        "all_sample_zero_feature_rows": all_zero,
        "expressed_feature_rows": count - all_zero,
        "sample_nonzero_feature_min": min(sample_nonzero),
        "sample_nonzero_feature_max": max(sample_nonzero),
        "numeric_structure_pass": clean,
        "feature_semantics_curated": False,
        "normalization_validated": False,
        "note": "FPKM numeric/feature QC only. No association with age was tested.",
    }

def run_replication_qc(receipt: dict, *, allow_network: bool = False) -> dict:
    require(receipt.get("source") == "GSE113957", "receipt belongs to different series")
    require(receipt.get("analysis_ready") is False, "receipt wrongly asserts readiness")
    for key in ("source_soft_sha256", "source_fpkm_sha256"):
        require(HASH.fullmatch(receipt.get(key, "")) is not None,
                f"malformed pinned {key}")
    if not allow_network:
        raise ReplicationQCError("network disabled; pass --allow-network for public GEO files")
    blobs = []
    for key, url in (
        ("source_soft_sha256", geo_soft_url("GSE113957")),
        ("source_fpkm_sha256", geo_fpkm_url("GSE113957")),
    ):
        require(receipt["source_soft_url" if key.endswith("soft_sha256") else "source_fpkm_url"] == url,
                "pinned URL mismatch")
        blob = download_bounded(url)
        digest = hashlib.sha256(blob).hexdigest()
        require(digest == receipt[key], f"downloaded {key} differs from pinned file bytes")
        blobs.append(blob)
    soft = decompress_bounded(blobs[0])
    expression = decompress_bounded(blobs[1])
    records = metadata_rows(soft)
    names = [s["titles"][0] for s in records]
    metadata = summarize_source(soft)
    matrix = inspect_fpkm(expression, names)
    return {
        "schema_version": SCHEMA,
        "accession": "GSE113957",
        "input_soft_sha256": receipt["source_soft_sha256"],
        "input_fpkm_sha256": receipt["source_fpkm_sha256"],
        "source_provenance_checked": True,
        "source_title_column_crosswalk_verified": True,
        "sample_metadata_qc": metadata,
        "expression_qc": matrix,
        "donor_independence_verified": False,
        "batch_effects_excluded": False,
        "cross_cohort_feature_harmonization_verified": False,
        "license_and_reuse_reviewed": False,
        "age_association_tested": False,
        "independent_replication_verified": False,
        "analysis_ready": False,
        "claim_level": "TECHNICAL_REPLICATION_READINESS_QC_ONLY",
        "warnings": [
            "Source cell id uniqueness is not independent donor verification.",
            "FPKM magnitude is not comparable to TPM or raw counts without a predeclared harmonization protocol.",
            "Sample labels are depositor reports, not clinical diagnoses.",
            "No age prediction, clinical effect or aging reversal has been tested."
        ],
    }
