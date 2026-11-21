# ΦAge | Open Computational Geroscience

**A research workbench for investigating mechanisms of biological aging through reproducible computational collaboration.**

> **Status:** v0.1 research prototype. **No treatment, human rejuvenation, or life-extension claim is established by this software.** This project does not provide medical advice, treatment instructions, clinical decision support, or validated biological-age estimation.

ΦAge is a public project from PHI369 Labs. Its aim is to make aging research easier to question, reproduce, and connect. Research agents should **challenge** evidence, not simply generate exciting claims.

## Start here

- **[Research dashboard](docs/index.html)**: interactive hallmark atlas and an explicitly hypothetical feedback-system simulator. This is a static website; it has no backend and makes no network requests except to load bundled files.
- **[12 hallmarks](data/hallmarks.json)**: annotated conceptual taxonomy from López-Otín et al., *Cell* (2023), DOI [10.1016/j.cell.2022.11.001](https://doi.org/10.1016/j.cell.2022.11.001).
- **[First experiment](experiments/EXP-001.md)**: preregistered-style plan to assess cross-tissue reproducibility, causal ambiguity, and intervention tradeoffs.
- **[Evidence policy](docs/EVIDENCE_POLICY.md)**: how to distinguish hypotheses, observations, experiments, and human outcomes.

## Quick start (Python 3.10+, no dependencies)

```bash
python -m unittest discover -s tests -v
python -m phiage validate examples/synthetic-evidence.json
python -m phiage audit examples/synthetic-evidence.json
python -m phiage simulate --steps 80 --generation 0.06 --repair 0.04 --boost 0.0
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
- **Standard-library unit tests** and CI.

Not yet implemented: ingestion of real datasets, PubMed adapters, independent computational agents, causal inference, omics integration, biological age calibration, human-intervention prediction, or claims of reversal.

## Evidence is not a scoreboard

A change in a biomarker does **not** establish longer human life or improved healthspan. Correlation is not causation. Independent source groups must be verified, not inferred. Counterevidence and missing data must appear alongside positive reports. Animal results cannot silently be promoted to human efficacy.

## Ecosystem

ΦAge is the **geroscience specialization**; [ΦDiscovery](https://github.com/MichaelWave369/PhiDiscovery) remains the general-purpose evidence triage foundation. The initial contract is designed to permit an adapter, but **no live integration is claimed**.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Research is open; clinical and laboratory experimentation require appropriate qualified oversight and ethics approval. **Do not submit private medical records or personal genomic data.**

## License

MIT. Source paper taxonomy credit: López-Otín et al. (2023), DOI:10.1016/j.cell.2022.11.001.
