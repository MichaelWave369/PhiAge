# EXP-001 v1.0 | Primary-source provenance coverage

**Purpose:** identify what the original public GEO metadata can and cannot establish about cell lines, human donors, culture and sequencing protocols. This is a source-evidence audit, **not biological age inference**, and does not process expression matrices.

## Original datasets

- [GSE113957](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE113957), [Fleischer et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC6300908/): fibroblasts obtained from cell repositories, published sample \`cell id\` values often in Coriell-like \`GM...\` format, donor age/sex and Normal/HGPS status by depositor. A unique public cell-line ID is not independent evidence of a unique *human donor*.
- [GSE307377](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE307377): nine donor-age-labeled skin fibroblast records, with \`TM...\` and \`CKC...\` source/library names that cannot be equated to \`GM...\` repository IDs. GEO [GSM9222986](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM9222986) provides an example of the primary source metadata.

## What is computed

The new \`provenance-gate\` command fetches only two explicitly allowed **official NCBI source metadata files**, validates their complete compressed SHA-256 against committed observations, and reports:
1. Sample-level coverage of clearly named **donor/subject/person** identifiers versus **cell-line** identifiers, without conflating them.
2. Duplicate *labels* in each namespace, but **never** infers that unique labels imply unique donors.
3. Explicit passage-number fields and missingness.
4. Presence, missingness and distinct literal text versions of deposited growth, treatment and extraction protocols and source-name descriptions. Protocol text presence is **not** independent experimental certification.
5. A blocked donor-linkage gate with evidence gaps and an explicit \`null\` instead of a fake numeric overlap score.

No sample-level, donor-level, Coriell, accession or cell-line identifiers are returned or stored in the report. Zero exact strings in two incompatible namespaces would still not establish zero overlapping donors.

## Command

\`\`\`bash
python -m unittest discover -s tests -v
python -m phiage provenance-gate --allow-network --output provenance-gate.json
\`\`\`

By default there is **no network**. PR-only GitHub Actions source probes are informational; synthetic tests remain deterministic.

## Independent-replication stop rule

The documented source material is insufficient to certify person-level uniqueness and independence across two projects. Any later study must (a) establish sample acquisition and provenance for both cohorts, (b) confirm clinical metadata and bioethical reuse permissions, (c) evaluate cell-culture passage and processing/batch comparability, and (d) freeze a donor-held-out statistical design before testing age associations.

\`cross_cohort_same_person_linkage_evaluable:false\`; \`donor_independence_verified:false\`; \`analysis_ready:false\`; \`age_effects_tested:false\`; and \`claim_level:SOURCE_PROVENANCE_GAPS_ONLY\`.

## Live primary-source evidence (2026-11-22 UTC)

The [v1.0 GitHub Actions provenance probe](https://github.com/MichaelWave369/PhiAge/actions/runs/44991103995) validated the deposited compressed-file checksums and found:

| Source-backed metadata field | GSE113957 | GSE307377 |
|---|---:|---:|
| GEO samples | 143 | 9 |
| Explicit donor/subject ID field | 0 | 0 |
| Public `cell id` field | 143 | 0 |
| Public `cell line` **description** field | 0 | 9 |
| Sample-level passage field | 0 | 0 |
| Growth protocol field | 143 | 9 |
| Extraction protocol field | 143 | 9 |
| Treatment protocol field | 0 | 9 |

GSE113957 deposited source-name description is missing for nine samples, but complete growth and extraction protocol text is present. Its 143 public cell ID labels are distinct; 57 match `GM...` syntax, eight `HGADFN...`, and 78 other syntax. This is a **text-format inventory**, not an authenticity or human-donor identity check.

Across GSE113957's two NCBI sequencing platforms, the hashed **published** growth and extraction protocol-text combinations are identical: 13/13 GPL16791 and 130/130 GPL18573 each have the same deposited text fingerprints. This does **not** establish that experimental batches, RNA preparation details, sequencing library chemistry or passage counts were identical. GSE113957 still has no sample-level passage characteristic; GSE307377 likewise has none.

The frozen aggregate [provenance receipt](../data/receipts/GSE113957_GSE307377_provenance_gate_2026-11-22.json) includes zero participant IDs or raw metadata text, and retains `cross_cohort_same_person_linkage_evaluable:false`, `donor_independence_verified:false`, `analysis_ready:false`. Future evidence work requires source-backed biobank/donor provenance, not a string comparison between `GM...` cell IDs and `TM...` expression-library identifiers.
