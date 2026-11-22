# EXP-001 v0.8 | Frozen pre-analysis design and statistical guardrails

This is an auditable pre-analysis **design draft**, not an externally preregistered confirmatory study and not a biological age model. Prior v0.4–0.7 work inspected sample metadata and aggregate transcript quality; it did not test age-expression hypotheses.

## Exact study definition

- **Source:** original public GSE113957 fibroblast RNA-seq cohort, FPKM processed expression, 133 samples deposited as \`Normal\` and 10 as \`HGPS\`. See [NCBI GEO](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE113957) and [Fleischer et al. (2018)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6300908/).
- **Eligibility for exploratory healthy-aging study:** sample explicitly labeled \`Normal\`, with a parseable public age of at least 20 years. This intentionally excludes childhood and adolescence; it does **not** certify the source label or independence of donors.
- **Exclusions:** HGPS source label for normal age prediction; samples with unknown or contradictory health labels or unparseable age.
- **Platform-aware design:** GPL18573 is the larger discovery source; GPL16791 is a small, shifted-platform feasibility stress test, **not an interchangeable random held-out cohort**. Its limited age overlap must be measured before interpreting any transport test.
- **Candidate independent replication source:** GSE307377 (nine fibroblast samples), with published TPM matrix and 24,560 exact overlapping RefSeq labels; transfer evaluation is **not** authorized until differing preprocessing and donor provenance are reviewed.

## Prospective negative controls (not executed)

1. Age labels permuted within the admissible platform/sex strata using a deterministic seed, only if enough samples support valid permutations.
2. Platform-only and sex-only baseline versus transcript-dependent signal.
3. Random-feature and zero-expression negative controls.
4. A temporally and cohort-disjoint validation design with donor/line leakage checks; explicit failure if the design cannot separate donors.
5. Age-decade sensitivity and model uncertainty, multiple-testing control, batch-effect diagnostics, and a locked feature/preprocessing pipeline before seeing age-effect results.

## Gate checklist

| Gate | Status |
|---|---|
| GSE113957 public metadata label/source receipt | Verified as depositor metadata |
| Source file bytes and RefSeq text overlap | Verified by SHA-256 only |
| Adult Healthy/Normal source eligibility stratification | v0.8 design audit |
| Platform-specific age distributions and sex imbalance | v0.8 design audit |
| Same person/line across studies ruled out | **Not verified** |
| FPKM-vs-TPM normalization and annotation equivalence | **Not verified** |
| Culture conditions, passage, batch confounding and reuse terms | **Not verified** |
| Predictive model or age-associated effect | **Not performed** |
| Biological replication, clinical benefit, life extension | **Not established** |

**Important:** Passing a *metadata* feasibility check does not open the biological analysis gate. All sample and expression analysis remains read-only until evidence and review are sufficient.

Run \`python -m phiage design-preflight --allow-network --output design-preflight.json\`. The command fetches only the exact pinned public source SOFT gzip and emits aggregate results. The frozen contract lives at \`data/design/EXP001_frozen_preflight_v08.json\`.

**Additional conservative gate:** every decade shared by both platforms must contain at least three public Normal-labeled adult samples on each platform. This is only a descriptive support threshold, not an assertion of statistical power. A sparse decade blocks the exploratory transport metadata gate; an approved model would still require donor identity, confounding, and quantification review.

## First live source-backed feasibility observation (2026-11-22 UTC)

From the pinned NCBI GEO SOFT file, there are 143 GSMs. Applying the declared **Normal source label and age ≥20** yields **107 adults**, 94 on GPL18573 and 13 on GPL16791. All HGPS samples are excluded. Age ranges overlap **30–50 years**. Shared age-decade counts (GPL18573 / GPL16791): **30–39 = 11/3**, **40–49 = 6/8**, **50–59 = 4/2**.

The 50–59 bin has only two GPL16791 profiles, below the declared descriptive minimum of three per platform per shared decade. Therefore **`exploratory_transport_metadata_gate_passed:false`**. This is a feasibility gate, **not** a statistical power calculation and not a negative biological finding.

The live [GitHub Actions run](https://github.com/MichaelWave369/PhiAge/actions/runs/44976453778) verified source checksum, frozen design hash and cohort composition. Its aggregate [JSON receipt](../data/receipts/GSE113957_design_preflight_2026-11-22.json) is preserved, with `analysis_ready:false`, `training_or_hypothesis_test_performed:false`, and `donor_independence_verified:false`.
