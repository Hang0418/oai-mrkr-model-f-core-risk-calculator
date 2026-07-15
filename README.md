# Dynamic clinical-radiographic knee-replacement prediction

Public code, aggregate source data, final manuscript figures, and a research-use calculator for the OAI dynamic prediction study with MRKR transport validation and recalibration.

## Online calculator

[Model F-core research-use risk calculator](https://hang0418.github.io/oai-mrkr-model-f-core-risk-calculator/)

The calculator implements the exact OAI-derived Model F-core coefficients and supports:

- the original OAI 24-month risk equation;
- the apparent MRKR slope plus baseline recalibration;
- user-specified local pain standardization, calibration slope, and baseline cumulative hazard;
- automatic derivation of KL worsening from baseline and 24-month KL grades.

The MRKR output is the probability of first side-specific hardware-positive postoperative imaging. It is not an exact operation-date risk and is not a clinical decision instrument.

## Final manuscript framework

The repository mirrors the current manuscript and supplement.

### Main text

- Table 1: OAI and MRKR cohort characteristics.
- Table 2: strictly nested OAI Models A-E.
- Table 3: 24-month MRKR transport and recalibration performance.
- Table 4: MRKR outcome-timing and robustness analyses.
- Figure 1: cohort formation, landmark design, and model roles.
- Figure 2: incremental value of updated OAI information.
- Figure 3: Model E internal validation and clinical performance.
- Figure 4: OAI/MRKR follow-up and outcome ascertainment.
- Figure 5: MRKR transport, recalibration, and robustness.

### Supplement

- Supplementary Tables S1-S16 are released as CSV files.
- Supplementary Figures S1-S10 are released as PNG, editable PDF, and editable SVG files.
- CHECK appears only as an event-limited exploratory analysis in Supplementary Table S16 and Supplementary Figure S6.

The exact title-to-file mapping is in [`data/tables/table_manifest.csv`](data/tables/table_manifest.csv) and [`docs/figure_table_framework.md`](docs/figure_table_framework.md).

## Repository structure

```text
assets/figures/main/            final Figures 1-5
assets/figures/supplementary/   final Supplementary Figures S1-S10
data/model/                     exact Model F-core and recalibration parameters
data/tables/main/               manuscript Tables 1-4 as CSV
data/tables/supplementary/      Supplementary Tables S1-S16 as CSV
data/source_data/               public aggregate figure source data
data/dictionaries/              harmonization and variable dictionaries
scripts/                        final analysis and figure-generation pipeline
docs/                           framework, reproducibility, and data-access notes
index.html                      static GitHub Pages calculator
```

Historical draft generators, superseded figures, exploratory symptom-trajectory analyses, and the erroneous offset-only audit result are intentionally excluded from this release.

## Model F-core formula

The uncentered OAI linear predictor is:

```text
LP =
  0.001640774773 * age
  - 0.135837832150 * female
  + 0.004415913844 * right_knee
  + 0.290861790566 * pain_landmark_z
  + 0.778457697796 * baseline_KL
  + 1.019422117079 * KL_worsening
```

where `KL_worsening = 1` when `24-month KL - baseline KL >= 1`.

Original OAI risk at horizon `t`:

```text
risk_OAI(t) = 1 - exp[-H0_OAI(t) * exp(LP)]
```

Apparent MRKR imaging-setting recalibration:

```text
risk_MRKR(t) = 1 - exp[-H0_MRKR(t) * exp(0.681400186 * LP_MRKR)]
```

At 24 months, `H0_OAI = 0.003918718` and apparent `H0_MRKR = 0.070563879`. The MRKR primary implementation uses within-MRKR pain standardization, which is a target-cohort preprocessing adaptation rather than a completely frozen transport transformation.

Exact values are stored in [`data/model/`](data/model/).

## Reproducibility boundary

All reported aggregate tables, model parameters, and final figures are public here. Raw and row-level OAI, MRKR, and CHECK data are not redistributed because they remain governed by their source data-use agreements and institutional controls. OAI access is provided through the [NIMH Data Archive](https://nda.nih.gov/oai/). MRKR is documented by [Nightingale Open Science](https://docs.ngsci.org/datasets/mrkr-emory-xray/) and listed in the [Registry of Open Data on AWS](https://registry.opendata.aws/mrkr/), where the hosted resource is identified as controlled access.

The scripts document the full local analysis pipeline. Steps that operate on row-level data require independently authorized local copies. See [`DATA_AVAILABILITY.md`](DATA_AVAILABILITY.md) and [`docs/reproducibility.md`](docs/reproducibility.md).

## Software

- R 4.x with `survival` and `data.table` for the retained final analysis scripts.
- Python 3.10+ with `pandas`, `numpy`, and `matplotlib` for the retained figure pipeline; the calculator reference implementation uses only the standard library.

## Citation

Please cite the associated manuscript when using the model formula, aggregate validation results, figures, or calculator. The citation will be updated when a journal record or preprint DOI is available.

## License

Code is released under the repository license. Source datasets remain subject to their original access terms and are not relicensed by this repository.
