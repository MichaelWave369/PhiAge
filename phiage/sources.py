"""Public-source registry gates for EXP-001. No dataset is fetched by this module."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import re
from urllib.parse import urlsplit

SCHEMA = "phiage-source-registry/v0.2"
ACCESS = {"metadata_only", "public_processed", "controlled_access"}
AGES = {"exact_public", "decade_bins", "age_groups", "reported_range", "unverified"}
REVIEW = {"candidate", "metadata_checked", "approved"}
ASSAYS = {"bulk_rna_seq", "single_cell_rna_seq", "rna_seq", "microarray"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")

class RegistryError(ValueError):
    """Source registry violates its provenance contract."""

def require(test: bool, message: str) -> None:
    if not test:
        raise RegistryError(message)

def nonempty(value) -> bool:
    return isinstance(value, str) and bool(value.strip())

def validate_registry(registry: dict) -> dict:
    require(isinstance(registry, dict), "registry must be an object")
    require(registry.get("schema_version") == SCHEMA, "unsupported source registry schema")
    records = registry.get("sources")
    require(isinstance(records, list) and records, "sources must be a nonempty list")
    identifiers = set()
    for record in records:
        require(isinstance(record, dict), "source entry must be an object")
        identifier = record.get("id")
        require(nonempty(identifier), "source id is missing")
        require(identifier not in identifiers, f"duplicate source ID: {identifier}")
        identifiers.add(identifier)
        for key in ("accession", "collection_id", "title"):
            require(nonempty(record.get(key)), f"{identifier}: missing {key}")
        url = record.get("source_url")
        require(nonempty(url), f"{identifier}: missing source_url")
        parsed = urlsplit(url)
        require(parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password,
                f"{identifier}: source_url must be HTTPS without embedded credentials")
        require(record.get("access_scope") in ACCESS, f"{identifier}: invalid access_scope")
        require(record.get("age_resolution") in AGES, f"{identifier}: invalid age_resolution")
        require(record.get("review_state") in REVIEW, f"{identifier}: invalid review_state")
        require(record.get("assay") in ASSAYS, f"{identifier}: invalid assay")
        require(record.get("license_status") in {"unreviewed", "reviewed"},
                f"{identifier}: invalid license_status")
        require(record.get("sample_overlap_status") in {"unknown", "documented_nonoverlap", "known_overlap"},
                f"{identifier}: invalid sample_overlap_status")
        require(type(record.get("metadata_complete")) is bool,
                f"{identifier}: metadata_complete must be boolean")
        count = record.get("sample_count")
        require(count is None or (type(count) is int and count > 0),
                f"{identifier}: sample_count must be positive integer or null")
        tissues = record.get("tissues")
        require(isinstance(tissues, list) and tissues and all(nonempty(t) for t in tissues),
                f"{identifier}: tissues must be a nonempty list")
        limits = record.get("limitations")
        require(isinstance(limits, list) and limits and all(nonempty(s) for s in limits),
                f"{identifier}: limitations must be a nonempty list")
        others = record.get("overlap_with")
        require(isinstance(others, list) and len(others) == len(set(others))
                and all(nonempty(s) and s != identifier for s in others),
                f"{identifier}: invalid overlap_with")
        sha = record.get("curated_file_sha256")
        require(sha is None or (isinstance(sha, str) and SHA256.fullmatch(sha)),
                f"{identifier}: curated_file_sha256 must be a lowercase SHA-256 or null")
    for record in records:
        require(all(other in identifiers for other in record["overlap_with"]),
                f"{record['id']}: overlap_with references unknown source")
    return registry

def canonical_sha256(registry: dict) -> str:
    validate_registry(registry)
    normalized = json.dumps(registry, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def review_blockers(source: dict) -> list[str]:
    blockers = []
    if source["review_state"] != "approved":
        blockers.append("review-not-approved")
    if source["license_status"] != "reviewed":
        blockers.append("license-unreviewed")
    if source["access_scope"] != "public_processed":
        blockers.append("processed-data-not-cleared")
    if source["age_resolution"] == "unverified":
        blockers.append("age-metadata-unverified")
    if source["sample_overlap_status"] != "documented_nonoverlap":
        blockers.append("independence-unverified")
    if not source["metadata_complete"]:
        blockers.append("sample-metadata-incomplete")
    if source["curated_file_sha256"] is None:
        blockers.append("input-checksum-missing")
    if source["overlap_with"]:
        blockers.append("known-or-possible-overlap")
    return blockers

def audit_registry(registry: dict) -> dict:
    validate_registry(registry)
    sources = registry["sources"]
    groups = defaultdict(list)
    for s in sources:
        groups[s["collection_id"]].append(s["id"])
    counts = Counter(s["review_state"] for s in sources)
    results = []
    for source in sorted(sources, key=lambda item: item["id"]):
        blockers = review_blockers(source)
        results.append({
            "id": source["id"], "accession": source["accession"],
            "source_url": source["source_url"], "collection_id": source["collection_id"],
            "assay": source["assay"], "tissues": source["tissues"],
            "review_state": source["review_state"], "eligible_for_analysis": not blockers,
            "blockers": blockers, "limitations": source["limitations"],
        })
    overlap_groups = [{"collection_id": k, "sources": sorted(ids)}
                      for k, ids in sorted(groups.items()) if len(ids) > 1]
    ready = [s for s in results if s["eligible_for_analysis"]]
    return {
        "engine": "phiage-source-audit/v0.2",
        "registry_sha256": canonical_sha256(registry),
        "source_count": len(sources),
        "review_counts": dict(sorted(counts.items())),
        "analysis_ready_count": len(ready),
        "distinct_declared_collections": len(groups),
        "overlapping_collection_groups": overlap_groups,
        "sources": results,
        "caveat": (
            "All readiness fields are curator assertions, not independently verified. "
            "Sources in the registry have NOT been downloaded or analyzed. "
            "Dataset entries never count as evidence of aging reversal, treatment or causation."
        ),
    }
