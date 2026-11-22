"""Conservative experimental-design feasibility audit, NOT an age predictor.

Only aggregates of public GEO sample metadata are emitted. No matrix loading,
statistical model training, p-values, or intervention claims. The external
SOFT file is pinned to the archived SHA-256 and network is disabled by default.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json

from .cohort_probe import _sample_age, _sample_status, geo_soft_url
from .geo_probe import decompress_bounded, download_bounded
from .replication_qc import metadata_rows, _characteristic_value, ReplicationQCError

SCHEMA = "phiage-exp001-design-preflight/v0.8"
PLAN_SCHEMA = "phiage-exp001-frozen-design/v0.8"

def require(condition, message):
    if not condition:
        raise ReplicationQCError(message)

def _strata_age_summary(samples):
    ages=[s["age"] for s in samples]
    decade_counts=Counter(10 * (int(s["age"]) // 10) for s in samples)
    return {
        "sample_count":len(samples),
        "age_min_years":min(ages) if ages else None,
        "age_max_years":max(ages) if ages else None,
        "ages_per_decade":{f"{key}-{key+9}":value for key,value in sorted(decade_counts.items())},
        "male_samples":sum(s["sex"]=="male" for s in samples),
        "female_samples":sum(s["sex"]=="female" for s in samples),
        "sex_missing_or_unrecognized_samples":sum(s["sex"] not in {"male","female"} for s in samples),
    }

def audit_metadata(soft_text: str, plan: dict) -> dict:
    require(plan.get("schema_version")==PLAN_SCHEMA,"frozen design schema mismatch")
    require(plan.get("target_accession")=="GSE113957","unsupported design target accession")
    population=plan.get("primary_population",{})
    require(population.get("explicit_source_label")=="healthy_label_explicit",
            "only source-reported Normal samples are permitted")
    require(type(population.get("minimum_age_years")) is int and
            population["minimum_age_years"]==20, "adult inclusion cutoff changed")
    require(plan.get("excluded_source_label")=="hgps_label_explicit",
            "HGPS exclusions must be explicit")
    primary=plan.get("primary_platform")
    secondary=plan.get("transport_platform")
    require(primary=="GPL18573" and secondary=="GPL16791",
            "platform design must match pinned GEO platform IDs")
    samples=metadata_rows(soft_text)
    total=len(samples)
    seen_cell_ids=set()
    collision_count=0
    missing_cell_ids=0
    normal=[]
    disease_count=Counter()
    age_missing=0
    missing_platform=0
    groups=defaultdict(list)
    for s in samples:
        chars=s["characteristics"]
        status=_sample_status(s["titles"][0],chars)
        disease_count[status]+=1
        age=_sample_age(chars)
        if age is None:
            age_missing+=1
        platform=s["platforms"][0] if s["platforms"] else None
        if platform is None:
            missing_platform+=1
        cell_id=_characteristic_value(chars,"cell id")
        if cell_id is None:
            missing_cell_ids+=1
        elif cell_id.strip().casefold() in seen_cell_ids:
            collision_count+=1
        else:
            seen_cell_ids.add(cell_id.strip().casefold())
        sex=(_characteristic_value(chars,"sex") or "").strip().casefold()
        if status==population["explicit_source_label"] and age is not None:
            record={"age":age,"sex":sex,"platform":platform}
            normal.append(record)
            if age>=20:
                groups[platform].append(record)
    adult=normal and [s for s in normal if s["age"]>=20] or []
    p=groups[primary]
    t=groups[secondary]
    primary_decades={int(s["age"])//10 for s in p}
    transport_decades={int(s["age"])//10 for s in t}
    common_decades=primary_decades & transport_decades
    overlap_lower=max((min(s["age"] for s in p) if p else float("inf")),
                      (min(s["age"] for s in t) if t else float("inf")))
    overlap_upper=min((max(s["age"] for s in p) if p else float("-inf")),
                      (max(s["age"] for s in t) if t else float("-inf")))
    has_range_overlap=bool(p and t and overlap_lower<=overlap_upper)
    overlapping_decade_samples_primary=sum(int(s["age"])//10 in common_decades for s in p)
    overlapping_decade_samples_secondary=sum(int(s["age"])//10 in common_decades for s in t)
    # All statuses are strictly depositor labels, not independent diagnoses.
    deficits=[]
    if total!=143 or disease_count["healthy_label_explicit"]!=133 or disease_count["hgps_label_explicit"]!=10:
        deficits.append("Public sample counts/status labels do not match frozen source metadata")
    if age_missing: deficits.append("One or more public sample ages missing/ambiguous")
    if collision_count or missing_cell_ids: deficits.append("Source cell-id label collisions or missing identifiers")
    if missing_platform: deficits.append("Some sample platform IDs are missing")
    if not p or not t: deficits.append("Platform-specific healthy-adult samples missing")
    if not has_range_overlap: deficits.append("Primary and transport platform adult age ranges do not overlap")
    if len(common_decades)<2:
        deficits.append("Fewer than two age decades are observed on both platforms")
    if overlapping_decade_samples_secondary<10:
        deficits.append("Fewer than ten secondary-platform adult profiles in shared age decades")
    result={
        "schema_version":SCHEMA,
        "source":"GSE113957",
        "source_observed_samples":total,
        "depositor_label_counts":dict(sorted(disease_count.items())),
        "unparseable_age_samples":age_missing,
        "source_cell_id_duplicate_label_excess":collision_count,
        "source_cell_id_missing":missing_cell_ids,
        "source_platform_missing":missing_platform,
        "primary_target":"descriptive platform-aware healthy adult design feasibility only",
        "target_population_source_label":"Normal (depositor-reported), not clinically verified",
        "adult_minimum_age_years":20,
        "excluded_hgps_samples":disease_count["hgps_label_explicit"],
        "healthy_all_ages":_strata_age_summary(normal),
        "eligible_adult_healthy":_strata_age_summary(adult),
        "primary_platform":primary,
        "transport_platform":secondary,
        "primary_platform_healthy_adult":_strata_age_summary(p),
        "transport_platform_healthy_adult":_strata_age_summary(t),
        "shared_age_decades":[f"{x*10}-{x*10+9}" for x in sorted(common_decades)],
        "shared_decade_primary_count":overlapping_decade_samples_primary,
        "shared_decade_transport_count":overlapping_decade_samples_secondary,
        "age_range_intersection_years":[overlap_lower,overlap_upper] if has_range_overlap else None,
        "exploratory_transport_metadata_gate_passed":not deficits,
        "transport_metadata_gate_blockers":deficits,
        "negative_controls_planned":plan.get("negative_controls",[]),
        "donor_independence_verified":False,
        "FPKM_TPM_harmonization_verified":False,
        "sample_preparation_and_batch_confounding_excluded":False,
        "training_or_hypothesis_test_performed":False,
        "replication_validated":False,
        "analysis_ready":False,
        "claim_level":"DESIGN_FEASIBILITY_ONLY",
        "warning":"No individual-level output; metadata age/platform overlap does not establish model transferability or causal aging biology.",
    }
    return result

def run_preflight(plan:dict,receipt:dict,overlap_receipt:dict,*,allow_network:bool=False) -> dict:
    require(plan.get("schema_version")==PLAN_SCHEMA,"frozen design schema mismatch")
    require(plan.get("source_soft_sha256")==receipt.get("source_soft_sha256"),
            "frozen plan/source checksum mismatch")
    require(plan.get("source_fpkm_sha256")==receipt.get("source_fpkm_sha256"),
            "frozen FPKM/source checksum mismatch")
    require(plan.get("source_tpm_sha256")==
            overlap_receipt.get("pinned_tpm_sha256"),"frozen TPM checksum mismatch")
    require(overlap_receipt.get("exact_refseq_identifier_overlap")==24560,
            "frozen exact transcript overlap receipt changed")
    require(overlap_receipt.get("expression_scale_harmonized") is False,
            "reference label match cannot imply expression-scale harmonization")
    require(receipt.get("donor_independence_verified") is False,
            "published GEO metadata is not independent donor verification")
    if not allow_network:
        raise ReplicationQCError("network disabled; pass --allow-network to inspect fixed official GEO metadata")
    url=geo_soft_url("GSE113957")
    require(url==receipt.get("source_soft_url"),"source URL different from pinned receipt")
    raw=download_bounded(url)
    sha=hashlib.sha256(raw).hexdigest()
    require(sha==plan["source_soft_sha256"],"SOFT file changed from pinned gzip SHA-256")
    out=audit_metadata(decompress_bounded(raw),plan)
    out["frozen_plan_sha256"]=hashlib.sha256(
        json.dumps(plan,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    out["source_soft_sha256"]=sha
    out["source_fpkm_sha256"]=receipt["source_fpkm_sha256"]
    out["source_tpm_sha256"]=plan["source_tpm_sha256"]
    out["exact_matching_refseq_label_count"]=24560
    return out
