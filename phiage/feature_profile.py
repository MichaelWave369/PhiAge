"""Exploratory, non-inferential QC of pinned public NCBI GEO fibroblast expression.

Reports syntactic feature-ID classes and log1p(TPM) sample-to-sample similarity.
No clinical, causal, age-related differential expression, or biomarker inference.
"""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
import math
import re

from .crosswalk import validate_crosswalk
from .expression_qc import ExpressionQCError, inspect_table
from .geo_probe import decompress_bounded, download_bounded, geo_supplement_url

MAX_ROWS = 250000
PATTERNS = [
    ("RefSeq_transcript_accession_syntax", re.compile(r"^(?:NM|NR|XM|XR)_[0-9]+(?:\.[0-9]+)?$")),
    ("Ensembl_transcript_accession_syntax", re.compile(r"^ENST[0-9]+(?:\.[0-9]+)?$")),
    ("Ensembl_gene_accession_syntax", re.compile(r"^ENSG[0-9]+(?:\.[0-9]+)?$")),
]

def classify_feature_id(value: str) -> str:
    for name, pattern in PATTERNS:
        if pattern.fullmatch(value):
            return name
    return "other_unclassified_syntax"

def _correlation(n: int, sx: float, sy: float, sxx: float, syy: float, sxy: float):
    if n < 3:
        return None
    vx = sxx - sx * sx / n
    vy = syy - sy * sy / n
    if vx <= 1e-10 or vy <= 1e-10:
        return None
    value = (sxy - sx * sy / n) / math.sqrt(vx * vy)
    if not math.isfinite(value):
        return None
    return round(max(-1.0, min(1.0, value)), 6)

def inspect_profile(text: str, expected_headers: list[str], crosswalk_audit: dict) -> dict:
    basic = inspect_table(text, expected_headers, kind="tpm")
    if not basic["structural_numeric_qc_pass"] or basic["duplicate_feature_ids"]:
        raise ExpressionQCError("TPM profile requires missing-free, nonnegative, unique-feature data")
    expected = {s["tpm_index"]: s for s in crosswalk_audit["mapped_samples"]}
    if set(expected) != set(range(8, 17)):
        raise ExpressionQCError("crosswalk indices do not cover exactly nine TPM columns")
    reader = csv.reader(text.splitlines(), delimiter="\t", strict=True)
    next(reader, None)
    n = 0
    patterns = Counter()
    annotations = Counter()
    sample_totals = [0.0] * 9
    sample_sq = [0.0] * 9
    sample_nonzero = [0] * 9
    cross = [[0.0] * 9 for _ in range(9)]
    all_zero = 0
    for row in reader:
        if not row or all(not c.strip() for c in row):
            continue
        n += 1
        if n > MAX_ROWS:
            raise ExpressionQCError("feature count exceeds safety bound")
        patterns[classify_feature_id(row[0].strip())] += 1
        # Metadata is unverified, and these are merely literal label tokens.
        tail = row[7].rsplit("|", 1)[-1].strip() if row[7].strip() else "(blank)"
        annotations[tail[:50]] += 1
        values = [float(value) for value in row[8:]]
        transformed = [math.log1p(value) for value in values]
        if all(value == 0 for value in values):
            all_zero += 1
        for i in range(9):
            sample_totals[i] += transformed[i]
            sample_sq[i] += transformed[i] ** 2
            sample_nonzero[i] += values[i] > 0
            for j in range(i + 1):
                cross[i][j] += transformed[i] * transformed[j]
    if n != basic["feature_rows"]:
        raise ExpressionQCError("profile row-count inconsistent with numeric QC")
    summary = []
    for i in range(9):
        subject = expected[i + 8]
        summary.append({
            "gsm_id": subject["gsm_id"],
            "library_id": subject["library_id"],
            "age_years": subject["age_years"],
            "group": subject["group"],
            "sex": subject["sex"],
            "nonzero_features": sample_nonzero[i],
            "zero_fraction": round(1 - sample_nonzero[i] / n, 6),
            "mean_log1p_tpm": round(sample_totals[i] / n, 6),
        })
    pairs = []
    for i in range(9):
        for j in range(i):
            pairs.append({
                "gsm_a": summary[j]["gsm_id"],
                "gsm_b": summary[i]["gsm_id"],
                "correlation": _correlation(
                    n, sample_totals[j], sample_totals[i],
                    sample_sq[j], sample_sq[i], cross[i][j]),
                "metric": "Pearson correlation of log1p(TPM) across all 27,142 deposited features",
            })
    defined = [p["correlation"] for p in pairs if p["correlation"] is not None]
    return {
        "schema_version": "phiage-feature-profile/v0.5",
        "accession": "GSE307377",
        "feature_rows": n,
        "all_sample_zero_rows": all_zero,
        "feature_id_syntax_counts": dict(sorted(patterns.items())),
        "annotation_tail_literal_counts_top_12": [
            {"label": key, "count": count} for key, count in
            sorted(annotations.items(), key=lambda x: (-x[1], x[0]))[:12]
        ],
        "per_sample_descriptives": summary,
        "sample_similarity_pairs": pairs,
        "similarity_min": min(defined) if defined else None,
        "similarity_median": sorted(defined)[len(defined)//2] if defined else None,
        "similarity_max": max(defined) if defined else None,
        "sample_column_crosswalk_verified": True,
        "feature_semantics_verified": False,
        "donor_independence_verified": False,
        "reproducibility_across_cohorts_verified": False,
        "analysis_ready": False,
        "claim_level": "TECHNICAL_QC_ONLY",
        "warning": (
            "Syntax patterns and annotation-tail strings are NOT independently curated gene identity. "
            "Sample correlations use one small, overlapping age-group cohort and establish no aging effect. "
            "No biological age score, differential expression, or clinical benefit inferred."
        ),
    }

def run_profile(mapping: dict, geo_receipt: dict, tpm_receipt: dict, *,
                allow_network: bool = False) -> dict:
    crosswalk = validate_crosswalk(mapping, geo_receipt, tpm_receipt)
    if not allow_network:
        raise ExpressionQCError("network disabled; explicit --allow-network required")
    pinned = tpm_receipt["normalized_table"]
    url = geo_supplement_url("GSE307377", "tpm")
    if url != pinned["source_url"]:
        raise ExpressionQCError("source URL differs from pinned receipt")
    blob = download_bounded(url)
    sha = hashlib.sha256(blob).hexdigest()
    if sha != pinned["sha256"]:
        raise ExpressionQCError("TPM gzip checksum differs from archived official-data receipt")
    profile = inspect_profile(decompress_bounded(blob),
                              pinned["structure"]["column_labels"], crosswalk)
    profile["tpm_gzip_sha256"] = sha
    profile["crosswalk_sha256"] = crosswalk["mapping_sha256"]
    return profile
