# Three-cohort baseline and outcome-risk summary

OAI and MRKR are summarized using the harmonized Model F-core transport datasets.
CHECK is summarized using the CHECK-compatible exploratory validation dataset; its event counts are limited and it should not be described as a definitive full Model E external validation.

Primary outputs:
- `three_cohort_baseline_characteristics.csv`
- `three_cohort_outcome_risk_by_horizon.csv`
- `three_cohort_baseline_and_outcome_risk_summary.xlsx`

Outcome risks are post-landmark cumulative risks. The Kaplan-Meier risk accounts for censoring before each horizon; the crude cumulative event proportion is provided for transparent denominators.
