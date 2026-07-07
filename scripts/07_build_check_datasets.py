#!/usr/bin/env python3
"""Build first-pass CHECK knee-level and longitudinal datasets.

CHECK is used here as an external validation/transportability cohort for the
OAI knee osteoarthritis prediction project. The outputs are intentionally
plain CSV files so downstream R/Python modeling scripts can use them directly.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "CHECK"
DERIVED = ROOT / "derived" / "CHECK"
META = ROOT / "metadata" / "CHECK"
RESULTS = ROOT / "results" / "tables"

CLINICAL_FILES = {
    0: RAW / "CHECK_T0_DANS_ENG_20161128.tab",
    1: RAW / "CHECK_T1_DANS_ENG_20151207.DTA",
    2: RAW / "CHECK_T2_DANS_ENG_20151209.DTA",
    3: RAW / "CHECK_T3_DANS_ENG_20151207.DTA",
    4: RAW / "CHECK_T4_DANS_ENG_20151207.DTA",
    5: RAW / "CHECK_T5_DANS_ENG_20151209.DTA",
    6: RAW / "CHECK_T6_DANS_ENG_20151207.DTA",
    7: RAW / "CHECK_T7_DANS_ENG_20151207.DTA",
    8: RAW / "CHECK_T8_DANS_ENG_20151207.DTA",
}

RADIOGRAPHIC_FILE = RAW / "Rontgen_opT10_20191118.dta"
RADIOGRAPHIC_VISITS = {0: 0, 2: 24, 5: 60, 8: 96, 10: 120}
SIDES = {
    "left": {"suffix": "L", "radio": "li", "label": "Left"},
    "right": {"suffix": "R", "radio": "re", "label": "Right"},
}


def normalize_id(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    text = text.lstrip("0")
    return text or "0"


def to_numeric(value: object) -> float:
    if pd.isna(value):
        return np.nan
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "na", "tkr", "-99", "-99.0"}:
        return np.nan
    try:
        return float(text)
    except ValueError:
        return np.nan


def yes_no(value: object) -> float:
    num = to_numeric(value)
    if pd.isna(num):
        return np.nan
    if num == 1:
        return 1.0
    if num in {0, 2}:
        return 0.0
    return np.nan


def read_clinical(visit: int, path: Path) -> pd.DataFrame:
    if visit == 0:
        df = pd.read_csv(path, sep="\t", dtype=str, low_memory=False)
    else:
        df = pd.read_stata(path, convert_categoricals=False, preserve_dtypes=False)
    df = df.copy()
    df["nsin_norm"] = df["nsin"].map(normalize_id)
    return df


def col_value(row: pd.Series, column: str) -> object:
    if column not in row.index:
        return np.nan
    return row[column]


def first_nonmissing(values: list[object]) -> float:
    for value in values:
        num = to_numeric(value)
        if not pd.isna(num):
            return num
    return np.nan


def tka_event(clinical_by_visit: dict[int, pd.DataFrame], nsin: str, side_suffix: str) -> dict[str, object]:
    first_visit = np.nan
    first_report_visit = np.nan
    flag_seen = 0
    for visit in range(1, 9):
        df = clinical_by_visit.get(visit)
        if df is None or nsin not in df.index:
            continue
        row = df.loc[nsin]
        flag = yes_no(col_value(row, f"T{visit}_TKA{side_suffix}"))
        reported_visit = to_numeric(col_value(row, f"T{visit}_TKA{side_suffix}_VISIT"))
        if flag == 1 or not pd.isna(reported_visit):
            flag_seen = 1
            first_report_visit = visit
            first_visit = reported_visit if not pd.isna(reported_visit) else float(visit)
            break
    return {
        "tka_through_t8": flag_seen,
        "tka_visit": first_visit,
        "tka_month": first_visit * 12 if not pd.isna(first_visit) else np.nan,
        "tka_reported_at_visit": first_report_visit,
        "early_tka_by_24m": int(flag_seen == 1 and not pd.isna(first_visit) and first_visit <= 2),
    }


def progression(start: object, end: object) -> float:
    start_num = to_numeric(start)
    end_num = to_numeric(end)
    if pd.isna(start_num) or pd.isna(end_num):
        return np.nan
    return float((end_num - start_num) >= 1)


def build_knee_level(clinical_by_visit: dict[int, pd.DataFrame], radiographic: pd.DataFrame) -> pd.DataFrame:
    t0 = clinical_by_visit[0]
    rows: list[dict[str, object]] = []

    for nsin, t0_row in t0.iterrows():
        radio_row = radiographic.loc[nsin] if nsin in radiographic.index else pd.Series(dtype=object)
        for side, spec in SIDES.items():
            row: dict[str, object] = {
                "source_cohort": "CHECK",
                "nsin": nsin,
                "knee_id": f"CHECK_{nsin}_{side}",
                "side": side,
                "side_label": spec["label"],
                "baseline_age": to_numeric(col_value(t0_row, "T0_Lft_T0")),
                "sex_code": to_numeric(col_value(t0_row, "T0_SEXE")),
                "baseline_bmi": to_numeric(col_value(t0_row, "T0_BMI")),
                "baseline_eq5d_pain": to_numeric(col_value(t0_row, "T0_pain")),
                "baseline_womac_pain": to_numeric(col_value(t0_row, "T0_wmpyn")),
                "baseline_womac_stiffness": to_numeric(col_value(t0_row, "T0_wmstf")),
                "baseline_womac_function": to_numeric(col_value(t0_row, "T0_wmfun")),
                "baseline_womac_total": to_numeric(col_value(t0_row, "T0_wmtot")),
                "baseline_womac_pain_std": to_numeric(col_value(t0_row, "T0_wmpyns")),
                "baseline_womac_function_std": to_numeric(col_value(t0_row, "T0_wmfuns")),
                "baseline_knee_pain_flag": yes_no(col_value(t0_row, f"T0_JVKPIJN{spec['suffix']}")),
            }

            radio_suffix = spec["radio"]
            for visit, month in RADIOGRAPHIC_VISITS.items():
                prefix = f"T{visit}_K"
                row[f"kl_t{visit}"] = to_numeric(col_value(radio_row, f"{prefix}_KL_{radio_suffix}_def"))
                row[f"jsn_medial_t{visit}"] = to_numeric(col_value(radio_row, f"{prefix}_JSN_{radio_suffix}_med"))
                row[f"jsn_lateral_t{visit}"] = to_numeric(col_value(radio_row, f"{prefix}_JSN_{radio_suffix}_lat"))
                row[f"radiograph_month_t{visit}"] = month

            for end_visit in (2, 5, 8, 10):
                row[f"kl_progression_t0_t{end_visit}"] = progression(row["kl_t0"], row[f"kl_t{end_visit}"])
                row[f"medial_jsn_progression_t0_t{end_visit}"] = progression(
                    row["jsn_medial_t0"], row[f"jsn_medial_t{end_visit}"]
                )
                row[f"lateral_jsn_progression_t0_t{end_visit}"] = progression(
                    row["jsn_lateral_t0"], row[f"jsn_lateral_t{end_visit}"]
                )

            row.update(tka_event(clinical_by_visit, nsin, spec["suffix"]))
            rows.append(row)

    return pd.DataFrame(rows)


def build_longitudinal(clinical_by_visit: dict[int, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for visit, df in clinical_by_visit.items():
        for nsin, row in df.iterrows():
            for side, spec in SIDES.items():
                pain_col = f"T0_JVKPIJN{spec['suffix']}" if visit == 0 else f"T{visit}_KPIJN{spec['suffix']}"
                rows.append(
                    {
                        "source_cohort": "CHECK",
                        "nsin": nsin,
                        "knee_id": f"CHECK_{nsin}_{side}",
                        "side": side,
                        "visit": visit,
                        "month": visit * 12,
                        "age_at_baseline": to_numeric(col_value(row, f"T{visit}_Lft_T0")),
                        "sex_code": to_numeric(col_value(row, f"T{visit}_SEXE")),
                        "bmi": to_numeric(col_value(row, f"T{visit}_BMI")),
                        "eq5d_pain": to_numeric(col_value(row, f"T{visit}_pain")),
                        "womac_pain": to_numeric(col_value(row, f"T{visit}_wmpyn")),
                        "womac_stiffness": to_numeric(col_value(row, f"T{visit}_wmstf")),
                        "womac_function": to_numeric(col_value(row, f"T{visit}_wmfun")),
                        "womac_total": to_numeric(col_value(row, f"T{visit}_wmtot")),
                        "womac_pain_std": to_numeric(col_value(row, f"T{visit}_wmpyns")),
                        "womac_function_std": to_numeric(col_value(row, f"T{visit}_wmfuns")),
                        "knee_pain_flag": yes_no(col_value(row, pain_col)),
                    }
                )
    return pd.DataFrame(rows)


def write_dictionary(columns: list[str]) -> None:
    descriptions = {
        "knee_id": "Unique CHECK knee identifier combining cohort, participant ID, and side.",
        "baseline_age": "Age at CHECK baseline.",
        "sex_code": "Original CHECK sex code; inspect source documentation before recoding for publication.",
        "baseline_bmi": "Body mass index at CHECK baseline.",
        "baseline_womac_pain": "Baseline WOMAC pain score.",
        "baseline_knee_pain_flag": "Side-specific clinical knee pain flag at baseline, normalized to 1=yes, 0=no.",
        "kl_t0": "Kellgren-Lawrence grade for the indexed knee at baseline.",
        "tka_through_t8": "Total knee arthroplasty reported through CHECK T8, side-specific.",
        "tka_month": "Approximate TKA month, using annual CHECK visit number times 12.",
    }
    META.mkdir(parents=True, exist_ok=True)
    with (META / "check_knee_dataset_dictionary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["variable", "description"])
        writer.writeheader()
        for col in columns:
            writer.writerow({"variable": col, "description": descriptions.get(col, "")})


def summarize(knee: pd.DataFrame, long_df: pd.DataFrame) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    summary = pd.DataFrame(
        [
            {"metric": "participants", "value": knee["nsin"].nunique()},
            {"metric": "knees", "value": len(knee)},
            {"metric": "knees_with_baseline_kl", "value": int(knee["kl_t0"].notna().sum())},
            {"metric": "tka_events_through_t8", "value": int(knee["tka_through_t8"].sum())},
            {"metric": "kl_progression_t0_t5", "value": int(knee["kl_progression_t0_t5"].sum(skipna=True))},
            {"metric": "kl_progression_t0_t8", "value": int(knee["kl_progression_t0_t8"].sum(skipna=True))},
            {"metric": "longitudinal_rows", "value": len(long_df)},
        ]
    )
    summary.to_csv(RESULTS / "check_dataset_summary.csv", index=False)

    by_side = (
        knee.groupby("side", dropna=False)
        .agg(
            knees=("knee_id", "count"),
            tka_events=("tka_through_t8", "sum"),
            baseline_kl_available=("kl_t0", lambda s: int(s.notna().sum())),
            kl_progression_t0_t5=("kl_progression_t0_t5", "sum"),
            kl_progression_t0_t8=("kl_progression_t0_t8", "sum"),
        )
        .reset_index()
    )
    by_side.to_csv(RESULTS / "check_knee_dataset_by_side.csv", index=False)

    pain_summary = (
        long_df.groupby("visit", dropna=False)
        .agg(
            rows=("knee_id", "count"),
            knees_with_pain_flag=("knee_pain_flag", lambda s: int(s.notna().sum())),
            mean_womac_pain=("womac_pain", "mean"),
            mean_womac_function=("womac_function", "mean"),
            mean_bmi=("bmi", "mean"),
        )
        .reset_index()
    )
    pain_summary.to_csv(RESULTS / "check_pain_trajectory_summary.csv", index=False)


def main() -> None:
    DERIVED.mkdir(parents=True, exist_ok=True)
    clinical_by_visit = {visit: read_clinical(visit, path) for visit, path in CLINICAL_FILES.items()}
    clinical_by_visit = {visit: df.set_index("nsin_norm", drop=False) for visit, df in clinical_by_visit.items()}
    radiographic = pd.read_stata(RADIOGRAPHIC_FILE, convert_categoricals=False, preserve_dtypes=False)
    radiographic["nsin_norm"] = radiographic["nsin"].map(normalize_id)
    radiographic = radiographic.set_index("nsin_norm", drop=False)

    knee = build_knee_level(clinical_by_visit, radiographic)
    long_df = build_longitudinal(clinical_by_visit)

    knee.to_csv(DERIVED / "check_knee_level_first_pass.csv", index=False)
    long_df.to_csv(DERIVED / "check_pain_trajectory_long.csv", index=False)
    write_dictionary(list(knee.columns))
    summarize(knee, long_df)

    print(f"CHECK knee-level rows: {len(knee):,}")
    print(f"CHECK participants: {knee['nsin'].nunique():,}")
    print(f"CHECK TKA events through T8: {int(knee['tka_through_t8'].sum()):,}")
    print(f"CHECK longitudinal rows: {len(long_df):,}")


if __name__ == "__main__":
    main()
