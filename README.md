# Knee OA Stage-Specific Risk Calculator

This repository accompanies the manuscript:

**Stage-specific prediction of knee osteoarthritis progression and arthroplasty risk with real-world recalibration**

It contains the public manuscript figure/table assets, aggregate CSV tables, and a static research-use calculator. Raw CHECK, OAI, and MRKR source data are not included.

## Online Calculator

[Open the research-use calculator](https://hang0418.github.io/oai-mrkr-model-f-core-risk-calculator/)

The calculator includes two stage-matched modules:

| Module | Intended population | Prediction target | Development cohort |
|---|---|---|---|
| Early Radiographic Progression | Symptomatic knees with baseline KL grade 0 or 1 | 24-month incident KL >=2 | CHECK |
| Knee Arthroplasty Risk | Knees assessed at the OAI 24-month landmark across KL grades 0-4 | 60-month target-knee TKA/KR | OAI |

MRKR is used for transport validation and target-cohort recalibration of the arthroplasty-risk model.

## Repository Contents

```text
index.html                  Static research-use calculator
figures/main/               Main manuscript Figures 1-5
figures/supplementary/      Supplementary Figures S1-S14
tables/main/                Main manuscript Tables 1-3 as CSV
tables/supplementary/       Supplementary Tables S1-S24 as CSV
screenshots/                Calculator screenshots used for Supplementary Figure S14
```

## Use

The calculator and risk thresholds are for research communication and reproducibility only. They are not validated for treatment decisions, surgical eligibility, referral urgency, or individual patient management.

## Data Availability

Only aggregate figure/table outputs are provided. Original cohort-level source data must be obtained through the relevant CHECK, OAI, and MRKR data-access mechanisms.
