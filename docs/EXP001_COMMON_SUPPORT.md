# ΦAge EXP-001 v0.9 · Common-support feasibility audit

This version compares **source metadata** within a *frozen 30–49-year* window, not aging-related transcript signals. It does **not** train, tune, validate or release an age predictor. No gene expression or participant-level records are exported.

## Why this window?

In v0.8, the original public GSE113957 metadata showed an under-supported 50–59 decade on the smaller sequencing platform GPL16791: only two samples against four GPL18573 samples. Before reading expression outcomes, v0.9 predeclares two decades, 30–39 and 40–49, and explicitly excludes both under-30 and 50-plus age groups. HGPS-depositor labels are not allowed into ordinary healthy chronological-aging comparisons.

Primary source: [NCBI GEO GSE113957](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE113957), original dataset published by [Fleischer et al. 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6300908/).

## Frozen metadata-only conditions

- Source label must equal depositor-reported Normal, not independently clinically certified.
- Age must be 30 ≤ age < 50 (reported in years/months, with no rounding across cutoff).
- Platform must be GPL18573 or GPL16791, and public sex label must be \`female\` or \`male\`; missing values block the balancing assessment rather than being silently assigned.
- Four age-decade-by-sex strata are examined. To pass the *descriptive support* gate, each has **at least two** samples on **each** platform, and the sum of minimum across-platform counts (maximum possible metadata-balanced pairs) must be at least **eight**.
- "Potential pairs" counts are a ceiling based on public metadata: there is **no actual patient matching, donor linkage, batch correction, statistical power or expression-level analysis**.
- The global scientific \`analysis_ready\` gate is **always false**, regardless of metadata support, until independent donor provenance, reuse permissions, culture/batch review and FPKM/TPM normalization are resolved.

## Run

\`\`\`bash
python -m unittest discover -s tests -v
python -m phiage common-support --allow-network --output common-support.json
\`\`\`

Network is disabled by default. The command fetches only the archived-sha256-pinned public NCBI GEO family SOFT metadata; it never downloads expression values or emits individual sample identifiers.

## Next review

If age-decade/sex cells are sparse, do **not** rebalance by inventing samples or changing the cutoffs after inspecting outcomes. A genuinely well-supported comparison may require additional donor-balanced public data or a simpler, separately justified exploratory design. Even a passing metadata gate would still not license an age association, aging-reversal claim or intervention.
