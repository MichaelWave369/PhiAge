"""Exact transcript-ID overlap census across two independent-source candidates.

This compares only deposited RefSeq accession text, never FPKM/TPM magnitudes.
Identical IDs are not proof of biological equivalence, batch control or replication.
"""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
import io
import re

from .geo_probe import download_bounded, decompress_bounded, geo_supplement_url
from .cohort_probe import geo_fpkm_url
from .replication_qc import ReplicationQCError, require

SCHEMA = "phiage-cross-cohort-transcript-identity/v0.7"
REFSEQ = re.compile(r"^(?:NM|NR|XM|XR)_[0-9]+(?:\.[0-9]+)?$")
VERSION = re.compile(r"^(.*)\.[0-9]+$")

def strip_version(label: str) -> str:
    match = VERSION.fullmatch(label)
    return match.group(1) if match else label

def scan_accessions(text: str, *, cohort: str) -> dict:
    require(cohort in {"GSE307377", "GSE113957"}, "unsupported cohort")
    reader = csv.reader(io.StringIO(text), delimiter="\t", strict=True)
    try:
        header = next(reader)
    except StopIteration as exc:
        raise ReplicationQCError("empty transcript file") from exc
    expected = "Transcript ID" if cohort == "GSE113957" else "Transcript/RepeatID"
    require(header[0].startswith(expected), "source transcript identifier heading changed")
    require(len(header) == (151 if cohort == "GSE113957" else 17),
            "unexpected cohort expression sample-column cardinality")
    ordered = []
    accessions = set()
    duplicate = 0
    bad = 0
    for i, cells in enumerate(reader):
        if not cells or not any(x.strip() for x in cells):
            continue
        require(i < 250000, "transcript census exceeded bounded row limit")
        require(len(cells) == len(header), "transcript census row differs from header")
        identifier = cells[0].strip()
        if not REFSEQ.fullmatch(identifier):
            bad += 1
        if identifier in accessions:
            duplicate += 1
        else:
            accessions.add(identifier)
        ordered.append(identifier)
    require(ordered, "transcript census empty")
    return {
        "cohort": cohort, "ordered_ids": ordered, "unique_ids": accessions,
        "duplicate_ids": duplicate, "invalid_refseq_syntax": bad,
    }

def compare_transcripts(fpkm: str, tpm: str) -> dict:
    first = scan_accessions(fpkm, cohort="GSE113957")
    second = scan_accessions(tpm, cohort="GSE307377")
    a, b = first["unique_ids"], second["unique_ids"]
    no_version_a = [strip_version(identifier) for identifier in a]
    no_version_b = [strip_version(identifier) for identifier in b]
    exact = a & b
    stripped = set(no_version_a) & set(no_version_b)
    return {
        "schema_version": SCHEMA,
        "input_cohorts": ["GSE113957", "GSE307377"],
        "GSE113957_unique_refseq_ids": len(a),
        "GSE307377_unique_refseq_ids": len(b),
        "exact_refseq_identifier_overlap": len(exact),
        "source_a_only_accessions": len(a - b),
        "source_b_only_accessions": len(b - a),
        "exact_identifier_set_equal": a == b,
        "identical_transcript_row_order": first["ordered_ids"] == second["ordered_ids"],
        "unversioned_identifier_overlap": len(stripped),
        "GSE113957_versionless_collisions": len(no_version_a) - len(set(no_version_a)),
        "GSE307377_versionless_collisions": len(no_version_b) - len(set(no_version_b)),
        "GSE113957_duplicate_source_accessions": first["duplicate_ids"],
        "GSE307377_duplicate_source_accessions": second["duplicate_ids"],
        "GSE113957_invalid_refseq_syntax": first["invalid_refseq_syntax"],
        "GSE307377_invalid_refseq_syntax": second["invalid_refseq_syntax"],
        "expression_scale_harmonized": False,
        "reference_annotation_equivalence_verified": False,
        "cross_cohort_biological_replication_verified": False,
        "analysis_ready": False,
        "claim_level": "TECHNICAL_TRANSCRIPT_ACCESSION_OVERLAP_ONLY",
        "caveat": (
            "Even identical RefSeq transcript ID strings do not prove compatible FPKM/TPM "
            "expression quantification, batch-independent effects, cell culture comparability, "
            "or causal/clinical aging associations. No age-effect test was run."
        ),
    }

def run_overlap(primary: dict, older: dict, *, allow_network: bool = False) -> dict:
    require(primary.get("source") == "GSE113957", "wrong primary cohort receipt")
    require(older.get("accession") == "GSE307377", "wrong secondary cohort receipt")
    if not allow_network:
        raise ReplicationQCError("network disabled; supply --allow-network")
    urls = [
        (geo_fpkm_url("GSE113957"), primary["source_fpkm_sha256"]),
        (geo_supplement_url("GSE307377", "tpm"), older["normalized_table"]["sha256"]),
    ]
    texts = []
    for url, expected_hash in urls:
        data = download_bounded(url)
        require(hashlib.sha256(data).hexdigest() == expected_hash,
                "source gzip differs from pinned SHA-256")
        texts.append(decompress_bounded(data))
    result = compare_transcripts(*texts)
    result["pinned_fpkm_sha256"] = urls[0][1]
    result["pinned_tpm_sha256"] = urls[1][1]
    return result
