# ΦAge | Open Computational Geroscience

**A research workbench for investigating mechanisms of biological aging through reproducible computational collaboration.**

> **Status:** v0.5 research prototype. **No treatment, human rejuvenation, or life-extension claim is established by this software.** This project does not provide medical advice, treatment instructions, clinical decision support, or validated biological-age estimation.

ΦAge is a public project from PHI369 Labs. Its aim is to make aging research easier to question, reproduce, and connect. Research agents should **challenge** evidence, not simply generate exciting claims.

## Start here

- **[Research dashboard](docs/index.html)**: interactive hallmark atlas and an explicitly hypothetical feedback-system simulator. This is a static website; it has no backend and makes no network requests except to load bundled files.
- **[12 hallmarks](data/hallmarks.json)**: annotated conceptual taxonomy from López-Otín et al., *Cell* (2023), DOI [10.1016/j.cell.2022.11.001](https://doi.org/10.1016/j.cell.2022.11.001).
- **[Observed feature QC receipt](data/receipts/GSE307377_feature_qc_summary_2026-11-21.json)**: archived summary from successful GitHub Actions, also rendered by the static dashboard. Source is one existing published GEO study, not independent aging replication.
- **[Source registry](data/source_registry.json)**: five documented candidate human datasets, all pending licensing and independence review. Run `python -m phiage sources data/source_registry.json` for a machine-readable readiness audit.
- **[First experiment](experiments/EXP-001.md)**: preregistered-style plan to assess cross-tissue reproducibility, causal ambiguity, and intervention tradeoffs.
- **[Evidence policy](docs/EVIDENCE_POLICY.md)**: how to distinguish hypotheses, observations, experiments, and human outcomes.

## Quick start (Python 3.10+, no dependencies)

```bash
python -m unittest discover -s tests -v
python -m phiage validate examples/synthetic-evidence.json
python -m phiage audit examples/synthetic-evidence.json
python -m phiage simulate --steps 80 --generation 0.06 --repair 0.04 --boost 0.0
python -m phiage sources data/source_registry.json --output source-audit.json
python -m phiage crosswalk --output crosswalk-audit.json
# Optional: live aggregate QC of two pinned NCBI GEO files; no biomedical results:
python -m phiage expression-qc --allow-network --output expression-qc.json
# Optional non-inferential feature/similarity QC; no gene-level claims:
python -m phiage feature-qc --allow-network --output feature-qc.json
# Optional bounded, read-only live GEO probe (does NOT analyze expression):
python -m phiage geo-probe GSE307377 --allow-network --with-counts --output geo-receipt.json
```

Save a machine-readable audit: `python -m phiage audit examples/synthetic-evidence.json --output audit.json`.

The sample evidence is **entirely synthetic**. The auditor correctly excludes every example from empirical corroboration. A simulation is a toy demonstration, not a prediction about humans.

## Architecture

```text
Public studies & datasets -> ingestion (future) -> structured evidence JSON
                                            -> validation + independence audit
                                            -> skeptical review & contradiction mapping
                                            -> hypotheses & falsifiable experiments
                                            -> reproducible receipts
                                                     |
                                          independent validation
```

Currently implemented:
- **Evidence contracts** and schema validation, including provenance, synthetic-data labeling, permitted designs, and duplicate IDs.
- **Independence-aware auditing**: repeated reports of one study cannot count as multiple independent results; reviews and simulations are excluded from independent empirical confirmation.
- **Contradiction-aware assessments**, including human/nonhuman evidence distinctions.
- **Deterministic toy feedback simulator** with adjustable parameters and exportable JSON, explicitly not calibrated to human biology.
- **Interactive static dashboard** in `docs/`, covering the 12 hallmarks, research questions, and an illustrative dynamics plot.
- **Candidate source registry audit v0.2**: DOI/accession-linked dataset discovery metadata, duplicate IDs, collection-family grouping, access/age/overlap/permission gates, and deterministic SHA-256 provenance receipts. **All five sources currently remain candidates; zero are approved for analysis.**
- **NCBI GEO probe v0.3:** allowlisted, bounded, read-only HTTPS retrieval of a public Series Matrix and vetted supplementary header, with SHA-256 and structural validation. Network access is **off by default**. This is a metadata check, not expression analysis or human efficacy evidence.
- **Verified public sample/library crosswalk v0.4:** nine one-to-one library labels from primary GEO sample Description fields matched against both raw and TPM headers. This clears *column identity*, not donor independence or analytical readiness.
- **Read-only aggregate expression QC:** exact SHA-256 pinning of real NCBI GEO count/TPM files; table shape, missing and invalid numeric cells, feature-ID duplication and descriptive totals, without differential expression or uploading rows.
- **Exploratory feature/similarity QC v0.5:** classify uncurated transcript identifier *syntax*, count literal annotation tags, measure sample zero fractions, and compute log1p(TPM) sample correlations, with no age-group hypothesis testing or medical claims.
- **Standard-library unit tests** and CI.

Not yet implemented: scientifically validated import, donor de-duplication or analysis of real expression measurements, PubMed adapters, independent computational agents, causal inference, omics integration, biological age calibration, human-intervention prediction, or claims of reversal.

## Evidence is not a scoreboard

A change in a biomarker does **not** establish longer human life or improved healthspan. Correlation is not causation. Independent source groups must be verified, not inferred. Counterevidence and missing data must appear alongside positive reports. Animal results cannot silently be promoted to human efficacy.

## Ecosystem

ΦAge is the **geroscience specialization**; [ΦDiscovery](https://github.com/MichaelWave369/PhiDiscovery) remains the general-purpose evidence triage foundation. The initial contract is designed to permit an adapter, but **no live integration is claimed**.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Research is open; clinical and laboratory experimentation require appropriate qualified oversight and ethics approval. **Do not submit private medical records or personal genomic data.**

## License

MIT. Source paper taxonomy credit: López-Otín et al. (2023), DOI:10.1016/j.cell.2022.11.001.
