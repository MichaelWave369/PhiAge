# EXP-001 technical exploratory QC, version 0.5

**No clinical claims. No age-related significance tests. No new discovery.**

## Source and scientific context
- [GSE307377](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE307377), [BioProject PRJNA1320544](https://www.ncbi.nlm.nih.gov/bioproject/PRJNA1320544).
- Study context: [Nucleosome stability safeguards cell identity, stress resilience and healthy aging](https://pmc.ncbi.nlm.nih.gov/articles/PMC12458469/). This is a *published source dataset* used in a mechanistic paper, not independent replication of that paper.
- Nine primary human dermal fibroblast samples. Four "young" and five "old". Exact deposited library names are matched to original GSM sample metadata in the v0.4 crosswalk.

## Why a non-inferential profile?
The original HOMER output labels the first column \`Transcript/RepeatID\`; that ambiguous label does **not** mean all 27,142 entries are repetitive elements. The deposited command starts with \`analyzeRepeats.pl rna hg19\`, which can quantify transcripts/genes depending on annotation/options. Classification of the *text syntax* of the first-column identifiers and literal annotation strings is a first step, **not** authoritative biological identity mapping.

Previously observed \`GSE307377_raw.txt.gz\` contains 73,187 fractional numeric values, despite its name. Do **not** round or use methods requiring integer counts without verifying the original HOMER settings and provenance. The \`_tpm.txt.gz\` is labeled TPM by the original depositor; that does not establish normalization correctness or comparable clinical endpoints.

## Read-only workflow

\`\`\`bash
python -m unittest discover -s tests -v
python -m phiage crosswalk
python -m phiage feature-qc --allow-network --output /tmp/phiage-feature-qc.json
\`\`\`

No network request occurs without \`--allow-network\`. The program checks the approved NCBI GEO URL and compressed SHA-256 against archived receipts before reading data. No raw transcript-level values are uploaded or committed to GitHub.

The report contains:
1. Unverified syntactic feature-ID categories.
2. Literal last-field tokens from deposited \`Annotation/Divergence\`, with counts; these are uncurated metadata, not biological findings.
3. Number of features zero in all nine samples; per-sample zero fraction and mean log1p(TPM).
4. Pearson sample-to-sample correlation of log1p(TPM) over **all 27,142 features**, including zero rows. Undefined correlations are explicit \`null\`.
5. Explicit gates: \`feature_semantics_verified=false\`, \`donor_independence_verified=false\`, \`analysis_ready=false\`, \`claim_level=TECHNICAL_QC_ONLY\`.

## Preregistration-style interpretation limits

Correlations across the same features in the same cell type may be high even if there are batch effects. They are technical similarity measures, **not evidence that aging is reversible**. The two age ranges do not overlap, sample size is tiny and culture duration, passage, batch, donor conditions and hidden confounders may influence results. No age-associated gene/pathway hypothesis is being tested here.

## Next analysis gate

Before any confirmatory comparisons, independently establish gene/feature mapping and provenance of the HOMER command, donor-level biological independence and documented culture/batch covariates, reuse terms, and a second independent human cohort. A same-paper reanalysis is not biological replication.

## Robustness improvement (after first live run)
To avoid overstating similarity caused by shared all-zero transcripts, the report separately computes correlations using only entries with expression in at least one of the nine samples. The original all-feature results remain available for transparency. Both are *descriptive technical quality checks*, not independent scientific replication or age-discrimination validation. Medians use the actual midpoint for 36 sample pairs rather than selecting a single central rank.

## Recorded live results, 2026-11-21

An [approved-by-CI technical run](https://github.com/MichaelWave369/PhiAge/actions/runs/44963480887) retrieved the hash-pinned official GEO TPM table. All 27,142 feature IDs matched RefSeq transcript-accession *syntax*. Depositor annotation tails contained 19,302 protein-coding, 6,371 ncRNA, 1,014 pseudogene ("pseudo"), 413 snoRNA, 39 snRNA, two rRNA, and one scRNA entries. These are metadata counts, **not independently curated gene identities**.

6,731 feature rows were zero in every sample, leaving 20,411 rows with at least one non-zero value. Across the 36 sample pairs, correlations on log1p(TPM) were 0.968799–0.995574 (all rows; median 0.989159) and 0.960331–0.994422 (non-all-zero rows; median 0.986313). These are *descriptive quality metrics* from nine samples of a published study, not age-discrimination results.

The source-backed [summary receipt](../data/receipts/GSE307377_feature_qc_summary_2026-11-21.json) is duplicated into the GitHub Pages site for transparent public inspection. It contains only aggregate observations and source hashes, not full gene-expression rows.

