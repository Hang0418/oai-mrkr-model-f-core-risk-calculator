#!/usr/bin/env python3
"""Create MRKR enrichment flags and audit CPT laterality modifiers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "MRKR" / "tables"
DERIVED_MRKR = ROOT / "derived" / "MRKR"
RESULTS = ROOT / "results" / "tables"

KNEE_ARTHROPLASTY_CPT_CODES = {
    "27438",
    "27440",
    "27442",
    "27445",
    "27446",
    "27447",
    "27486",
    "27487",
}


def build_icd_flags() -> pd.DataFrame:
    rows = []
    usecols = ["empi_anon", "date_anon", "knee_osteoarthritis"]
    for chunk in pd.read_csv(TABLES / "MRKR_ICD.csv", usecols=usecols, chunksize=800_000):
        chunk["date_anon"] = pd.to_datetime(chunk["date_anon"], errors="coerce")
        chunk["knee_osteoarthritis"] = pd.to_numeric(chunk["knee_osteoarthritis"], errors="coerce").fillna(0).astype(int)
        pos = chunk.loc[chunk["knee_osteoarthritis"].eq(1), ["empi_anon", "date_anon"]].dropna()
        if not pos.empty:
            rows.append(pos)
    if not rows:
        return pd.DataFrame(columns=["empi_anon", "first_knee_oa_dx_date", "any_knee_oa_dx"])
    dx = pd.concat(rows, ignore_index=True)
    out = dx.groupby("empi_anon", as_index=False)["date_anon"].min()
    out = out.rename(columns={"date_anon": "first_knee_oa_dx_date"})
    out["any_knee_oa_dx"] = 1
    return out


def cpt_laterality_audit() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    usecols = ["empi_anon", "cpt_code", "cpt_group_modifier", "date_anon"]
    for chunk in pd.read_csv(TABLES / "MRKR_CPT.csv", usecols=usecols, dtype={"cpt_code": "string"}, chunksize=800_000):
        arthro = chunk.loc[chunk["cpt_code"].isin(KNEE_ARTHROPLASTY_CPT_CODES)].copy()
        if not arthro.empty:
            rows.append(arthro)
    if not rows:
        empty = pd.DataFrame()
        return empty, empty
    cpt = pd.concat(rows, ignore_index=True)
    cpt["modifier_clean"] = cpt["cpt_group_modifier"].fillna("").astype(str).str.upper().str.strip()
    cpt["modifier_has_left"] = cpt["modifier_clean"].str.contains(r"(^|[^A-Z])LT([^A-Z]|$)|LEFT", regex=True)
    cpt["modifier_has_right"] = cpt["modifier_clean"].str.contains(r"(^|[^A-Z])RT([^A-Z]|$)|RIGHT", regex=True)
    cpt["laterality_from_modifier"] = np.select(
        [cpt["modifier_has_left"] & cpt["modifier_has_right"], cpt["modifier_has_left"], cpt["modifier_has_right"]],
        ["bilateral_or_conflicting", "left", "right"],
        default="not_side_specific",
    )
    summary = (
        cpt.groupby(["cpt_code", "laterality_from_modifier"], as_index=False)
        .agg(rows=("empi_anon", "size"), patients=("empi_anon", "nunique"))
        .sort_values(["cpt_code", "laterality_from_modifier"])
    )
    modifier_counts = (
        cpt.groupby(["cpt_code", "modifier_clean"], as_index=False)
        .agg(rows=("empi_anon", "size"), patients=("empi_anon", "nunique"))
        .sort_values(["cpt_code", "rows"], ascending=[True, False])
    )
    return summary, modifier_counts


def main() -> None:
    DERIVED_MRKR.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    mrkr = pd.read_csv(DERIVED_MRKR / "mrkr_transport_knee_dataset.csv")
    mrkr["landmark_date"] = pd.to_datetime(mrkr["landmark_date"], errors="coerce")
    dx = build_icd_flags()
    out = mrkr.merge(dx, on="empi_anon", how="left")
    out["any_knee_oa_dx"] = out["any_knee_oa_dx"].fillna(0).astype(int)
    out["first_knee_oa_dx_date"] = pd.to_datetime(out["first_knee_oa_dx_date"], errors="coerce")
    out["knee_oa_dx_before_landmark"] = (
        out["any_knee_oa_dx"].eq(1)
        & out["first_knee_oa_dx_date"].notna()
        & out["landmark_date"].notna()
        & out["first_knee_oa_dx_date"].le(out["landmark_date"])
    ).astype(int)
    out["oa_enriched_kl2_or_dx"] = ((out["kl_0"] >= 2) | out["knee_oa_dx_before_landmark"].eq(1)).astype(int)
    out["oa_enriched_kl2"] = (out["kl_0"] >= 2).astype(int)
    out["oa_enriched_pain_present"] = (out["pain_24"] > 0).astype(int)
    out["high_quality_landmark"] = (
        out["baseline_to_landmark_months"].between(18, 30)
        & out["pain_day_distance_24"].notna()
        & out["pain_day_distance_24"].le(90)
        & out["kl_0"].notna()
        & out["kl_24"].notna()
        & out["time_hardware_months"].gt(0)
    ).astype(int)
    out.to_csv(DERIVED_MRKR / "mrkr_transport_knee_dataset_enriched.csv", index=False)

    subgroup_summary = []
    for flag in [
        "model_f_complete",
        "oa_enriched_kl2",
        "knee_oa_dx_before_landmark",
        "oa_enriched_kl2_or_dx",
        "oa_enriched_pain_present",
        "high_quality_landmark",
    ]:
        d = out.loc[out[flag].eq(1)]
        subgroup_summary.append(
            {
                "subgroup": flag,
                "knees": len(d),
                "patients": d["empi_anon"].nunique(),
                "hardware_events": int(d["event_hardware_after_landmark"].sum()),
                "events_by_24m": int(((d["event_hardware_after_landmark"].eq(1)) & (d["time_hardware_months"].le(24))).sum()),
                "median_followup_months": d["time_hardware_months"].median(),
                "pain_24_nonmissing_pct": d["pain_24"].notna().mean(),
            }
        )
    pd.DataFrame(subgroup_summary).to_csv(RESULTS / "mrkr_enrichment_subgroup_counts.csv", index=False)

    cpt_summary, modifier_counts = cpt_laterality_audit()
    cpt_summary.to_csv(RESULTS / "mrkr_cpt_laterality_audit_summary.csv", index=False)
    modifier_counts.to_csv(RESULTS / "mrkr_cpt_laterality_modifier_counts.csv", index=False)

    print("Wrote MRKR enriched dataset and CPT laterality audit.")
    print(pd.DataFrame(subgroup_summary).to_string(index=False))
    if not cpt_summary.empty:
        print(cpt_summary.to_string(index=False))


if __name__ == "__main__":
    main()
