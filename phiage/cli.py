"""Minimal dependency-free CLI for reproducible local experiments."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .evidence import EvidenceError, audit, load
from .simulation import simulate
from .sources import RegistryError, audit_registry
from .geo_probe import GEOProbeError, probe as geo_probe
from .crosswalk import CrosswalkError, validate_crosswalk
from .expression_qc import ExpressionQCError, run_qc as expression_qc
from .feature_profile import run_profile as feature_profile

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="phiage", description="Evidence-first geroscience workbench")
    subs = parser.add_subparsers(dest="command", required=True)
    check = subs.add_parser("validate", help="validate JSON provenance contract")
    check.add_argument("input")
    triage = subs.add_parser("audit", help="independence-aware skeptical triage")
    triage.add_argument("input")
    triage.add_argument("--output", help="write JSON receipt to disk")
    sim = subs.add_parser("simulate", help="run an educational, uncalibrated toy model")
    sim.add_argument("--steps", type=int, default=80)
    sim.add_argument("--generation", type=float, default=0.06)
    sim.add_argument("--repair", type=float, default=0.04)
    sim.add_argument("--boost", type=float, default=0.0)
    sim.add_argument("--output", help="write JSON receipt to disk")
    sources = subs.add_parser("sources", help="audit candidate datasets and EXP-001 readiness")
    sources.add_argument("input", help="local source registry JSON")
    sources.add_argument("--output", help="write deterministic JSON audit to disk")
    sources.add_argument("--require-ready", action="store_true",
                         help="exit 3 unless at least one source passes the metadata gates")
    geo = subs.add_parser("geo-probe", help="read-only structural metadata probe of NCBI GEO")
    geo.add_argument("accession", help="GSE accession from the EXP-001 allowlist")
    geo.add_argument("--allow-network", action="store_true", help="explicitly permit bounded HTTPS GEO fetches")
    geo.add_argument("--with-counts", action="store_true", help="inspect a vetted public supplementary-file header")
    geo.add_argument("--with-tpm", action="store_true", help="inspect deposited TPM table header")
    geo.add_argument("--output", help="write immutable JSON probe receipt")
    cross = subs.add_parser("crosswalk", help="verify nine primary-source GEO library mappings")
    cross.add_argument("--mapping", default="data/crosswalks/GSE307377_gsm_to_library.json")
    cross.add_argument("--geo-receipt", default="data/receipts/GSE307377_geo_probe_2026-11-21.json")
    cross.add_argument("--tpm-receipt", default="data/receipts/GSE307377_tpm_2026-11-21.json")
    cross.add_argument("--output")
    numeric = subs.add_parser("expression-qc", help="read-only QC of pinned public GEO count and TPM tables")
    numeric.add_argument("--mapping", default="data/crosswalks/GSE307377_gsm_to_library.json")
    numeric.add_argument("--geo-receipt", default="data/receipts/GSE307377_geo_probe_2026-11-21.json")
    numeric.add_argument("--tpm-receipt", default="data/receipts/GSE307377_tpm_2026-11-21.json")
    numeric.add_argument("--allow-network", action="store_true")
    numeric.add_argument("--output")
    profile = subs.add_parser("feature-qc", help="explore feature ID syntax and technical sample similarity")
    profile.add_argument("--mapping", default="data/crosswalks/GSE307377_gsm_to_library.json")
    profile.add_argument("--geo-receipt", default="data/receipts/GSE307377_geo_probe_2026-11-21.json")
    profile.add_argument("--tpm-receipt", default="data/receipts/GSE307377_tpm_2026-11-21.json")
    profile.add_argument("--allow-network", action="store_true")
    profile.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            bundle = load(args.input)
            data = {"valid": True, "hypotheses": len(bundle["hypotheses"]),
                    "evidence": len(bundle["evidence"])}
        elif args.command == "audit":
            data = audit(load(args.input))
        elif args.command == "geo-probe":
            data = geo_probe(args.accession, allow_network=args.allow_network,
                             with_counts=args.with_counts, with_tpm=args.with_tpm)
        elif args.command in ("crosswalk", "expression-qc", "feature-qc"):
            mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
            geo = json.loads(Path(args.geo_receipt).read_text(encoding="utf-8"))
            tpm = json.loads(Path(args.tpm_receipt).read_text(encoding="utf-8"))
            if args.command == "crosswalk":
                data = validate_crosswalk(mapping, geo, tpm)
            elif args.command == "expression-qc":
                data = expression_qc(mapping, geo, tpm, allow_network=args.allow_network)
            else:
                data = feature_profile(mapping, geo, tpm, allow_network=args.allow_network)
        elif args.command == "sources":
            data = audit_registry(json.loads(Path(args.input).read_text(encoding="utf-8")))
        else:
            data = simulate(args.steps, args.generation, args.repair, args.boost)
        body = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        output = getattr(args, "output", None)
        if output:
            Path(output).write_text(body, encoding="utf-8")
            print(f"Wrote {output}")
        else:
            print(body, end="")
        if args.command == "sources" and args.require_ready and data["analysis_ready_count"] == 0:
            print("phiage: no source passes the EXP-001 readiness gate", file=sys.stderr)
            return 3
        return 0
    except (ValueError, EvidenceError, RegistryError, GEOProbeError, CrosswalkError, ExpressionQCError, OSError, json.JSONDecodeError) as exc:
        print(f"phiage: {exc}", file=sys.stderr)
        return 2
