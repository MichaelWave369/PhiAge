"""Fail-closed offline review of EXP-001 public provenance evidence.

Separates primary-source observations, paper-level claims, uninspected
supplements and materials-only repository policy. No subject-level records.
"""
from __future__ import annotations
from collections import Counter
from urllib.parse import urlparse

from .replication_qc import ReplicationQCError

SCHEMA = "phiage-exp001-provenance-review-ledger/v1.1"
CLAIM_LEVEL = "RESEARCH_PROVENANCE_REVIEW_ONLY"
ALLOWED_TYPES = {
    "primary_data_registry", "original_peer_reviewed_publication",
    "original_supplement", "institutional_cohort_protocol",
    "biomaterial_use_policy",
}
ALLOWED_CLASSES = {
    "source_observed", "publication_reported", "policy_context_only",
    "linked_uninspected",
}
ALLOWED_LEVELS = {
    "sample-metadata", "study-level", "potential-sample-supplement",
    "material-distribution-policy",
}
REQUIRED_GATES = frozenset({
    "person_level_donor_linkage","cross_study_overlap_exclusion",
    "culture_history_crosswalk","second_cohort_culture_review",
    "public_expression_reuse_scope","batch_and_platform_comparability",
    "feature_and_scale_harmonization","statistical_analysis_authorization",
})
ALLOWED_HOSTS = frozenset({
    "www.ncbi.nlm.nih.gov","link.springer.com","static-content.springer.com",
    "pmc.ncbi.nlm.nih.gov","bmjopen.bmj.com","www.coriell.org",
})

def require(value, message):
    if not value:
        raise ReplicationQCError(message)

def audit_review(ledger: dict, observation: dict) -> dict:
    require(isinstance(ledger,dict) and ledger.get("schema_version")==SCHEMA,
            "unrecognized provenance ledger")
    require(ledger.get("cohort_accessions")==["GSE113957","GSE307377"],
            "unexpected study scope")
    require(observation.get("receipt_type")=="phiage-source-observed-provenance-coverage/v1.0"
            and observation.get("claim_level")=="SOURCE_PROVENANCE_GAPS_ONLY",
            "v1.0 source-backed receipt absent or invalid")
    require(observation.get("analysis_ready") is False and
            observation.get("cross_cohort_same_person_linkage_evaluable") is False,
            "source-backed receipt improperly asserts human donor linkage")
    observed={s.get("accession"):s for s in observation.get("source_cohorts",[])}
    require(set(observed)==set(ledger["cohort_accessions"]),
            "receipt cohort accession mismatch")
    frozen=ledger.get("source_snapshots",{})
    require(set(frozen)==set(observed), "source snapshot registry changed")
    for accession,record in frozen.items():
        sample=observed[accession]
        ident=sample.get("identity",{})
        require(sample["geo_sample_records"]==record["samples"],
                f"{accession}: source sample counts drifted")
        require(ident["subject_identifier_field_present"]==record["donor_id_fields"]==0,
                f"{accession}: person ID field counts drifted")
        require(ident["sample_level_passage_field_present"]==record["sample_level_passage_fields"]==0,
                f"{accession}: GEO passage field coverage changed")
        if accession=="GSE113957":
            require(ident["cell_id_field_present"]==record["cell_id_fields"]==143,
                    "Coriell-style cell ID field coverage changed")
            require(observation["source_soft_sha256"]==record["source_gzip_sha256"],
                    "GSE113957 official source hash changed")
        else:
            require(ident["cell_line_description_field_present"]==record["cell_line_description_fields"]==9,
                    "GSE307377 descriptive cell-line field coverage changed")
            require(observation["source_matrix_sha256"]==record["source_gzip_sha256"],
                    "GSE307377 official source hash changed")
    sources=ledger.get("sources",[])
    require(isinstance(sources,list) and len(sources)>=6, "inadequate provenance citations")
    ids=[s.get("id") for s in sources]
    require(len(set(ids))==len(ids) and all(isinstance(x,str) and x for x in ids),
            "missing or duplicate source ID")
    for source in sources:
        require(source.get("type") in ALLOWED_TYPES,"unsupported source type")
        p=urlparse(source.get("url",""))
        require(p.scheme=="https" and p.netloc in ALLOWED_HOSTS and
                p.username is None and p.password is None,
                "source URL must be approved original host")
        require(source.get("review_state") in {
            "source_snapshot_verified","publication_text_reviewed","linked_not_parsed",
            "context_only"
        },"unapproved source review state")
        require(bool(source.get("locator")) and bool(source.get("scope")),
                "source missing scope/locator")
    claims=ledger.get("claims",[])
    claim_ids=[x.get("id") for x in claims]
    require(len(claim_ids)==len(set(claim_ids)) and all(claim_ids),
            "duplicate or empty claims")
    require(len(claims)>=6,"insufficient source-scoped claims")
    for item in claims:
        require(item.get("evidence_class") in ALLOWED_CLASSES,
                "unsupported evidence class")
        require(item.get("level") in ALLOWED_LEVELS,"unrecognized evidence granularity")
        linked=item.get("source_ids")
        require(isinstance(linked,list) and len(linked)>=1 and
                all(source_id in ids for source_id in linked),
                "claim references an absent source")
        require(bool(item.get("statement")) and bool(item.get("limitation")),
                "every claim requires statement and limitation")
        if item["evidence_class"]=="linked_uninspected":
            require(item["level"]=="potential-sample-supplement",
                    "uninspected source cannot be promoted to sample-level evidence")
    gates=ledger.get("review_gates",[])
    gate_ids=[x.get("id") for x in gates]
    require(set(gate_ids)==REQUIRED_GATES and len(gate_ids)==len(REQUIRED_GATES),
            "required scientific safety gates missing or changed")
    for gate in gates:
        require(gate.get("status")=="blocked","unreviewed human study gate must stay blocked")
        require(bool(gate.get("required")) and bool(gate.get("review_question")),
                "gate missing written review requirements")
        linked=gate.get("supporting_claim_ids",[])
        require(linked and all(cid in claim_ids for cid in linked),
                "gate cites unknown research claim")
    flags=ledger.get("policies",{})
    require(flags.get("no_network_by_default") is True and
            flags.get("emit_person_level_identifiers") is False and
            flags.get("permit_cross_study_person_reidentification") is False and
            flags.get("permit_donor_claims") is False and
            flags.get("permit_model_fitting") is False and
            flags.get("permit_age_effect_inference") is False and
            flags.get("analysis_ready") is False and
            flags.get("supplement_sample_level_verified") is False and
            flags.get("global_claim_level")==CLAIM_LEVEL,
            "unsafe or overclaimed evidence review policy")
    # Public audit output contains only designed aggregate summaries.
    by_class=dict(sorted(Counter(c["evidence_class"] for c in claims).items()))
    return {
        "schema_version":"phiage-exp001-reviewed-provenance-summary/v1.1",
        "review_id":ledger["review_id"],
        "cohorts":ledger["cohort_accessions"],
        "cohort_sample_counts":{k:observed[k]["geo_sample_records"] for k in ledger["cohort_accessions"]},
        "explicit_subject_id_field_count":sum(s["identity"]["subject_identifier_field_present"] for s in observed.values()),
        "geo_sample_level_passage_field_count":sum(s["identity"]["sample_level_passage_field_present"] for s in observed.values()),
        "cited_original_source_count":len(sources),
        "scoped_evidence_statement_count":len(claims),
        "evidence_class_counts":by_class,
        "required_review_gate_count":len(gates),
        "blocked_review_gate_count":len(gates),
        "blocked_gates":[{"id":g["id"],"reason":g["required"],"next_review_question":g["review_question"]}
                         for g in gates],
        "linked_supplement_sample_level_join_verified":False,
        "external_human_subject_reidentification_performed":False,
        "cross_cohort_person_identity_verified":False,
        "culture_history_source_granularity":"published study-level mean and linked unparsed supplement; no GEO sample field",
        "Coriell_policy_scope":"biomaterial distribution only; public GEO expression-data reuse must be reviewed separately",
        "donor_independence_verified":False,
        "cross_cohort_overlap_excluded":False,
        "expression_harmonized":False,
        "age_effects_tested":False,
        "analysis_ready":False,
        "claim_level":CLAIM_LEVEL,
        "note":"Citations establish provenance leads, not an approved human donor linkage or experimental result.",
    }
