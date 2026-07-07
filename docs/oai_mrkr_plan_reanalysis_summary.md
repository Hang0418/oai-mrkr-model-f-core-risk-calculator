# OAI-MRKR transport validation reanalysis summary

This reanalysis follows `OAI_MRKR_transport_validation_project_plan.docx`.

## Analysis position

The complete OAI Model E remains the main dynamic clinical-radiographic model. MRKR is used for real-world transport validation of a reduced common-variable model, not for direct external validation of the full OAI Model E.

The reanalysed Model F-core is:

`Surv(time_months, event_primary) ~ age + female + right_knee + pain_landmark_z + kl_baseline + kl_worsening`

where `pain_landmark_z` is cohort-specific standardized landmark pain and `kl_worsening = 1` if `kl_change >= 1`.

## Cohorts

| Cohort | Role | Knees | Patients | Total events | Event rate | Median follow-up |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| OAI | Training/model development | 3,104 | 1,656 | 566 | 18.2% | 84.0 months |
| MRKR | Real-world transport validation | 3,412 | 2,179 | 1,140 | 33.4% | 20.0 months |

MRKR had much earlier events than OAI. Median event time was 7.6 months in MRKR versus 61.0 months in OAI, supporting the plan's recommendation to make 24 months the main MRKR horizon and to include strict early-event sensitivity analyses.

## Model F-core coefficients in OAI

| Predictor | HR | 95% CI | P value |
| --- | ---: | ---: | ---: |
| Age | 1.002 | 0.991-1.012 | 0.761 |
| Female | 0.873 | 0.706-1.079 | 0.209 |
| Right knee | 1.004 | 0.879-1.148 | 0.948 |
| Landmark pain z-score | 1.338 | 1.235-1.449 | <0.001 |
| Baseline KL grade | 2.178 | 1.921-2.469 | <0.001 |
| KL worsening | 2.772 | 2.197-3.497 | <0.001 |

The common-variable model preserves the key OAI signal: structural severity and KL worsening dominate risk prediction, while higher landmark pain adds independent prognostic information.

## Main 24-month validation

| Cohort/model | 24m AUC | C-index | Mean predicted 24m risk | Observed KM 24m risk | Brier |
| --- | ---: | ---: | ---: | ---: | ---: |
| OAI apparent | 0.820 | 0.759 | 3.4% | 3.4% | 0.036 |
| MRKR original OAI-derived | 0.709 | 0.681 | 4.4% | 28.0% | 0.328 |
| MRKR slope+baseline recalibrated | 0.709 | 0.681 | 27.8% | 28.0% | 0.246 |
| MRKR offset-only recalibrated | 0.709 | 0.681 | 76.1% | 28.0% | 0.616 |

Interpretation: Model F has moderate transport discrimination in MRKR, but original OAI absolute risk strongly underestimates MRKR hardware-defined arthroplasty risk. Slope+baseline recalibration corrects the calibration-in-the-large and improves Brier score. Offset-only baseline recalibration is not appropriate because the MRKR calibration slope is well below 1.

## MRKR strict cohort sensitivity

| MRKR cohort | Knees | Events | 24m events | C-index | 24m AUC | Observed 24m risk | Calibration slope |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| All MRKR | 3,412 | 1,140 | 855 | 0.681 | 0.709 | 28.0% | 0.681 |
| Exclude events <=3m | 3,084 | 812 | 527 | 0.665 | 0.685 | 20.2% | 0.632 |
| Exclude events <=6m | 2,908 | 636 | 351 | 0.657 | 0.672 | 15.2% | 0.610 |
| Exclude events <=12m | 2,756 | 484 | 199 | 0.659 | 0.667 | 10.0% | 0.615 |

Interpretation: discrimination attenuates after excluding early MRKR events but remains above chance, supporting a transportability signal that is not solely due to imminent surgery or hardware ascertainment.

## Outcome sensitivity

| MRKR outcome | Knees | Events | 24m events | C-index | 24m AUC | Observed 24m risk | Calibration slope |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Hardware primary | 3,412 | 1,140 | 855 | 0.681 | 0.709 | 28.0% | 0.681 |
| CPT patient-level sensitivity | 3,365 | 1,404 | 1,019 | 0.640 | 0.667 | 30.7% | 0.480 |
| Combined hardware or CPT | 3,412 | 1,547 | 1,140 | 0.635 | 0.666 | 33.8% | 0.481 |

CPT-based outcomes show weaker discrimination, probably because CPT events are patient-level and not side-specific. The side-specific hardware outcome should remain the primary MRKR validation endpoint unless side-specific CPT can be recovered.

## MRKR recalibrated 24-month risk strata

| Recalibrated 24m risk group | Knees | 24m events | Mean recalibrated risk | Observed KM 24m risk |
| --- | ---: | ---: | ---: | ---: |
| <10% | 300 | 17 | 6.9% | 6.8% |
| 10-25% | 1,378 | 193 | 17.8% | 16.3% |
| 25-50% | 1,411 | 494 | 35.7% | 38.2% |
| >50% | 323 | 151 | 55.5% | 50.7% |

The recalibrated risk groups show a clinically coherent gradient and acceptable group-level calibration at 24 months.

## Recommended manuscript message

Use OAI Model E as the main internally validated dynamic model. Present MRKR as real-world transport validation of a reduced Model F. The main MRKR result is that the OAI-derived common-variable score retains moderate discrimination, but absolute risks require slope+baseline recalibration because MRKR has different event ascertainment, shorter follow-up, and strong early-event enrichment.

Do not state that MRKR externally validates the full OAI Model E.
