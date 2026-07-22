# Data availability and public-release boundary

## Included in this repository

- manuscript Figures 1-5 and Supplementary Figures S1-S14 as PNG/PDF files;
- manuscript Tables 1-3 and Supplementary Tables S1-S24 as aggregate CSV files after the final consistency revision;
- calculator screenshots used for Supplementary Figure S14;
- the static two-module research-use calculator.

## Not redistributed

- raw OAI, MRKR, or CHECK files;
- row-level or knee-level analytic datasets;
- patient, knee, examination, image, encounter, procedure, or date identifiers;
- image-level hardware observations or CPT-level records;
- individual prediction vectors, resampling assignments, or follow-up records.

OAI data require an NDA account and acceptance of the applicable access terms through the [NIMH Data Archive](https://nda.nih.gov/oai/). The Emory Knee Radiograph (MRKR) dataset is documented by [Nightingale Open Science](https://docs.ngsci.org/datasets/mrkr-emory-xray/) and listed in the [Registry of Open Data on AWS](https://registry.opendata.aws/mrkr/); the hosted resource is marked as controlled access. CHECK data remain subject to study-specific approval and access conditions. De-identification does not remove these contractual and governance restrictions.

## Reproduction levels

1. **Public verification:** inspect aggregate figure/table outputs, calculator logic, and public reproducibility scripts without restricted data.
2. **Full local reproduction:** obtain authorized source data, reconstruct the documented local directory structure, and run the released analysis pipeline.

No raw or row-level clinical data are required to use the static calculator.
