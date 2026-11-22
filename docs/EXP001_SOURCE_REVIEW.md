# EXP-001 v1.1 | Review original evidence before comparing donors

**Status: blocked, source-scoped literature and provenance review only.** This phase creates no age model and makes no independent donor or life-extension claim.

## Major distinction corrected

The v1.0 public-**GEO** provenance gate accurately found no explicit sample-level \`passage\` characteristics in either downloaded GEO Series Matrix/SOFT source. **That is not the same as "the papers report no culture history".** Fleischer et al. (2018) describe study-level culture histories: healthy-group fibroblasts had mean population doubling **10 ± 4.2**; HGPS group mean passage number **11 ± 0.7**, and supplementary **Tables S2/S3** are linked in original [Additional file 1](https://static-content.springer.com/esm/art%3A10.1186%2Fs13059-018-1599-6/MediaObjects/13059_2018_1599_MOESM1_ESM.docx). Population doubling ≠ passage count, and the averages must **not** be assigned to specific GSM records. The file is an identified original supplement; its per-line content has **not yet been audited or crosswalked**.

Primary paper: [Fleischer et al., Genome Biology (2018)](https://link.springer.com/article/10.1186/s13059-018-1599-6). Methods state that apparently healthy fibroblast lines were obtained from Coriell's NIA/NIGMS cell repositories, while HGPS lines came from the Progeria Research Foundation. That establishes **reported collection sources**, not unique human donor IDs.

The [GSE307377 parent publication](https://pmc.ncbi.nlm.nih.gov/articles/PMC12458469/) reports nine young/older primary dermal fibroblast donors supplied by the **San Diego Nathan Shock Center Human Cell Models of Aging Core** and refers to supplementary Table 1. The [SD-NSC Clinical Cohort resource protocol](https://bmjopen.bmj.com/content/14/6/e082659) provides background about cohort biobanking, but is **not** a verified person-to-cell-line crosswalk for those nine GEO samples.

## Physical biomaterials are not public expression matrices

Coriell's original [NIGMS FAQ](https://www.coriell.org/1/NIGMS/FAQ) and [How to Order / MTA](https://www.coriell.org/1/NIGMS/How-to-Order) discuss consent, privacy, shipping, secondary distribution and terms for **physical cell cultures / DNA samples**. Their requirements should not be blindly applied as the copyright or licensing terms of independently posted RNA-seq expression datasets. Public GEO availability is not sufficient, by itself, to conclude unrestricted data reuse either. Review actual publication and data repository terms separately, with attribution, before redistribution. Do not expose or attempt to reconstruct private donor identities.

## New review ledger

[EXP001_provenance_review_v11.json](../data/evidence/EXP001_provenance_review_v11.json) lists the original source URLs, evidence granularity, source-specific factual statements, uncertainties and eight blocking scientific review gates. These gates cannot be marked passed simply by editing a JSON field: the validator rejects such promotion, requires a complete evidence trail, and checks the source snapshot against the archived v1.0 original GEO observations and hashes.

\`\`\`bash
python -m unittest discover -s tests -v
python -m phiage review-provenance --output /tmp/phiage-review-v11.json
\`\`\`

An **optional** \`python -m phiage supplement-probe --allow-network\` downloads only the publicly linked original publisher DOCX under explicit size, archive and XML limits, and reports caption presence, table count and SHA-256 **without** printing any original specimen rows or cell identifiers. It is not a sample-level audit. The PR-only live check is informational because publisher mirrors may refuse automated downloads.

## Hard research gates

1. Establish permitted, anonymized and independently verified human donor lineage for both cohorts.
2. Rule out cross-cohort donor overlap using appropriate authorized biobank provenance, **not** identifier guessing or personal reidentification.
3. Audit Fleischer original supplementary S2/S3, then verify any cell-line-to-GSM linkage; do not interchange population doublings with passages.
4. Audit GSE307377's original supplementary Table 1 for culture and sample acquisition context.
5. Review actual public expression-data permissions independently of physical biospecimen MTAs.
6. Validate culture/processing/platform/batch comparability and sample selection.
7. Verify transcript annotation and scale semantics between FPKM and TPM.
8. Obtain an externally reviewable, leakage-aware, predeclared statistical plan before age effect modeling.

No machine-readable \`analysis_ready:true\` can be produced by v1.1. A passing literature metadata review is not independent biological replication or a medical result.

## Original publisher DOCX structural checkpoint (22 November 2026 UTC)

The original Springer supplementary DOCX was downloaded successfully by [GitHub Actions run 44995236689](https://github.com/MichaelWave369/PhiAge/actions/runs/44995236689). Its observed 2,440,808 bytes yielded SHA-256 c5e38bdd1c188f34d228d40c0b768ac7155e8a4440265835b248a37c0fe87c94. The bounded Word XML parser counted 52 nonempty paragraphs, one native Word table with 11 rows, and mentions of Tables S2/S3. **These are document-structure observations only.** A table can be embedded as text or an image rather than a native Word table; no GSM-to-culture row mapping has been demonstrated.

The [archived publisher receipt](../data/receipts/Fleischer2018_supplement_structure_2026-11-22.json) is tied to the [review summary](../data/receipts/EXP001_source_review_summary_2026-11-22.json). The new review validator rejects mismatched publisher fingerprints and all attempts to promote a source-structure observation to person-level evidence. Eight review gates remain blocked.
