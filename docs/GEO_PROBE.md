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

