"""Conservative cohort common-support audit based on public GEO metadata.

No expression values, fitting, age-prediction, health inference or clinical
claims. This reports AGGREGATES ONLY, never individual donor identifiers.
"""
from __future__ import annotations
from collections import Counter, defaultdict
import hashlib
import json
import statistics

from .cohort_probe import _sample_age, _sample_status, geo_soft_url
from .geo_probe import download_bounded, decompress_bounded
from .replication_qc import ReplicationQCError, metadata_rows, _characteristic_value

SCHEMA = "phiage-exp001-common-support/v0.9"
PLAN_SCHEMA = "phiage-exp001-common-support-plan/v0.9"

def require(condition, message):
    if not condition:
        raise ReplicationQCError(message)

def _validate_plan(plan):
    require(isinstance(plan, dict) and plan.get("schema_version")==PLAN_SCHEMA,
            "unexpected common-support plan version")
    require(plan.get("accession")=="GSE113957", "unexpected public cohort accession")
    require(plan.get("source_label")=="healthy_label_explicit", "source Normal label required")
    require(plan.get("exclude_label")=="hgps_label_explicit", "HGPS exclusion required")
    require(plan.get("lower_age_years")==30 and plan.get("upper_age_exclusive")==50,
            "frozen 30–49 age window must not be changed")
    require(plan.get("primary_platform")=="GPL18573" and
            plan.get("comparison_platform")=="GPL16791", "frozen platforms changed")
    require(plan.get("age_decade_bins") == [30,40], "frozen age decade bins changed")
    require(type(plan.get("minimum_per_platform_sex_decade")) is int and
            plan["minimum_per_platform_sex_decade"]==2, "frozen stratum minimum changed")
    require(type(plan.get("minimum_cross_platform_pair_capacity")) is int and
            plan["minimum_cross_platform_pair_capacity"]==8, "frozen pair capacity minimum changed")
    require(plan.get("allow_age_model_fitting") is False, "age-model fitting must remain disabled")

def _summarize(records):
    ages=[r["age"] for r in records]
    return {
        "n":len(records),
        "male":sum(r["sex"]=="male" for r in records),
        "female":sum(r["sex"]=="female" for r in records),
        "unknown_sex":sum(r["sex"] not in {"male","female"} for r in records),
        "minimum_age_years":min(ages) if ages else None,
        "maximum_age_years":max(ages) if ages else None,
        "mean_age_years":round(statistics.mean(ages), 4) if ages else None,
    }

def audit_common_support(soft_text,plan):
    """Public metadata only; no person-level rows in returned JSON."""
    _validate_plan(plan)
    samples=metadata_rows(soft_text)
    selection=defaultdict(list)
    statuses=Counter()
    cell_labels=set()
    duplicate_ids=0
    missing_ids=0
    missing_ages=0
    unknown_platform=0
    unknown_sex=0
    eligible_other_platform=0
    primary=plan["primary_platform"]
    secondary=plan["comparison_platform"]
    for s in samples:
        chars=s["characteristics"]
        status=_sample_status(s["titles"][0],chars)
        statuses[status]+=1
        age=_sample_age(chars)
        if age is None: missing_ages+=1
        cell=_characteristic_value(chars,"cell id")
        if not cell or not cell.strip(): missing_ids+=1
        elif cell.strip().casefold() in cell_labels: duplicate_ids+=1
        else: cell_labels.add(cell.strip().casefold())
        if status!=plan["source_label"] or age is None or not (30<=age<50):
            continue
        platform=s["platforms"][0] if s["platforms"] else "(missing)"
        if platform not in (primary,secondary):
            eligible_other_platform+=1
            unknown_platform+=1
            continue
        sex=(_characteristic_value(chars,"sex") or "").strip().casefold()
        if sex not in ("male","female"): unknown_sex+=1
        selection[platform].append({"age":age,"sex":sex})
    strata=[]
    missing_strata=[]
    thin_strata=[]
    pair_capacity=0
    matched_by_platform={primary:0,secondary:0}
    for decade in plan["age_decade_bins"]:
        for sex in ("female","male"):
            count_a=sum(10*(int(s["age"])//10)==decade and s["sex"]==sex for s in selection[primary])
            count_b=sum(10*(int(s["age"])//10)==decade and s["sex"]==sex for s in selection[secondary])
            possible=min(count_a,count_b)
            pair_capacity+=possible
            matched_by_platform[primary]+=possible
            matched_by_platform[secondary]+=possible
            stratum={"decade":f"{decade}-{decade+9}","sex":sex,
                     "primary_n":count_a,"comparison_n":count_b,
                     "maximum_balanced_pairs":possible,
                     "at_least_two_each":min(count_a,count_b)>=2}
            strata.append(stratum)
            if possible==0: missing_strata.append(f"{decade}-{decade+9}/{sex}")
            elif possible<2: thin_strata.append(f"{decade}-{decade+9}/{sex}")
    a=selection[primary]
    b=selection[secondary]
    blockers=[]
    if len(samples)!=143 or statuses["healthy_label_explicit"]!=133 or statuses["hgps_label_explicit"]!=10:
        blockers.append("Pinned GEO sample count or source status distribution changed")
    if duplicate_ids or missing_ids:
        blockers.append("Source cell-id label duplicates or missing values")
    if missing_ages or unknown_platform or eligible_other_platform or unknown_sex:
        blockers.append("Unresolved source ages, sex, or platform assignments")
    if not a or not b:
        blockers.append("One sequencing platform has no eligible 30-49 Normal-labeled samples")
    if missing_strata:
        blockers.append("Age-decade × sex strata absent on at least one platform")
    if thin_strata:
        blockers.append("Age-decade × sex strata with fewer than two samples on a platform")
    if pair_capacity<plan["minimum_cross_platform_pair_capacity"]:
        blockers.append("Fewer than eight possible age-decade/sex-stratified balanced pairs")
    # The row counts describe capacity only: no subject matching or split exists.
    return {
        "schema_version":SCHEMA,"accession":"GSE113957",
        "source_sample_count":len(samples),
        "source_label_counts":dict(sorted(statuses.items())),
        "status":"descriptive metadata feasibility only",
        "age_window_years":{"min_inclusive":30,"max_exclusive":50},
        "disease_excluded_from_age_study":"hgps_label_explicit",
        "primary_platform":primary,"comparison_platform":secondary,
        "primary_metadata":_summarize(a),"comparison_metadata":_summarize(b),
        "sex_by_age_decade_strata":strata,
        "missing_strata":missing_strata,"thin_strata":thin_strata,
        "maximum_balanced_pair_capacity":pair_capacity,
        "maximum_balanced_samples_total":2*pair_capacity,
        "excluded_source_status_hgps":statuses["hgps_label_explicit"],
        "unknown_sex_in_window":unknown_sex,
        "missing_or_unparsed_ages_all_source":missing_ages,
        "unrecognized_platform_in_window":unknown_platform,
        "source_cell_id_missing":missing_ids,
        "source_cell_id_duplicate_label_excess":duplicate_ids,
        "metadata_balance_thresholds_passed":not blockers,
        "metadata_blockers":blockers,
        "frozen_plan_minimum_per_stratum":2,
        "frozen_plan_minimum_balanced_pairs":8,
        "donor_independence_verified":False,
        "batch_or_platform_effects_controlled":False,
        "sample_matching_performed":False,
        "FPKM_TPM_harmonized":False,
        "clinical_label_validity_verified":False,
        "replication_performed":False,
        "age_effect_tested":False,
        "analysis_ready":False,
        "claim_level":"COMMON_SUPPORT_METADATA_AUDIT_ONLY",
        "limitation":(
            "Counts of age-decade/sex label combinations reflect only deposited public "
            "metadata, not biological donor verification, causal identification, expression "
            "normalization or statistical power. No person-level sample list is exported."
        ),
    }

def run_common_support(plan,source,overlap,*,allow_network=False):
    _validate_plan(plan)
    require(source.get("source")=="GSE113957" and source.get("analysis_ready") is False,
            "unexpected archived source receipt")
    require(source.get("source_soft_sha256")==plan.get("pinned_soft_sha256"),
            "source SOFT hash differs from frozen plan")
    require(source.get("source_fpkm_sha256")==plan.get("pinned_fpkm_sha256"),
            "source FPKM hash differs from frozen plan")
    require(overlap.get("pinned_tpm_sha256")==plan.get("pinned_tpm_sha256"),
            "TPM checksum differs from frozen plan")
    require(overlap.get("exact_refseq_identifier_overlap")==24560 and
            overlap.get("expression_scale_harmonized") is False,
            "transcript identity receipt must remain non-harmonized and pinned")
    if not allow_network:
        raise ReplicationQCError("network disabled: pass --allow-network for public NCBI metadata")
    url=geo_soft_url("GSE113957")
    require(url==source.get("source_soft_url"),"source URL mismatch")
    payload=download_bounded(url)
    digest=hashlib.sha256(payload).hexdigest()
    require(digest==plan["pinned_soft_sha256"],"official source bytes changed from pinned checksum")
    out=audit_common_support(decompress_bounded(payload),plan)
    out["source_soft_sha256"]=digest
    out["frozen_plan_sha256"]=hashlib.sha256(
        json.dumps(plan,sort_keys=True,separators=(",",":")).encode("utf-8")).hexdigest()
    out["exact_cross_cohort_refseq_labels"]=24560
    return out
