"""Pinned primary-source provenance gap audit for EXP-001 (technical only).

Do not mistake GEO samples, depositor cell-line identifiers, or sample library
labels for unique human donors. Reads public source metadata and returns only
aggregate field coverage. No sample rows, donor identifiers, or expression.
"""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
import io
import json
import re

from .cohort_probe import geo_soft_url, _metadata_rows
from .geo_probe import download_bounded, decompress_bounded, parse_series_matrix
from .replication_qc import metadata_rows, _characteristic_value, ReplicationQCError

SCHEMA = "phiage-exp001-provenance-gate/v1.0"
PLATFORM = re.compile(r"^GPL[0-9]+$")
GSM = re.compile(r"^GSM[0-9]+$")
SAMPLING_KEYS = {
    "passage", "passage number", "passage_number", "passage #",
    "culture passage", "cell passage"
}
SUBJECT_KEYS = {
    "donor id", "donor_id", "donor identifier", "individual id",
    "individual_id", "patient id", "patient_id", "participant id",
    "participant_id", "subject id", "subject_id"
}
PROTOCOL_FIELDS = {
    "growth": "!Sample_growth_protocol_ch1",
    "treatment": "!Sample_treatment_protocol_ch1",
    "extraction": "!Sample_extract_protocol_ch1",
    "source_name": "!Sample_source_name_ch1",
}
CHAR_FIELD = "!Sample_characteristics_ch1"

def require(value, message):
    if not value:
        raise ReplicationQCError(message)

def _nonempty(value):
    return bool(value.strip()) and value.strip().casefold() not in {"none","n/a","unknown","not provided"}

def _field_summary(records: list[dict]) -> dict:
    n=len(records)
    require(0 < n <= 500, "unexpected sample count")
    out={}
    for label in sorted(PROTOCOL_FIELDS):
        field=PROTOCOL_FIELDS[label]
        positive=sum(any(_nonempty(x) for x in record["fields"].get(field,[])) for record in records)
        variants=set()
        for record in records:
            for value in record["fields"].get(field,[]):
                if _nonempty(value):
                    variants.add(value.strip())
        out[label]={"samples_with_nonempty":positive,"samples_missing":n-positive,
                    "distinct_text_versions":len(variants),"text_validated":False}
    return out

def _char_map(fields: list[str]) -> dict[str,list[str]]:
    result={}
    for value in fields:
        if ":" not in value:
            continue
        name,v=value.split(":",1)
        key=name.strip().casefold()
        if key and _nonempty(v):
            result.setdefault(key,[]).append(v.strip())
    return result

def _identity_coverage(records: list[dict]) -> dict:
    n=len(records)
    subject_present=0
    cell_id_present=0
    passage_present=0
    ambiguous_subject=0
    unique_subject_ids=set()
    unique_cell_ids=set()
    subject_duplicate=0
    cell_duplicate=0
    char_keys=Counter()
    namespaced=Counter()
    for record in records:
        chars=_char_map(record["fields"].get(CHAR_FIELD,[]))
        for k in chars:
            char_keys[k]+=1
        source_subject=[v for key,vals in chars.items() if key in SUBJECT_KEYS for v in vals]
        source_cell=chars.get("cell id",[])
        if source_subject:
            subject_present+=1
            if len(set(s.casefold() for s in source_subject))!=1:
                ambiguous_subject+=1
            for s in set(s.casefold() for s in source_subject):
                if s in unique_subject_ids: subject_duplicate+=1
                else: unique_subject_ids.add(s)
        if source_cell:
            cell_id_present+=1
            if len(set(s.casefold() for s in source_cell))!=1:
                raise ReplicationQCError("contradictory cell ID values in source record")
            key=source_cell[0].casefold()
            if key in unique_cell_ids: cell_duplicate+=1
            else: unique_cell_ids.add(key)
            if re.fullmatch(r"GM[0-9]+", source_cell[0], re.I):
                namespaced["GM_format"]+=1
            elif re.fullmatch(r"HGADFN[0-9]+", source_cell[0], re.I):
                namespaced["HGADFN_format"]+=1
            else:
                namespaced["other_cell_id_format"]+=1
        if any(k in SAMPLING_KEYS for k in chars):
            passage_present+=1
    return {
        "observed_characteristic_field_presence":dict(sorted(char_keys.items())),
        "subject_identifier_field_present":subject_present,
        "subject_identifier_field_missing":n-subject_present,
        "subject_identifier_inconsistent_samples":ambiguous_subject,
        "subject_identifier_duplicate_label_excess":subject_duplicate,
        "cell_id_field_present":cell_id_present,
        "cell_id_field_missing":n-cell_id_present,
        "cell_id_duplicate_label_excess":cell_duplicate,
        "public_cell_id_syntax_count":dict(sorted(namespaced.items())),
        "sample_level_passage_field_present":passage_present,
        "sample_level_passage_field_missing":n-passage_present,
        "distinct_cell_id_labels":len(unique_cell_ids),
        "distinct_subject_labels":len(unique_subject_ids),
        "subject_identity_proven":False,
    }

def parse_soft_samples(text: str) -> list[dict]:
    require("^SERIES = GSE113957" in text, "wrong GSE113957 SOFT file")
    validated=metadata_rows(text)
    output=[]
    current=None
    for line in text.splitlines():
        if line.startswith("^SAMPLE = "):
            gsm=line[len("^SAMPLE = "):].strip()
            require(GSM.fullmatch(gsm) is not None, "bad SOFT GSM")
            current={"gsm_id":gsm,"fields":{}}
            output.append(current)
        elif line.startswith("^"):
            current=None
        elif current is not None and line.startswith("!Sample_") and " = " in line:
            key,value=line.split(" = ",1)
            if key in set(PROTOCOL_FIELDS.values()) | {CHAR_FIELD}:
                current["fields"].setdefault(key,[]).append(value.strip())
    require(len(validated)==len(output), "SOFT sample count changed")
    require([s["gsm_id"] for s in validated]==[s["gsm_id"] for s in output],
            "SOFT sample order or identity changed")
    return output

def parse_matrix_samples(text: str, mapping: dict) -> list[dict]:
    parsed=parse_series_matrix(text,"GSE307377")
    rows=_metadata_rows(text)
    n=parsed["sample_count"]
    require(n==9, "GSE307377 count changed")
    gsm=[s["gsm_id"] for s in parsed["sample_catalog"]]
    require(set(gsm)==set(s["gsm_id"] for s in mapping.get("samples",[])),
            "archived 9-sample crosswalk GSM mismatch")
    for key,cell_rows in rows.items():
        for cells in cell_rows:
            require(len(cells)==n, f"matrix metadata column count mismatch: {key}")
    return [{"gsm_id":gsm[i],
             "fields":{key:[row[i] for row in cell_rows] for key,cell_rows in rows.items()}}
            for i in range(n)]

def audit_provenance(soft: str, matrix: str, mapping: dict) -> dict:
    require(mapping.get("accession")=="GSE307377" and len(mapping.get("samples",[]))==9,
            "crosswalk metadata changed")
    cohort_a=parse_soft_samples(soft)
    cohort_b=parse_matrix_samples(matrix,mapping)
    audit_a=_identity_coverage(cohort_a)
    audit_b=_identity_coverage(cohort_b)
    a={"accession":"GSE113957","geo_sample_records":len(cohort_a),
       "identity":audit_a,"public_protocol_metadata":_field_summary(cohort_a),
       "independent_donors_verified":False}
    b={"accession":"GSE307377","geo_sample_records":len(cohort_b),
       "identity":audit_b,"public_protocol_metadata":_field_summary(cohort_b),
       "library_labels_archived":len(mapping["samples"]),
       "independent_donors_verified":False}
    blockers=[]
    for x in (a,b):
        if x["identity"]["subject_identifier_field_present"] < x["geo_sample_records"]:
            blockers.append(f'{x["accession"]}: explicit donor/subject identifier missing in some source samples')
        if x["identity"]["sample_level_passage_field_missing"]:
            blockers.append(f'{x["accession"]}: sample-level passage field absent in some samples')
        if x["identity"]["cell_id_field_missing"]:
            blockers.append(f'{x["accession"]}: cell-line identifier absent in some samples')
    blockers.append("Cross-cohort person/biobank linkage cannot be proven from deposited identifiers")
    blockers.append("Source protocol text is depositor metadata, not externally audited experimental conditions")
    blockers.append("Culture/batch balance, reuse permissions, and FPKM/TPM harmonization unresolved")
    return {
        "schema_version":SCHEMA,
        "source_cohorts":[a,b],
        "source_identity_coverage_checked":True,
        "clinical_donor_identity_confirmed":False,
        "cross_cohort_overlap_excluded":False,
        "cross_cohort_overlap_demonstrated":False,
        "comparability_of_identifier_namespaces_verified":False,
        "cross_cohort_common_subject_ids":None,
        "cross_cohort_same_person_linkage_evaluable":False,
        "donor_independence_verified":False,
        "biological_replication_verified":False,
        "analysis_ready":False,
        "age_effects_tested":False,
        "claim_level":"SOURCE_PROVENANCE_GAPS_ONLY",
        "gate_blockers":blockers,
        "warning":"Unique public cell IDs and nine deposited library labels cannot establish independent people or prove absence of repeated donors. Identifier values are not exported.",
    }

def run_provenance(source:dict,geo:dict,mapping:dict,*,allow_network=False):
    require(source.get("source")=="GSE113957" and source.get("analysis_ready") is False,
            "source receipt not pinned to GSE113957")
    require(geo.get("accession")=="GSE307377" and geo.get("analysis_ready") is False,
            "source receipt not pinned to GSE307377")
    matrix_info=geo["series_matrix"]
    require(matrix_info["source_url"]==
            "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE307nnn/GSE307377/matrix/GSE307377_series_matrix.txt.gz",
            "GSE307377 series matrix URL changed")
    require(source["source_soft_url"]==geo_soft_url("GSE113957"),
            "GSE113957 SOFT URL changed")
    require(re.fullmatch(r"[0-9a-f]{64}",source.get("source_soft_sha256","")) is not None,
            "missing source checksum")
    require(re.fullmatch(r"[0-9a-f]{64}",matrix_info.get("sha256","")) is not None,
            "missing matrix checksum")
    if not allow_network:
        raise ReplicationQCError("network disabled; pass --allow-network for pinned NCBI metadata")
    blobs=[]
    for url,sha in [(source["source_soft_url"],source["source_soft_sha256"]),
                    (matrix_info["source_url"],matrix_info["sha256"])]:
        blob=download_bounded(url)
        require(hashlib.sha256(blob).hexdigest()==sha,
                "downloaded official metadata differs from archived SHA-256")
        blobs.append(decompress_bounded(blob))
    report=audit_provenance(blobs[0],blobs[1],mapping)
    report["source_soft_sha256"]=source["source_soft_sha256"]
    report["source_matrix_sha256"]=matrix_info["sha256"]
    report["curated_crosswalk_sha256"]=hashlib.sha256(
        json.dumps(mapping,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return report
