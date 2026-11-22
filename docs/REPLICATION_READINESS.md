# EXP-001 v0.7: GSE113957 replication-readiness audit

**Status: technical data qualification only.** This is an instrument for investigating which claims would be unsafe, not a published aging discovery.

## Primary sources

- NCBI [GSE113957](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE113957) and [PRJNA454681](https://www.ncbi.nlm.nih.gov/bioproject/454681).
- Fleischer et al. (2018), [Predicting age from the transcriptome of human dermal fibroblasts](https://doi.org/10.1186/s13059-018-1599-6).
- Source file hashes from [v0.6 candidate receipt](../data/receipts/GSE113957_cohort_source_observation_2026-11-22.json).
- Read-only outputs from \`python -m phiage replication-qc --allow-network\`.

## Why these checks matter

The original dataset reports 133 "Normal" and 10 HGPS fibroblast samples. The public \`cell id\` annotation can expose reused *labels* but not prove independent biological donors. The same series includes more than one sequencing platform in previously published reanalyses, so platform-by-group counts are important for eventual confounder adjustment. Source cell-culture conditions and RNA preparation can also affect observed expression.

Before any feature-level age analysis, the method verifies the exact pinned compressed bytes of the primary GEO SOFT metadata and FPKM table. The module refuses a changed checksum, unexpected columns, ambiguous metadata titles or duplicate GSM IDs. It then reports **only aggregated** sample-label duplication checks, platform-by-group counts and numeric matrix-quality measures. No individual participant's metadata or transcript expression rows are committed to the project.

### Core release gates

1. Source sample-to-column names: exact bijection on published labels, **not independence**.
2. Donor-level independence: no sample overlap or duplicate biological donors proven; remains blocked even if all \`cell id\` values differ.
3. Library and platform effects: report platform and health-group composition; no correction automatically assumed.
4. FPKM numerical format: check feature cardinality, duplicate IDs, missing/nonfinite/negative values and all-zero entries. Results are technical QA, not evidence of aging biology.
5. Cross-cohort transcript harmonization with GSE307377: unresolved. FPKM vs TPM magnitudes are not directly interchangeable, and shared accession syntax is not a sufficient annotation match.
6. Human age-effect test, replication and clinical claims: **not run**.

### Usage

\`\`\`bash
python -m unittest discover -s tests -v
python -m phiage replication-qc --allow-network --output /tmp/phiage-replication-qc.json
\`\`\`

The optional live job runs as an **informational, nonblocking** GitHub Actions check on pull requests; all deterministic safety tests run without fetching external files. No source accession is dynamically accepted from user input; network is off by default.

### Interpretation

An observation of 143 unique GEO sample names, unique public \`cell id\` labels, or an expression table without missing values cannot establish donor-level independence, a validated biological age predictor or lifespan extension. GSE113957 has already been studied by its authors and re-used in subsequent papers. A new analysis of it is reanalysis, not independent sample-level evidence of aging reversal.

## Transcript identity: a necessary but insufficient comparability check

`python -m phiage transcript-overlap --allow-network` fetches the **two immutable SHA-256-pinned official GEO tables**, examines only the first column of each, and counts exact RefSeq accession intersections, non-shared identifiers, source duplicates, and optional version-stripped intersections. It also checks if accession row order is exactly the same.

A perfect 27,142/27,142 identifier match would only establish **shared reference labels**, not equal abundance units (FPKM versus TPM), equivalent normalization, batch correction, or independent age-association replication. No version stripping is used to construct an analysis matrix automatically.

## Live observed results (2026-11-22 UTC)

[GitHub Actions run 44972049685](https://github.com/MichaelWave369/PhiAge/actions/runs/44972049685) verified both downloaded source artifacts against previously archived SHA-256 values.

**GSE113957:** 143 unique deposited `cell id` labels, no missing/duplicate labels, but **not an independent human donor audit**. Two GEO platforms: **GPL16791 = 13 Normal**, **GPL18573 = 120 Normal and 10 HGPS**. Study labels also show a marked sex imbalance: Normal = 99 male / 34 female; HGPS = 3 male / 7 female. Healthy-labeled age range in the public metadata is **1–96 years**, HGPS-labeled **2.25–8.833333 years**. Dataset rows: **27,142 unique transcript IDs**, **143 expression columns**, **3,929 all-zero entries**, no observed missing/nonfinite/negative values or duplicate feature identifiers. See [the archived aggregate QC receipt](../data/receipts/GSE113957_replication_qc_2026-11-22.json).

**Exact cross-cohort reference-label intersection:** GSE113957 and GSE307377 each contain 27,142 unique RefSeq-format transcript IDs; **24,560 match exactly, leaving 2,582 unmatched in each** (90.5% exact overlap). Stripping simple version suffixes did not increase the observed overlap. No biological/age-associated effect was tested, and expression/annotation equivalence remains **unverified**. See [the overlap receipt](../data/receipts/GSE113957_GSE307377_overlap_2026-11-22.json).

The platform-by-group imbalance and different abundance measurements (FPKM versus TPM) must be addressed **before** any held-out age-association hypothesis can be considered. Matching RefSeq strings is a necessary reference-label check, not independent validation of a gene-level scientific claim.
