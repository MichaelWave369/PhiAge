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
