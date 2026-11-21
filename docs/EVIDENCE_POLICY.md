# ΦAge evidence policy

1. **Provenance:** every non-synthetic evidence record must link to an identifiable source; unverified citations are never treated as reviewed studies.
2. **Independence:** distinct publications, preprints, or summaries may come from the same underlying study; group them and record uncertainty. The current software trusts declared groups and **does not verify independence**.
3. **Design:** reviews and simulations cannot count as independent empirical replication. Observational effects are not causal.
4. **Species:** nonhuman results cannot establish human efficacy. Explicitly distinguish human interventions from animal and in-vitro evidence.
5. **Endpoints:** biomarkers, molecular shifts, functional outcomes, clinical outcomes, healthspan and lifespan are separate measures.
6. **Contradictions:** conflicting records must be visible; no averaging them away into a confidence score.
7. **Causality:** require perturbation, robust causal design, or qualified analysis; every hypothesis must have a falsifier.
8. **Research safety:** all research claims are provisional and subject to competent peer review; no personalized medical decisions.
9. **Synthetic fixtures:** invented examples always have `synthetic: true`; they are excluded from empirical evidence counts.
10. **Reproducibility:** publish transformations, code, provenance, assumptions, negative results, and explicit uncertainty.

**Status vocabulary:** `no-empirical-evidence`, `needs-independent-replication`, `contested`, and `replicated-signal-not-causation`. None means proven treatment or human rejuvenation.

Foundational taxonomy: Carlos López-Otín et al. (2023), *Cell*, DOI [10.1016/j.cell.2022.11.001](https://doi.org/10.1016/j.cell.2022.11.001), PubMed [36599349](https://pubmed.ncbi.nlm.nih.gov/36599349/).
