# OAI-MRKR Model F-core Risk Calculator

This repository contains the public code, aggregate results, figures, and static research-use calculator for the OAI-derived Model F-core transport validation in MRKR.

## Online Calculator

The calculator is a static GitHub Pages app:

https://hang0418.github.io/oai-mrkr-model-f-core-risk-calculator/

It estimates OAI-derived and recalibrated 24-month knee replacement risk using the common-variable Model F-core formula. The tool is intended for manuscript reproducibility, transport validation, and local recalibration research.

It is not a clinical decision calculator and must not be used to determine treatment, referral, surgery, or individual patient management.

## Repository Contents

- `index.html`: static research-use calculator.
- `scripts/`: analysis and manuscript-generation code.
- `data/aggregate/`: public aggregate tables, model coefficients, calibration summaries, performance metrics, and inclusion/exclusion summaries.
- `data/dictionaries/`: public schema and variable dictionaries used to interpret the analytic files.
- `assets/figures/`: publication-ready figures in PNG, PDF, and SVG formats.
- `docs/`: project notes, analysis plans, and data-access documentation.

## Data Availability

This repository intentionally does not include raw OAI, raw MRKR, or row-level derived cohort records.

OAI source data are available through the OAI data access process and are subject to the terms of that resource. MRKR source data and row-level derived MRKR records may contain institution-specific or restricted clinical information and require appropriate governance approval. The public release therefore includes only aggregate, non-row-level outputs needed to reproduce the reported model formula, figures, tables, and calculator implementation.

See `DATA_AVAILABILITY.md` for the exact release boundary.

## Model Formula

Model F-core uses the OAI Cox landmark model:

```text
LP =
  0.0016407748 * age
  - 0.1358378321 * female
  + 0.0044159138 * right_knee
  + 0.2908617906 * pain_landmark_z
  + 0.7784576978 * baseline_KL
  + 1.0194221171 * I(24-month KL - baseline KL >= 1)
```

Original OAI-derived risk at horizon `t`:

```text
risk(t) = 1 - exp[-H0_OAI(t) * exp(LP)]
```

MRKR slope plus baseline recalibration:

```text
risk_recalibrated(t) = 1 - exp[-H0_MRKR(t) * exp(slope_MRKR * LP)]
```

The full coefficient, baseline cumulative hazard, standardization, and recalibration tables are in `data/aggregate/`.

## Reproduce Key Outputs

From the repository root, after installing the R and Python dependencies used by the scripts:

```bash
Rscript scripts/19_reanalyse_oai_mrkr_transport_plan.R
Rscript scripts/24_oai_mrkr_ci_ph_formula_sensitivity.R
Rscript scripts/25_generate_sci_highres_figures.R
python3 scripts/26_rework_wps_manuscript_tables_figures.py
```

The scripts expect access to the restricted raw/row-level data in the local project structure. Public aggregate tables and figures are already included for transparent review of reported results.

## Citation

Please cite the associated manuscript when using the formula, calculator, or aggregate results.

