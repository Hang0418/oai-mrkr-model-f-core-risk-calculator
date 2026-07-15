# Model and endpoint notes

## Model E

Model E is the full OAI dynamic model. It combines baseline clinical and radiographic information with 0-24 month symptom and structural changes. It is evaluated internally in OAI and is not transported unchanged to MRKR or CHECK.

## Model F-core

Model F-core is the OAI-derived common-variable transport model using age, sex, knee side, landmark pain, baseline KL grade, and KL worsening. It is applied directly to MRKR before recalibration.

## OAI endpoint

OAI uses recorded post-landmark target-knee replacement with the recorded replacement date.

## MRKR endpoint

The primary MRKR endpoint is first side-specific hardware-positive postoperative imaging after the 24-month landmark. Its image date is an ascertainment time and the right endpoint of a last-negative/first-positive interval, not necessarily the operation date.

The main timing sensitivities use a temporally concordant CPT date within the interval, the interval midpoint, and an interval-censored Weibull model. Early-detection exclusions at 3, 6, and 12 months redefine the risk set.

## Recalibration

The apparent MRKR recalibration coefficient (`gamma = 0.681400186`) multiplies the original OAI linear predictor. This is distinct from the held-out validation calibration slope, whose target is 1 after updating. Absolute risk is updated through the MRKR baseline cumulative hazard.

Offset-only audit variants that were identified as incorrectly implemented are not part of the formal analysis or public result set.
