# Reproducibility guide

## Public verification

Run the release checker from the repository root:

```bash
python3 scripts/00_verify_public_release.py
```

This checks the expected 4 main tables, 16 supplementary table groups, 5 main figures, 10 supplementary figures, calculator coefficients, recalibration values, and absence of prohibited row-level files.

The reference implementation can be exercised with:

```bash
python3 scripts/01_model_f_core_reference.py \
  --age 64 --female 1 --right-knee 1 --pain 6 \
  --baseline-kl 3 --month24-kl 4 --mode both
```

Expected results are approximately 21.0% original OAI 24-month risk and 54.8% apparent MRKR 24-month hardware-detection risk.

## Full local analysis

The numbered scripts retained from the final project pipeline are:

1. `16_build_mrkr_transport_dataset.py`: build the side-specific MRKR transport cohort.
2. `48_prepare_mrkr_hardware_intervals.py`: reconstruct last-negative/first-positive hardware-detection intervals.
3. `48_latest_framework_reanalysis.R`: fit the final nested OAI and transport analyses.
4. `53_prepare_figure_revision_source_data.py`: prepare final aggregate plotting inputs.
5. `49_generate_latest_framework_figures.py`: generate Figure 1 and shared figure helpers.
6. `54_generate_reviewer_refined_figures_2_5.py`: generate final Figures 2-5.
7. `55_supplementary_consistency_audit.R`: recompute final supplementary performance summaries.
8. `50_generate_latest_supplementary_figures.py`: generate Supplementary Figures S1-S10.

These full-pipeline scripts retain the local project paths used in the analysis and require authorized row-level data. Public CSV files under `data/` are verification outputs, not substitutes for restricted source records.

## Statistical conventions

- Both knees from a participant/patient remain in the same resample, fold, or split.
- OAI confidence intervals and optimism correction use participant-level resampling.
- MRKR discrimination confidence intervals use patient-clustered bootstrap resampling.
- MRKR updating validation uses 100 repeated event-stratified 70/30 patient-level splits.
- Direct transport and apparent recalibration are distinguished from pooled held-out recalibration.
- MRKR event time is the first side-specific hardware-positive postoperative image unless a prespecified timing sensitivity is stated.
- CHECK is event-limited exploratory evidence and is not validation of the full Model E.
