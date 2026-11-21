"""Strict, deterministic evidence checks; not a causal inference engine."""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path

VERSION = "phiage-evidence/v0.1"
DESIGNS = {"observational", "intervention", "mechanistic", "review", "simulation"}
DIRECTIONS = {"supports", "contradicts", "mixed", "inconclusive"}
SPECIES = {"human", "mouse", "rat", "nonhuman_primate", "other", "in_vitro", "not_applicable"}
EMPIRICAL = {"observational", "intervention", "mechanistic"}
HALLMARKS = {
    "genomic-instability", "telomere-attrition", "epigenetic-alterations",
    "loss-of-proteostasis", "disabled-macroautophagy", "deregulated-nutrient-sensing",
    "mitochondrial-dysfunction", "cellular-senescence", "stem-cell-exhaustion",
    "altered-intercellular-communication", "chronic-inflammation", "dysbiosis",
}

class EvidenceError(ValueError):
    """Invalid provenance or study record."""

def _need(cond: bool, message: str) -> None:
    if not cond:
        raise EvidenceError(message)

def validate(bundle: dict) -> dict:
    _need(isinstance(bundle, dict), "bundle must be an object")
    _need(bundle.get("schema_version") == VERSION, "unsupported schema_version")
    hypotheses = bundle.get("hypotheses")
    evidence = bundle.get("evidence")
    _need(isinstance(hypotheses, list) and hypotheses, "hypotheses must be non-empty list")
    _need(isinstance(evidence, list), "evidence must be a list")
    ids = set()
    for h in hypotheses:
        _need(isinstance(h, dict), "hypothesis must be an object")
        identifier = h.get("id")
        _need(isinstance(identifier, str) and identifier.strip(), "hypothesis id required")
        _need(identifier not in ids, f"duplicate hypothesis id: {identifier}")
        ids.add(identifier)
        _need(h.get("hallmark") in HALLMARKS, f"unknown hallmark for {identifier}")
        _need(isinstance(h.get("claim"), str) and h["claim"].strip(), "claim required")
        _need(isinstance(h.get("falsifier"), str) and h["falsifier"].strip(), "falsifier required")
    eids = set()
    for record in evidence:
        _need(isinstance(record, dict), "evidence record must be an object")
        eid = record.get("id")
        _need(isinstance(eid, str) and eid.strip(), "evidence id required")
        _need(eid not in eids, f"duplicate evidence id: {eid}")
        eids.add(eid)
        _need(record.get("hypothesis_id") in ids, f"unknown hypothesis for {eid}")
        _need(record.get("design") in DESIGNS, f"unsupported study design for {eid}")
        _need(record.get("direction") in DIRECTIONS, f"unsupported direction for {eid}")
        _need(record.get("species") in SPECIES, f"unsupported species for {eid}")
        _need(type(record.get("synthetic")) is bool, f"synthetic must be boolean for {eid}")
        group = record.get("independence_group")
        _need(isinstance(group, str) and group.strip(), f"independence_group required for {eid}")
        _need(isinstance(record.get("summary"), str) and record["summary"].strip(), f"summary required for {eid}")
        if "sample_size" in record:
            _need(type(record["sample_size"]) is int and record["sample_size"] > 0,
                  f"sample_size must be positive integer for {eid}")
        if not record["synthetic"]:
            source = record.get("source_url")
            _need(isinstance(source, str) and source.startswith("https://") and "." in source,
                  f"non-synthetic evidence requires HTTPS source_url for {eid}")
    return bundle

def digest(bundle: dict) -> str:
    payload = json.dumps(bundle, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def audit(bundle: dict) -> dict:
    validate(bundle)
    results = []
    for hypothesis in bundle["hypotheses"]:
        records = [e for e in bundle["evidence"] if e["hypothesis_id"] == hypothesis["id"]]
        usable = [e for e in records if not e["synthetic"] and e["design"] in EMPIRICAL]
        grouped = defaultdict(list)
        for e in usable:
            grouped[e["independence_group"]].append(e)
        signals = {}
        for group_id, members in sorted(grouped.items()):
            directions = {m["direction"] for m in members}
            if "contradicts" in directions and "supports" in directions:
                direction = "mixed"
            elif "contradicts" in directions:
                direction = "contradicts"
            elif "supports" in directions and "mixed" not in directions:
                direction = "supports"
            else:
                direction = "inconclusive"
            signals[group_id] = direction
        supporting = sum(v == "supports" for v in signals.values())
        contradicting = sum(v == "contradicts" for v in signals.values())
        if not grouped:
            stage = "no-empirical-evidence"
        elif contradicting or "mixed" in signals.values():
            stage = "contested"
        elif supporting >= 2:
            stage = "replicated-signal-not-causation"
        else:
            stage = "needs-independent-replication"
        results.append({
            "id": hypothesis["id"], "hallmark": hypothesis["hallmark"], "claim": hypothesis["claim"],
            "stage": stage, "input_records": len(records),
            "excluded_synthetic": sum(bool(e["synthetic"]) for e in records),
            "excluded_nonempirical": sum(not e["synthetic"] and e["design"] not in EMPIRICAL for e in records),
            "independence_groups": len(grouped), "supporting_groups": supporting,
            "contradicting_groups": contradicting,
            "human_intervention_groups": len({e["independence_group"] for e in usable
                                               if e["species"] == "human" and e["design"] == "intervention"}),
            "group_directions": signals,
            "caveat": "Declared independence is unverified; signal count is not proof of causation or clinical benefit.",
        })
    return {
        "engine": "phiage/v0.1", "schema_version": VERSION,
        "source_sha256": digest(bundle), "hypotheses": results,
        "disclaimer": "Research triage only. No evidence score establishes human rejuvenation or a treatment.",
    }

def load(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return validate(json.load(fh))
