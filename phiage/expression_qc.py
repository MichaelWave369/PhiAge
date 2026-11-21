
"""Read-only QC of two fixed GEO expression tables, after source-backed GSM mapping.

No differential expression, biomarker scoring, intervention modelling, donor
identity claim, or new data redistribution. Only aggregate numerical properties.
"""
from __future__ import annotations
from collections import Counter
import csv
import hashlib
import math

from .crosswalk import CrosswalkError, validate_crosswalk
from .geo_probe import download_bounded, decompress_bounded, geo_supplement_url

class ExpressionQCError(ValueError):
    """A downloaded table failed source integrity or structural/numeric QC."""

def inspect_table(text: str, expected_headers: list[str], *, kind: str) -> dict:
    """Scan all rows and return aggregate numerical/annotation QC only."""
    if kind not in {"raw", "tpm"}:
        raise ExpressionQCError("unsupported expression type")
    reader = csv.reader(text.splitlines(), delimiter="\t", strict=True)
    try:
        actual_header = next(reader)
    except StopIteration as exc:
        raise ExpressionQCError("expression table is empty") from exc
    if len(actual_header) != 17 or len(expected_headers) != 17:
        raise ExpressionQCError("expression header: expected exactly 17 table columns")
    # The archived inspector intentionally clipped long labels at 130 chars.
    # The one long command-containing annotation header can be compared by its
    # pinned prefix; all other headers, especially sample columns, must match.
    for index, (actual, archived) in enumerate(zip(actual_header, expected_headers)):
        if index == 0 and len(archived) == 130:
            match = actual.startswith(archived)
        else:
            match = actual == archived
        if not match:
            raise ExpressionQCError(f"expression header mismatch at column {index}")
    sample_columns = 9
    samples = [{"column": h, "nonzero_cells": 0, "zero_cells": 0, "total": 0.0,
                "min": None, "max": None} for h in actual_header[8:]]
    count = 0
    missing = invalid = negative = nonintegral = 0
    first_ids = set()
    feature_duplications = 0
    blank_features = 0
    chr_values = set()
    for row in reader:
        if not row or all(not c.strip() for c in row):
            continue
        count += 1
        if count > 250000:
            raise ExpressionQCError("too many features; input exceeds research safety bound")
        if len(row) != len(actual_header):
            raise ExpressionQCError(f"row {count}: expected 17 columns, got {len(row)}")
        feature = row[0].strip()
        if not feature:
            blank_features += 1
        elif feature in first_ids:
            feature_duplications += 1
        else:
            first_ids.add(feature)
        if len(chr_values) < 100:
            chr_values.add(row[1].strip())
        for i, value in enumerate(row[8:]):
            val = value.strip()
            if not val or val.upper() in {"NA", "N/A", "NULL"}:
                missing += 1
                continue
            try:
                number = float(val)
            except ValueError:
                invalid += 1
                continue
            if not math.isfinite(number):
                invalid += 1
                continue
            if number < 0:
                negative += 1
            if kind == "raw" and number >= 0 and not number.is_integer():
                nonintegral += 1
            stat = samples[i]
            stat["total"] += number
            stat["min"] = number if stat["min"] is None else min(stat["min"], number)
            stat["max"] = number if stat["max"] is None else max(stat["max"], number)
            if number == 0:
                stat["zero_cells"] += 1
            else:
                stat["nonzero_cells"] += 1
    if count == 0:
        raise ExpressionQCError("expression file has no data rows")
    for stat in samples:
        stat["total"] = round(stat["total"], 4)
    integrity = missing == invalid == negative == 0 and blank_features == 0
    return {
        "table_type": kind,
        "feature_rows": count,
        "sample_columns": sample_columns,
        "missing_numeric_cells": missing, "non_numeric_or_nonfinite_cells": invalid,
        "negative_cells": negative, "non_integer_raw_cells": nonintegral,
        "blank_feature_ids": blank_features, "duplicate_feature_ids": feature_duplications,
        "unique_feature_ids": len(first_ids), "observed_chr_label_count_capped": len(chr_values),
        "structural_numeric_qc_pass": integrity,
        "ordinary_integer_count_model_ready": (integrity and kind == "raw" and nonintegral == 0
                                                and feature_duplications == 0),
        "sample_aggregate_descriptives": samples,
        "feature_semantics_verified": False,
        "warning": "These aggregate counts are technical data QC, not gene-level interpretation or evidence of biological age change.",
    }

def run_qc(crosswalk: dict, geo_receipt: dict, tpm_receipt: dict, *,
           allow_network: bool = False) -> dict:
    report = validate_crosswalk(crosswalk, geo_receipt, tpm_receipt)
    if not allow_network:
        raise ExpressionQCError("network disabled: pass --allow-network for pinned public GEO files")
    result = {"schema_version": "phiage-expression-qc/v0.4", "accession": "GSE307377",
              "crosswalk_mapping_sha256": report["mapping_sha256"],
              "sample_to_column_verified": True,
              "donor_independence_verified": False, "clinical_interpretation": False,
              "feature_identity_verified": False, "analysis_ready": False, "tables": {}}
    for kind, receipt, key in (
        ("raw", geo_receipt, "supplementary_table"),
        ("tpm", tpm_receipt, "normalized_table")
    ):
        record = receipt[key]
        url = geo_supplement_url("GSE307377", kind)
        if url != record["source_url"]:
            raise ExpressionQCError(f"{kind}: source URL does not match archived receipt")
        blob = download_bounded(url)
        sha = hashlib.sha256(blob).hexdigest()
        if sha != record["sha256"]:
            raise ExpressionQCError(f"{kind}: downloaded bytes differ from archived SHA-256; stop")
        summary = inspect_table(decompress_bounded(blob),
                                record["structure"]["column_labels"], kind=kind)
        summary["compressed_sha256"] = sha
        result["tables"][kind] = summary
    result["warnings"] = [
        "The GEO library-to-GSM mapping is verified; it does not prove donor independence.",
        "Transcript/RepeatID features are not presumed to represent uniquely identified genes.",
        "TPM/count comparisons here are QC only; no statistical aging associations were estimated.",
        "No public source has passed the EXP-001 permission and cohort independence review.",
    ]
    return result
