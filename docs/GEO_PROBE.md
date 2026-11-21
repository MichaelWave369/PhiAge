# NCBI GEO source verification R0.3

This is **read-only metadata observation**, not an aging experiment result.

Source: [NCBI Programmatic Access to GEO](https://www.ncbi.nlm.nih.gov/geo/info/geo_paccess.html). The GEO Series Matrix can contain samples and optional expression values; supplementary files are dataset-specific. Nothing in a GEO Series entry alone confirms donor identity, correct group labels, quality control, licensing, or independence.

The initial small pilot target is [GSE307377](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE307377): *Bulk RNA-seq analysis of primary human dermal fibroblasts from young and aged donors*. NCBI describes four younger donors (ages 23–33) and five older donors (ages 64–72) and lists a supplementary 1.3 MB file named \`GSE307377_raw.txt.gz\`. Sample labels and supplementary structure must be checked before analysis.

Run:
\`\`\`bash
python -m phiage geo-probe GSE307377 --allow-network --with-counts --output geo-receipt.json
\`\`\`

The prototype fetches from pinned \`https://ftp.ncbi.nlm.nih.gov/geo/series/\` paths, refuses external redirects, caps compressed/decompressed sizes, parses GSM accessions, audits duplicate sample records, and saves compressed-file SHA-256 receipts. It does not handle restricted dbGaP files, analyze genes, normalize counts, infer independent donors, or declare a licensed dataset.

**Safety and research gates:** A successful network response only proves that a file could be fetched and parsed. It does not approve the source for human biological claims. Refer to \`data/source_registry.json\` for licensing, overlap and age metadata blockers. Published GSM records do not necessarily correspond one-to-one with people.

## Next steps
1. Curator verifies exact transcriptome sample labels, age groups and donor identifiers from original GEO metadata.
2. Curator verifies redistribution and conditions for processed expression data and records accession-to-file mapping and hashes.
3. A normalization-aware exploratory pipeline checks matrix dimensions, missingness and batch effects.
4. Any donor-level cross-validation must prevent sample leakage. A 4-vs-5 exploratory contrast is **not** cross-tissue replication.

## First live check (2026-11-21)
A non-blocking GitHub Actions integration check on PR #5 successfully retrieved:
- Series Matrix: 9 unique GSM accessions, 9 cells with age metadata, gzip SHA-256 `0410e57d6a6b7dbdfbaeee3595a439f801f3dccbbcf7f8aa7339e920cc6fd709`.
- Supplementary `GSE307377_raw.txt.gz`: 1,363,809 compressed bytes; 17 tab-separated columns; **zero column headings literally equal GSM accessions**; gzip SHA-256 `08102ba1c503ce08782eee5eab08619d04c5b396785dc027d65c737b5e1a640c`.

These observations verify two public artifacts could be retrieved and inspected, **not** that a correct sample-column crosswalk, donor independence, gene-level analysis, license clearance or any aging finding exists. The probe now includes public sample titles and columns for a conservative manual crosswalk audit.


## Public record captured

The exact metadata/header receipt from the successful non-blocking CI probe is saved at [`data/receipts/GSE307377_geo_probe_2026-11-21.json`](../data/receipts/GSE307377_geo_probe_2026-11-21.json), including the two SHA-256 hashes and the public nine-sample catalog.

**Crosswalk blocker:** The expression header includes eight non-sample columns (`Transcript/RepeatID`, chromosome, start, end, strand, length, copies, and annotation) followed by nine columns with `TM`/ `CKC` tags. They are not named by GSM accession. The tag names suggest five older and four younger profiles, but that is **not independent proof** of which individual column corresponds to which GSM or donor. The source registry must remain blocked until a documented mapping is established.


## TPM discovery
The official [GSE307377 GEO record](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE307377) also lists `GSE307377_tpm.txt.gz`, a separate deposited processed expression table. Probe its header with `--with-tpm`. TPM values are relative abundance estimates, **not** differential-expression test statistics or an age reversal measurement. The pipeline still refuses to infer which `TM` tag belongs to which GSM accession.

## Live deposited TPM observation (2026-11-21)

The CI probe retrieved `GSE307377_tpm.txt.gz` successfully (1,498,390 compressed bytes; SHA-256 `1b5a6e82268dcf05dec75f7b24109b06cb4006abe7b925be8fdad89bae38c1ad`). The header has **17 tab-separated columns**, eight annotation fields and nine `TM`-tagged data columns; none uses a GSM accession. The original first column is `Transcript/RepeatID`, so it is not safe to assume the rows are uniquely identified protein-coding genes.

The complete observed table-header receipt is preserved in [`data/receipts/GSE307377_tpm_2026-11-21.json`](../data/receipts/GSE307377_tpm_2026-11-21.json). The raw values were **not** statistically analyzed. A documented feature-ID mapping, normalization audit, donor mapping, and licensing check remain prerequisites.


## v0.4: Primary GEO sample Description resolves library label ambiguity

Nine GEO sample detail pages explicitly publish `Library name: TM…` in their **Description** fields, along with age/group/sex labels. The public sample-to-library mapping is now archived at [the crosswalk JSON](../data/crosswalks/GSE307377_gsm_to_library.json). It includes a primary GEO URL for every GSM and compares library IDs to both archived table headers.

**Resolution:** The expression-column identity ambiguity is resolved using public depositor metadata, not positional inference. This is not an assertion that every GSM is an independent donor. A complete scientific analysis remains gated by donor provenance, feature semantics, normalization, covariates, license review, and replication.

The read-only command `python -m phiage expression-qc --allow-network` validates public file hashes against the original receipts and scans table-level numeric quality and feature-ID properties. It does not produce gene-level or clinical aging conclusions.

## v0.4 live numerical QC (2026-11-21)

CI structurally scanned both pinned deposited tables: **27,142 unique feature identifiers and nine expression columns in each**. No missing, nonnumeric, nonfinite, negative, blank-ID or duplicate feature-ID entries were observed. Importantly, the file named `raw` contains **73,187 non-integer numeric entries**, so it is **not** automatically eligible for models requiring integer raw counts, despite its file label. The source describes HOMER pipeline processing; fractional values may have technical reasons, but those reasons are not validated here.

The QC now exposes `ordinary_integer_count_model_ready` separately from `structural_numeric_qc_pass`. Passing numeric QC does **not** mean statistical analysis is authorized or biologically interpretable. This is a technical observation, not an aging finding.

