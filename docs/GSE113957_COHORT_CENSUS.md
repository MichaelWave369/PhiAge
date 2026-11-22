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
python -m phiage cohort-probe GSE113957 --allow-network --output cohort-census.json
\`\`\`

Runs solely against a fixed NCBI GEO Series Matrix HTTPS URL, using bounded gzip decompression, fixed-source checksum receipt, and synthetic parser tests. The command does not fetch raw sequencing, participant private records, or gene-expression rows for analysis. It counts unique **GSM sample IDs**, public-characteristic fields, strictly parseable ages, and explicit sample-level health/HGPS labels. Samples without clear statements remain \`unknown\`, and conflicting statements are marked \`conflicting\`; **no ID-pattern guesswork**.

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
