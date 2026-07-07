#!/usr/bin/env python3
"""Build a 24-month OAI landmark dataset for KR/TKA risk prediction."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "derived" / "OAI"
RESULTS = ROOT / "results" / "tables"
RAW_OUTCOMES = ROOT / "raw" / "OAI" / "Outcomes_ASCII" / "OUTCOMES99.txt"
RAW_XRAY_SQ_24M = (
    ROOT
    / "raw"
    / "OAI"
    / "X-Ray Image Assessments_ASCII"
    / "XR Knee Semi-Quant"
    / "kxr_sq_bu03.txt"
)

LANDMARK_MONTH = 24.0
DAYS_PER_MONTH = 30.4375

NUMBER_RE = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)")
MONTH_RE = re.compile(r"(\d+)\s*-\s*month", re.IGNORECASE)
YEAR_RE = re.compile(r"year\s*(\d+)", re.IGNORECASE)


def numeric_code(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if text == "" or text.startswith("."):
        return None
    match = NUMBER_RE.match(text)
    return float(match.group(1)) if match else None


def recent_contact_month(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if text == "" or text.startswith("."):
        return None
    month_match = MONTH_RE.search(text)
    if month_match:
        return float(month_match.group(1))
    year_match = YEAR_RE.search(text)
    if year_match:
        return float(year_match.group(1)) * 12.0
    code = numeric_code(text)
    code_map = {
        0: 0,
        1: 12,
        2: 18,
        3: 24,
        4: 30,
        5: 36,
        6: 48,
        7: 60,
        8: 72,
        9: 84,
        10: 96,
        11: 108,
        12: 120,
        13: 168,
        14: 192,
    }
    return code_map.get(int(code)) if code is not None else None


def read_xray_24m() -> pd.DataFrame:
    xray = pd.read_csv(RAW_XRAY_SQ_24M, sep="|", dtype=str, keep_default_na=False)
    xray["side_code"] = xray["SIDE"].map(numeric_code)
    xray["side"] = xray["side_code"].map({1.0: "right", 2.0: "left"})
    keep = ["ID", "side", "V03XRKL", "V03XRJSM", "V03XRJSL", "V03XROSTM", "V03XROSTL"]
    xray = xray.loc[xray["side"].notna(), [c for c in keep if c in xray.columns]].copy()
    xray = xray.rename(columns={"ID": "id"})
    for col in [c for c in xray.columns if c.startswith("V03")]:
        xray[f"xray_24m_{col.lower()}_num"] = xray[col].map(numeric_code)
    return xray.drop_duplicates(["id", "side"])


def first_nonmissing(series: pd.Series) -> float | None:
    valid = series.dropna()
    if valid.empty:
        return None
    return float(valid.iloc[0])


def build_pain_features(pain: pd.DataFrame) -> pd.DataFrame:
    pain = pain.copy()
    pain = pain.loc[pain["visit_month_approx"].isin([0, 12, 24])].copy()
    pain["knee_id"] = pain["id"].astype(str) + "_" + pain["side"].astype(str)

    wide = pain.pivot_table(
        index=["id", "side", "side_code"],
        columns="visit_month_approx",
        values=["womac_pain", "womac_function", "koos_pain", "koos_function"],
        aggfunc=first_nonmissing,
    )
    wide.columns = [f"{metric}_{int(month)}m" for metric, month in wide.columns]
    wide = wide.reset_index()

    for metric in ["womac_pain", "womac_function", "koos_pain", "koos_function"]:
        base = f"{metric}_0m"
        current = f"{metric}_24m"
        twelve = f"{metric}_12m"
        if base in wide.columns and current in wide.columns:
            wide[f"{metric}_delta_0_24m"] = wide[current] - wide[base]
            wide[f"{metric}_slope_per_year_0_24m"] = wide[f"{metric}_delta_0_24m"] / 2.0
        if base in wide.columns and twelve in wide.columns:
            wide[f"{metric}_delta_0_12m"] = wide[twelve] - wide[base]

    def trajectory(row: pd.Series) -> str:
        base = row.get("womac_pain_0m")
        delta = row.get("womac_pain_delta_0_24m")
        if pd.isna(base) or pd.isna(delta):
            return "missing"
        if base < 4 and delta < 3:
            return "low_stable"
        if delta >= 3:
            return "worsening"
        if base >= 8 and delta > -3:
            return "high_persistent"
        if delta <= -3:
            return "improving"
        return "moderate_stable"

    wide["pain_trajectory_rule_0_24m"] = wide.apply(trajectory, axis=1)
    return wide


def build_landmark() -> pd.DataFrame:
    knee = pd.read_csv(DERIVED / "oai_knee_level_first_pass.csv", dtype={"id": str}, low_memory=False)
    pain = pd.read_csv(DERIVED / "oai_pain_trajectory_long.csv", dtype={"id": str}, low_memory=False)
    outcomes = pd.read_csv(RAW_OUTCOMES, sep="|", dtype=str, keep_default_na=False)
    outcomes = outcomes[["id", "V99RNTCNT"]].copy()
    outcomes["censor_month"] = outcomes["V99RNTCNT"].map(recent_contact_month)

    pain_features = build_pain_features(pain)
    xray_24m = read_xray_24m()

    df = knee.merge(pain_features, on=["id", "side", "side_code"], how="left")
    df = df.merge(outcomes, on="id", how="left")
    df = df.merge(xray_24m, on=["id", "side"], how="left")

    df["event_month"] = df["outcome_kr_days"] / DAYS_PER_MONTH
    df["event_after_landmark"] = (
        (df["outcome_kr_event"] == 1) & (df["event_month"] > LANDMARK_MONTH)
    ).astype(int)
    df["event_before_or_at_landmark"] = (
        (df["outcome_kr_event"] == 1) & (df["event_month"] <= LANDMARK_MONTH)
    ).astype(int)
    df["observed_end_month"] = df["event_month"].where(df["outcome_kr_event"] == 1, df["censor_month"])
    df["time_from_landmark_months"] = df["observed_end_month"] - LANDMARK_MONTH

    df["xray_kl_current_24m"] = df["xray_24m_v03xrkl_num"].combine_first(df["xray_sq_v00xrkl_num"])
    df["xray_jsn_medial_current_24m"] = df["xray_24m_v03xrjsm_num"].combine_first(
        df["xray_sq_v00xrjsm_num"]
    )
    df["xray_jsn_lateral_current_24m"] = df["xray_24m_v03xrjsl_num"].combine_first(
        df["xray_sq_v00xrjsl_num"]
    )
    df["xray_kl_delta_0_24m"] = df["xray_24m_v03xrkl_num"] - df["xray_sq_v00xrkl_num"]
    df["xray_jsn_medial_delta_0_24m"] = df["xray_24m_v03xrjsm_num"] - df["xray_sq_v00xrjsm_num"]

    df["landmark_eligible_24m"] = (
        (df["analysis_eligible_first_pass"] == 1)
        & (df["event_before_or_at_landmark"] == 0)
        & (df["time_from_landmark_months"] > 0)
        & df["womac_pain_24m"].notna()
    ).astype(int)

    df["landmark_complete_core_24m"] = (
        (df["landmark_eligible_24m"] == 1)
        & df["subject_v00age_num"].notna()
        & df["enrollee_p02sex_num"].notna()
        & df["clinical00_p01bmi_num"].notna()
        & df["womac_pain_0m"].notna()
        & df["womac_pain_24m"].notna()
        & df["womac_function_24m"].notna()
        & df["xray_kl_current_24m"].notna()
    ).astype(int)

    return df


def write_summary(df: pd.DataFrame) -> None:
    eligible = df.loc[df["landmark_eligible_24m"] == 1]
    complete = df.loc[df["landmark_complete_core_24m"] == 1]
    rows = [
        ("landmark_month", LANDMARK_MONTH),
        ("knee_rows_total", len(df)),
        ("eligible_24m_landmark_knees", len(eligible)),
        ("eligible_24m_landmark_participants", eligible["id"].nunique()),
        ("events_after_24m_eligible", int(eligible["event_after_landmark"].sum())),
        ("complete_core_24m_knees", len(complete)),
        ("complete_core_24m_participants", complete["id"].nunique()),
        ("events_after_24m_complete_core", int(complete["event_after_landmark"].sum())),
    ]
    pd.DataFrame(rows, columns=["metric", "value"]).to_csv(
        RESULTS / "oai_24m_landmark_summary.csv", index=False
    )

    traj = (
        eligible.groupby("pain_trajectory_rule_0_24m", dropna=False)
        .agg(knees=("id", "size"), participants=("id", "nunique"), events=("event_after_landmark", "sum"))
        .reset_index()
        .sort_values(["events", "knees"], ascending=False)
    )
    traj.to_csv(RESULTS / "oai_24m_landmark_by_pain_trajectory.csv", index=False)


def main() -> None:
    DERIVED.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    df = build_landmark()
    out = DERIVED / "oai_24m_landmark_dataset.csv"
    df.to_csv(out, index=False)
    write_summary(df)
    print(f"Wrote {len(df)} rows to {out}")
    print(f"24m eligible knees: {int(df['landmark_eligible_24m'].sum())}")
    print(f"24m complete core knees: {int(df['landmark_complete_core_24m'].sum())}")
    print(
        "Events after 24m among complete core knees: "
        f"{int(df.loc[df['landmark_complete_core_24m'] == 1, 'event_after_landmark'].sum())}"
    )


if __name__ == "__main__":
    main()
