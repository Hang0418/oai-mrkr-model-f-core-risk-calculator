# Data availability and public-release boundary

## Included in this repository

- exact Model F-core coefficients, pain-standardization parameters, OAI baseline cumulative hazards, and apparent MRKR recalibration parameters;
- manuscript Tables 1-4 and Supplementary Tables S1-S16 as aggregate CSV files;
- aggregate source data supporting the released figures;
- final Figures 1-5 and Supplementary Figures S1-S10;
- analysis and figure-generation code;
- the static research-use calculator.

## Not redistributed

- raw OAI, MRKR, or CHECK files;
- row-level or knee-level analytic datasets;
- patient, knee, examination, image, encounter, procedure, or date identifiers;
- image-level hardware observations or CPT-level records;
- individual prediction vectors, resampling assignments, or follow-up records.

OAI data must be obtained through the OAI data-access process. MRKR data are institutionally governed real-world clinical/imaging data. CHECK data remain subject to their source access terms. De-identification does not remove these contractual and governance restrictions.

## Reproduction levels

1. **Public verification:** inspect exact formulas, aggregate tables, source-data summaries, and vector figures without restricted data.
2. **Full local reproduction:** obtain authorized source data, reconstruct the documented local directory structure, and run the released analysis pipeline.

No raw or row-level clinical data are required to use the static calculator.
