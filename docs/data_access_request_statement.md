# OAI / MOST Data Access Request Statement

## Project Title
Longitudinal pain trajectories and imaging structural features for predicting total knee arthroplasty risk in knee osteoarthritis: model development in OAI and external validation in MOST.

## Research Purpose
This project aims to develop and externally validate longitudinal prediction models for clinically important outcomes in knee osteoarthritis. The Osteoarthritis Initiative (OAI) will be used as the model development cohort, and the Multicenter Osteoarthritis Study (MOST) will be used as an independent external validation cohort. The primary outcome is incident target-knee total knee arthroplasty or knee replacement during follow-up. Secondary outcomes include radiographic progression, joint space narrowing progression, worsening pain, and functional decline.

## Requested Data
For OAI, the requested data include tabular clinical data, questionnaire and patient-reported outcome measures, WOMAC/KOOS variables, knee injury and surgery variables, medication and treatment variables, TKA/KR outcome files, X-ray semi-quantitative assessments including KL grade and JSN, data dictionaries, variable descriptions, and release notes. Raw MRI or DICOM images are not requested for the first-stage analysis unless required later for an approved extension.

For MOST, the requested materials include study datasets, data dictionaries, dataset descriptions, measurement lists, variable guides, outcome files, TKA/KR variables, knee X-ray scoring variables, and related documentation. Raw image files are not requested for the first-stage analysis unless required later for an approved extension.

## Analysis Plan
The analysis unit will be the knee level, with person-level sensitivity analyses. Longitudinal pain and function measurements will be harmonized across visits and converted so that higher values represent worse symptoms or function. OAI and MOST visits will be aligned using landmark windows, with OAI baseline plus 24 months used for model development and MOST baseline plus 30 months used for external validation. Latent class mixed models or group-based trajectory models will be used to identify pain trajectory classes. Cox proportional hazards models, random survival forests, and gradient boosting survival models will be compared for TKA/KR risk prediction. Model performance will be assessed using C-index, time-dependent AUROC, Brier score, calibration curves, and decision curve analysis.

## Data Security and Use
All downloaded data will be stored in a secure local research directory with raw data preserved unchanged. Data will be used only for non-commercial scientific research and educational purposes. No attempt will be made to re-identify participants. Results will be reported only in aggregate form, following all applicable data use terms and citation requirements.
