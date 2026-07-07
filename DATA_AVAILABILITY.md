# Data Availability and Public Release Boundary

## Public Files Included

This release includes:

- aggregate model performance tables;
- aggregate calibration and recalibration tables;
- model coefficients and baseline cumulative hazards;
- public schema dictionaries;
- publication figures;
- analysis scripts;
- the static research-use calculator.

These files are sufficient to inspect the reported formula, reproduce the calculator logic, review aggregate MRKR transport validation results, and regenerate manuscript figures from aggregate outputs.

## Files Intentionally Excluded

The following files are intentionally not included:

- raw OAI source files;
- raw MRKR source files;
- raw CHECK source files;
- row-level OAI analytic datasets;
- row-level MRKR analytic datasets;
- combined row-level transport datasets;
- any file containing patient identifiers, anonymized patient identifiers, dates, image-level records, encounter-level records, CPT line records, or individual-level follow-up rows.

## Rationale

Even when de-identified or anonymized, row-level clinical datasets can remain subject to data-use agreements, institutional governance, or re-identification risk. Public release is therefore limited to aggregate outputs and code. Users who need to reproduce the full pipeline from raw data should obtain the required source datasets and approvals independently, then run the scripts locally.

## Public Data Inventory

Aggregate public data are stored under:

```text
data/aggregate/
data/dictionaries/
```

Restricted or local-only data should remain outside the repository under project directories such as:

```text
raw/
derived/OAI/
derived/MRKR/
derived/transport/
MRKR/tables/
```

