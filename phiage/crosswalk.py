"""Independent, fail-closed sample-to-column crosswalk validation for EXP-001.

Source: GEO sample Description "Library name". This verifies names of columns, NOT
independence of donors, scientific quality, data licensing, or biological effects.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "phiage-gsm-library-crosswalk/v0.4"
LIBRARY = re.compile(r"^TM[1-9][0-9]*_CKC[1-9][0-9]*_[YO]_CTRL$")
RAW_COLUMN = re.compile(r"^tags/(?P<library>TM[1-9][0-9]*_CKC[1-9][0-9]*_[YO]_CTRL)_(?P<suffix>S[0-9]+) \([0-9.]+ total\)$")
TPM_COLUMN = re.compile(r"^tags/(?P<library>TM[1-9][0-9]*_CKC[1-9][0-9]*_[YO]_CTRL)_(?P<suffix>S[0-9]+) TPM$")
TITLE = re.compile(r"^Human dermal fibroblast, (?P<group>young|old), age (?P<age>[0-9]+), (?P<sex>female|male)$")
SOURCE = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc="

class CrosswalkError(ValueError):
    """The recorded sample-to-column mapping is incomplete or inconsistent."""

def require(test, message):
    if not test:
        raise CrosswalkError(message)

def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)

def content_sha(obj):
    data = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def _indexed_columns(labels, pattern, description):
    require(isinstance(labels, list) and len(labels) == 17, f"{description}: expected 17 columns")
    observed = {}
    suffixes = {}
    for offset, header in enumerate(labels[8:], start=8):
        match = pattern.fullmatch(header)
        require(match is not None, f"{description}: unrecognized expression header at index {offset}")
        library = match["library"]
        require(library not in observed, f"{description}: duplicate library {library}")
        observed[library] = {"index": offset, "header": header}
        suffixes[library] = match["suffix"]
    require(len(observed) == 9, f"{description}: expected nine unique expression libraries")
    return observed, suffixes

def validate_crosswalk(mapping: dict, geo: dict, tpm: dict) -> dict:
    require(isinstance(mapping, dict) and mapping.get("schema_version") == SCHEMA,
            "crosswalk schema mismatch")
    require(mapping.get("accession") == "GSE307377", "unexpected crosswalk accession")
    samples = mapping.get("samples")
    require(isinstance(samples, list) and len(samples) == 9, "exactly nine crosswalk rows required")
    meta = geo.get("series_matrix", {}).get("metadata", {})
    require(meta.get("sample_count") == 9 and meta.get("unique_GSM_count") == 9,
            "archived GEO series matrix must identify nine unique sample accessions")
    catalog = meta.get("sample_catalog")
    require(isinstance(catalog, list) and len(catalog) == 9, "missing nine public GEO sample records")
    observed_gsms = {}
    for s in catalog:
        require(isinstance(s, dict) and isinstance(s.get("gsm_id"), str), "invalid sample catalog entry")
        require(s["gsm_id"] not in observed_gsms, "GEO contains duplicate GSM id")
        observed_gsms[s["gsm_id"]] = s
    raw_labels = geo.get("supplementary_table", {}).get("structure", {}).get("column_labels")
    tpm_labels = tpm.get("normalized_table", {}).get("structure", {}).get("column_labels")
    raw, raw_suffix = _indexed_columns(raw_labels, RAW_COLUMN, "raw")
    norm, norm_suffix = _indexed_columns(tpm_labels, TPM_COLUMN, "TPM")
    require(set(raw) == set(norm) and raw_suffix == norm_suffix,
            "raw and normalized files have differing library IDs or suffixes")
    expected = set(observed_gsms)
    checked = []
    seen_gsm, seen_library = set(), set()
    for s in samples:
        require(isinstance(s, dict), "invalid mapping row")
        gsm, library = s.get("gsm_id"), s.get("library_id")
        require(isinstance(gsm, str) and gsm in expected, "crosswalk GSM not in GEO sample catalog")
        require(gsm not in seen_gsm, f"duplicate crosswalk GSM: {gsm}")
        require(isinstance(library, str) and LIBRARY.fullmatch(library), f"invalid library id for {gsm}")
        require(library not in seen_library, f"duplicate crosswalk library: {library}")
        require(library in raw and library in norm, f"{gsm}: library absent from expression files")
        require(s.get("source_url") == SOURCE + gsm, f"{gsm}: missing exact primary GEO source")
        require(s.get("source_field") == "Description: Library name", f"{gsm}: provenance field missing")
        observed = observed_gsms[gsm]
        title = TITLE.fullmatch(observed.get("title") or "")
        require(title is not None, f"{gsm}: unsupported title age or sex syntax")
        require(type(s.get("age_years")) is int and int(title["age"]) == s["age_years"],
                f"{gsm}: age disagrees with GEO metadata")
        require(s.get("group") == title["group"] and s.get("sex") == title["sex"],
                f"{gsm}: age group/sex disagrees with GEO metadata")
        age_labels = observed.get("public_age_labels") or []
        require(f"age: {s['age_years']}" in age_labels, f"{gsm}: public age characteristic disagrees")
        require(library.split("_")[-2] == ("Y" if s["group"] == "young" else "O"),
                f"{gsm}: depositor library age group code mismatch")
        checked.append({
            "gsm_id": gsm, "library_id": library, "age_years": s["age_years"],
            "sex": s["sex"], "group": s["group"], "raw_index": raw[library]["index"],
            "tpm_index": norm[library]["index"], "raw_header": raw[library]["header"],
            "tpm_header": norm[library]["header"], "source_url": s["source_url"],
        })
        seen_gsm.add(gsm)
        seen_library.add(library)
    require(seen_gsm == expected and seen_library == set(raw),
            "mapping must cover all published GSM accessions and expression columns")
    counts = Counter(s["group"] for s in checked)
    require(counts == {"young": 4, "old": 5}, "unexpected age grouping in crosswalk")
    return {
        "schema_version": "phiage-crosswalk-validation/v0.4",
        "accession": "GSE307377", "mapping_sha256": content_sha(mapping),
        "geo_receipt_sha256": content_sha(geo), "tpm_receipt_sha256": content_sha(tpm),
        "sample_to_column_verified": True, "donor_independence_verified": False,
        "feature_identity_verified": False, "expression_quality_verified": False,
        "reuse_rights_reviewed": False, "analysis_ready": False,
        "group_counts": dict(counts), "mapped_samples": sorted(checked, key=lambda s: s["gsm_id"]),
        "limitations": [
            "Library name crosswalk uses primary GEO sample descriptions; manual publication review still advisable.",
            "GSM/library uniqueness is not proof of independent human donors or technical independence.",
            "First table column is Transcript/RepeatID; feature semantics need separate verification.",
            "No normalization audit, intervention, healthspan, or aging-reversal result.",
        ],
    }
