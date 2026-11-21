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
