# GSE113957 second-cohort audit (v0.6)

## Intended role
Metadata-only investigation of a **candidate** second human fibroblast cohort for EXP-001. No confirmatory analysis is authorized by the mere appearance of a GEO series accession.

Primary sources:
- [NCBI GEO GSE113957](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE113957)
- [Fleischer et al. (2018), Predicting age from the transcriptome of human dermal fibroblasts](https://pmc.ncbi.nlm.nih.gov/articles/PMC6300908/)
- [A source GSM record illustrating FPKM methods](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM3124655)

The publication describes fibroblasts from 133 healthy individuals of ages 1–94 and 10 patients with Hutchinson-Gilford progeria syndrome. These **publication counts do not establish how many independently analyzable donors have complete metadata**.

## New read-only gate
\`\`\`bash
python -m unittest discover -s tests -v
python -m phiage cohort-probe GSE113957 --allow-network --with-fpkm --output cohort-census.json
\`\`\`

Runs solely against a fixed NCBI GEO family SOFT HTTPS URL, using bounded gzip decompression, fixed-source checksum receipt, and synthetic parser tests. The command does not fetch raw sequencing, participant private records, or gene-expression rows for analysis. It counts unique **GSM sample IDs**, public-characteristic fields, strictly parseable ages, and explicit sample-level health/HGPS labels. Samples without clear statements remain \`unknown\`, and conflicting statements are marked \`conflicting\`; **no ID-pattern guesswork**.

## What it does not certify
- Whether each GSM corresponds to a unique independent human donor
- Whether samples labeled HGPS should be excluded or included in an age-related model
- Exact, independently reviewed ages and cell-passage conditions
- Author-provided sample-to-matrix columns for processed FPKM values
- Transcript/gene version and quantification harmonization vs GSE307377
- Licensing/reuse or metadata sufficiency for statistical analysis

A successful metadata probe must still output \`analysis_ready:false\`, \`healthy_hgps_grouping_verified:false\`, \`donor_independence_verified:false\`, and \`claim_level:COHORT_METADATA_DISCOVERY_ONLY\`.

## Next stage
Independently validate published sample/donor mapping, specimen/cell line overlap, FPKM source filename, expression-column keys, replicate structure, culture confounders and public reuse terms. Only then decide whether a frozen hold-out design is feasible. Keep original healthy and HGPS cohorts distinct. Never treat an HGPS phenotype as ordinary accelerated healthy aging, or reuse of this dataset as an independent validation cohort.

## Correct source file layout (verified in official NCBI FTP directory)

The expected `GSE113957_series_matrix.txt.gz` returned HTTP 404. Instead, the [SOFT directory](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE113nnn/GSE113957/soft/) contains the official `GSE113957_family.soft.gz` (approximately 12 KB compressed), and the [supplementary directory](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE113nnn/GSE113957/suppl/) contains `GSE113957_fpkm.txt.gz` (approximately 7.2 MB compressed). Both links were inspected as public official directory listings. **No file checksums or row-to-GSM crosswalk have been verified at this stage.**

SOFT is block-oriented (`^SAMPLE = GSM…`), unlike the column-oriented GEO Series Matrix. The dedicated parser extracts sample-level fields, then transposes metadata *in memory only* to reuse conservative validation. An optional `--with-fpkm` downloads only the bounded published FPKM file to inspect its first header row and record an immutable compressed-file checksum. It does not analyze expression values. The source census remains unapproved for analysis.

## Further evidence gates from the live census

The primary SOFT metadata explicitly reports disease codes `Normal` and `HGPS`. A conservative update now recognizes the exact `disease: Normal` label as a **source-assigned control group**, not an independently verified healthy phenotype. Years-and-months formats (for example `2yr3mos` and `6ys11mos`) are retained as fractional years rather than rounded to invented integer ages.

The published FPKM table has eight annotation columns followed by 143 public sample titles. A new check compares the exact public title set from SOFT sample blocks against these source column labels. It refuses duplicates and order-based guesses. Even a perfect name-to-column match **does not verify donor independence, the FPKM quantification model, biological feature harmonization, or data reuse rights**. The `analysis_ready` flag stays false.

## Observed live candidate-source results, 2026-11-22 UTC

A [successful GitHub Actions run](https://github.com/MichaelWave369/PhiAge/actions/runs/44965976209) verified **143 unique GSM sample records** from the source family SOFT. The public source explicitly lists 133 `disease: Normal` and 10 `disease: HGPS`, matching the paper's reported group split. The improved age parser recognized all 143 public age fields, some in years and months, spanning ages 1–96 *across both status groups*.

The separately deposited `GSE113957_fpkm.txt.gz` file contains 151 columns: eight annotation columns and 143 **unique** public sample-title columns. All 143 column names matched the SOFT sample titles exactly, providing a source-backed column name crosswalk without relying on positional assumptions. The gzip SHA-256 values are preserved in [the concise source receipt](../data/receipts/GSE113957_cohort_source_observation_2026-11-22.json).

**Remaining blockers:** the 143 samples have not been independently certified as 143 independent donors, exact source-donor overlap with other studies is unknown, cell-culture and experimental batch confounding remain, the FPKM process and feature harmonization vs GSE307377 remain unresolved, licensing/redistribution review is not complete, and no aging hypothesis has been tested. Source labels do not equal independent medical validation.
