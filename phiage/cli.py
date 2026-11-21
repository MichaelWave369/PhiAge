"""Minimal dependency-free CLI for reproducible local experiments."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .evidence import EvidenceError, audit, load
from .simulation import simulate
from .sources import RegistryError, audit_registry

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
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            bundle = load(args.input)
            data = {"valid": True, "hypotheses": len(bundle["hypotheses"]),
                    "evidence": len(bundle["evidence"])}
        elif args.command == "audit":
            data = audit(load(args.input))
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
    except (ValueError, EvidenceError, RegistryError, OSError, json.JSONDecodeError) as exc:
        print(f"phiage: {exc}", file=sys.stderr)
        return 2
