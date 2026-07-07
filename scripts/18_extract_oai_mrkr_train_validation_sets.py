#!/usr/bin/env python3
"""Extract harmonized OAI training and MRKR validation datasets.

This script creates a common schema for the variables that can be mapped in
both OAI and MRKR. OAI is treated as the model-development/training cohort;
MRKR is treated as the external validation cohort.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "derived"
OUT = DERIVED / "transport"
RESULTS = ROOT / "results" / "tables"


CORE_VARS = [
    "time_months",
    "event_primary",
    "age",
    "female",
    "side_label",
    "pain_landmark_0_10",
    "kl_baseline",
    "kl_change",
]

EXTENDED_VARS = CORE_VARS + ["pain_baseline_0_10", "pain_change_0_10", "kl_landmark"]


def pain_group(x: pd.Series) -> pd.Series:
    return pd.cut(
        x,
        bins=[-np.inf, 0, 3, 6, np.inf],
        labels=["0", "1-3", "4-6", "7-10"],
    )


def yes_no_complete(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    return df[cols].notna().all(axis=1).astype(int)


def load_oai() -> pd.DataFrame:
    path = DERIVED / "OAI" / "oai_24m_landmark_dataset.csv"
    df = pd.read_csv(path)
    df = df.loc[(df["landmark_eligible_24m"].eq(1)) & (df["time_from_landmark_months"].gt(0))].copy()

    out = pd.DataFrame(
        {
            "cohort": "OAI",
            "split": "train",
            "source_dataset": str(path.relative_to(ROOT)),
            "patient_id": df["id"].astype(str),
            "knee_id": "OAI_" + df["id"].astype(str) + "_" + df["side"].astype(str),
            "side": df["side"].map({"right": "R", "left": "L"}),
            "side_label": df["side"],
            "time_months": df["time_from_landmark_months"],
            "event_primary": df["event_after_landmark"],
            "event_primary_definition": "Target-knee KR/TKA after OAI 24-month landmark",
            "event_sensitivity": np.nan,
            "event_sensitivity_definition": np.nan,
            "time_sensitivity_months": np.nan,
            "age": df["subject_v00age_num"],
            "female": np.where(df["enrollee_p02sex_num"].eq(2), 1, np.where(df["enrollee_p02sex_num"].eq(1), 0, np.nan)),
            "sex": df["enrollee_p02sex_raw"],
            "pain_baseline_0_10": df["womac_pain_0m"] / 2,
            "pain_landmark_0_10": df["womac_pain_24m"] / 2,
            "pain_change_0_10": df["womac_pain_delta_0_24m"] / 2,
            "kl_baseline": df["xray_sq_v00xrkl_num"],
            "kl_landmark": df["xray_kl_current_24m"],
            "kl_change": df["xray_kl_delta_0_24m"],
            "baseline_to_landmark_months": 24.0,
            "landmark_window": "scheduled_24m",
            "raw_landmark_complete_flag": df["landmark_complete_core_24m"],
            "race": df.get("enrollee_p02race_raw", np.nan),
            "ethnicity": df.get("enrollee_p02hisp_raw", np.nan),
        }
    )
    out["pain_landmark_group"] = pain_group(out["pain_landmark_0_10"])
    out["core_model_f_complete"] = yes_no_complete(out, CORE_VARS)
    out["extended_common_complete"] = yes_no_complete(out, EXTENDED_VARS)
    return out


def load_mrkr() -> pd.DataFrame:
    path = DERIVED / "MRKR" / "mrkr_transport_knee_dataset.csv"
    df = pd.read_csv(path)
    out = pd.DataFrame(
        {
            "cohort": "MRKR",
            "split": "validation",
            "source_dataset": str(path.relative_to(ROOT)),
            "patient_id": df["empi_anon"].astype(str),
            "knee_id": df["knee_id"],
            "side": df["side"],
            "side_label": df["side_label"],
            "time_months": df["time_hardware_months"],
            "event_primary": df["event_hardware_after_landmark"],
            "event_primary_definition": "Side-specific arthroplasty hardware first observed after MRKR landmark",
            "event_sensitivity": df["cpt_arthroplasty_after_landmark"],
            "event_sensitivity_definition": "Patient-level knee arthroplasty CPT after MRKR landmark; not side-specific",
            "time_sensitivity_months": df["time_cpt_months"],
            "age": df["age"],
            "female": df["female"],
            "sex": df["sex"],
            "pain_baseline_0_10": df["pain_0"],
            "pain_landmark_0_10": df["pain_24"],
            "pain_change_0_10": df["pain_change"],
            "kl_baseline": df["kl_0"],
            "kl_landmark": df["kl_24"],
            "kl_change": df["kl_change"],
            "baseline_to_landmark_months": df["baseline_to_landmark_months"],
            "landmark_window": "closest_to_24m_within_18_36m",
            "raw_landmark_complete_flag": df["model_f_complete"],
            "race": df["race"],
            "ethnicity": df["ethnicity"],
        }
    )
    out["pain_landmark_group"] = pain_group(out["pain_landmark_0_10"])
    out["core_model_f_complete"] = yes_no_complete(out, CORE_VARS) & out["time_months"].gt(0)
    out["extended_common_complete"] = yes_no_complete(out, EXTENDED_VARS) & out["time_months"].gt(0)
    out["core_model_f_complete"] = out["core_model_f_complete"].astype(int)
    out["extended_common_complete"] = out["extended_common_complete"].astype(int)
    return out


def summarize(mapped: pd.DataFrame, core: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cohort, d in mapped.groupby("cohort", sort=False):
        c = core.loc[core["cohort"].eq(cohort)]
        rows.append(
            {
                "cohort": cohort,
                "split": d["split"].iloc[0],
                "mapped_knees": len(d),
                "mapped_patients": d["patient_id"].nunique(),
                "core_complete_knees": len(c),
                "core_complete_patients": c["patient_id"].nunique(),
                "primary_events_core": int(c["event_primary"].sum()),
                "primary_event_rate_core": c["event_primary"].mean(),
                "median_followup_months_core": c["time_months"].median(),
                "median_baseline_to_landmark_months_core": c["baseline_to_landmark_months"].median(),
                "age_mean_core": c["age"].mean(),
                "female_pct_core": c["female"].mean(),
                "pain_landmark_mean_core": c["pain_landmark_0_10"].mean(),
                "kl_baseline_mean_core": c["kl_baseline"].mean(),
                "kl_change_mean_core": c["kl_change"].mean(),
                "extended_complete_knees": int(d["extended_common_complete"].sum()),
            }
        )
    return pd.DataFrame(rows)


def write_dictionary() -> None:
    rows = [
        ("cohort", "OAI or MRKR."),
        ("split", "train for OAI, validation for MRKR."),
        ("patient_id", "De-identified participant or patient identifier, cohort-specific."),
        ("knee_id", "Cohort-specific knee identifier."),
        ("side", "R or L."),
        ("side_label", "right or left."),
        ("time_months", "Time from landmark to primary event or censoring."),
        ("event_primary", "Primary event indicator for the cohort-specific outcome."),
        ("event_primary_definition", "Outcome definition used for the primary training/validation endpoint."),
        ("event_sensitivity", "MRKR patient-level CPT arthroplasty sensitivity outcome; missing for OAI."),
        ("time_sensitivity_months", "Time to sensitivity event or censoring where applicable."),
        ("age", "Age at baseline/landmark proxy used for transport modeling."),
        ("female", "1 female, 0 male."),
        ("pain_baseline_0_10", "Baseline pain mapped to 0-10. OAI WOMAC pain is divided by 2; MRKR uses pain_score."),
        ("pain_landmark_0_10", "Landmark pain mapped to 0-10."),
        ("pain_change_0_10", "Landmark pain minus baseline pain on 0-10 scale."),
        ("pain_landmark_group", "Landmark pain group: 0, 1-3, 4-6, or 7-10."),
        ("kl_baseline", "Baseline Kellgren-Lawrence grade. MRKR uses model-inferred KL."),
        ("kl_landmark", "Landmark KL grade. MRKR uses model-inferred KL."),
        ("kl_change", "Landmark KL minus baseline KL."),
        ("baseline_to_landmark_months", "Observed or scheduled interval between baseline and landmark."),
        ("core_model_f_complete", "Complete for age, sex, side, landmark pain, baseline KL, KL change, time, and primary event."),
        ("extended_common_complete", "Core complete plus baseline pain, pain change, and landmark KL."),
    ]
    pd.DataFrame(rows, columns=["variable", "definition"]).to_csv(
        OUT / "oai_mrkr_common_schema_dictionary.csv", index=False
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    oai = load_oai()
    mrkr = load_mrkr()
    mapped = pd.concat([oai, mrkr], ignore_index=True)
    core = mapped.loc[mapped["core_model_f_complete"].eq(1)].copy()

    oai.to_csv(OUT / "oai_train_model_f_mapped.csv", index=False)
    mrkr.to_csv(OUT / "mrkr_validation_model_f_mapped.csv", index=False)
    core.loc[core["cohort"].eq("OAI")].to_csv(OUT / "oai_train_model_f_core.csv", index=False)
    core.loc[core["cohort"].eq("MRKR")].to_csv(OUT / "mrkr_validation_model_f_core.csv", index=False)
    core.to_csv(OUT / "oai_mrkr_model_f_core_combined.csv", index=False)
    mapped.to_csv(OUT / "oai_mrkr_model_f_mapped_combined.csv", index=False)
    summarize(mapped, core).to_csv(RESULTS / "oai_mrkr_train_validation_dataset_summary.csv", index=False)
    write_dictionary()

    print("Wrote harmonized OAI training and MRKR validation datasets.")
    print(summarize(mapped, core).to_string(index=False))


if __name__ == "__main__":
    main()
