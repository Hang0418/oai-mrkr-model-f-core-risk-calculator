#!/usr/bin/env python3
"""Summarize OAI, MRKR, and CHECK baseline data and time-specific outcome risks.

The OAI and MRKR summaries use the harmonized Model F-core transport schema.
CHECK is summarized from the CHECK-compatible exploratory validation dataset,
and should be interpreted as exploratory because the event count is limited.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path("/Users/hehang/Downloads/时间序列预测模型/膝关节炎")
OUT = ROOT / "results" / "tables"

OAI_CORE = ROOT / "derived" / "transport" / "oai_train_model_f_core.csv"
MRKR_CORE = ROOT / "derived" / "transport" / "mrkr_validation_model_f_core.csv"
CHECK = ROOT / "derived" / "validation" / "check_24m_external_tka_dataset.csv"
OAI_LANDMARK = ROOT / "derived" / "OAI" / "oai_24m_landmark_dataset.csv"


def fmt_n_pct(n: float, denom: float) -> str:
    if pd.isna(n) or pd.isna(denom) or denom == 0:
        return "Not available"
    return f"{int(n)} ({100 * n / denom:.1f}%)"


def fmt_mean_sd(x: pd.Series) -> str:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if x.empty:
        return "Not available"
    return f"{x.mean():.1f} ({x.std(ddof=1):.1f})"


def fmt_median_iqr(x: pd.Series) -> str:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if x.empty:
        return "Not available"
    q1, med, q3 = x.quantile([0.25, 0.50, 0.75])
    return f"{med:.1f} ({q1:.1f}-{q3:.1f})"


def fmt_pct(x: float) -> str:
    if pd.isna(x):
        return "Not available"
    return f"{100 * x:.1f}%"


def km_risk(time: pd.Series, event: pd.Series, horizon: float) -> float:
    """Kaplan-Meier cumulative incidence at horizon for right-censored data."""
    df = pd.DataFrame(
        {
            "time": pd.to_numeric(time, errors="coerce"),
            "event": pd.to_numeric(event, errors="coerce"),
        }
    ).dropna()
    df = df[df["time"] >= 0]
    if df.empty:
        return math.nan

    surv = 1.0
    event_times = sorted(t for t in df.loc[(df["event"] == 1) & (df["time"] <= horizon), "time"].unique())
    for t in event_times:
        at_risk = ((df["time"] >= t)).sum()
        events = ((df["time"] == t) & (df["event"] == 1)).sum()
        if at_risk > 0:
            surv *= 1 - events / at_risk
    return 1 - surv


def raw_count_by_horizon(time: pd.Series, event: pd.Series, horizon: float) -> int:
    t = pd.to_numeric(time, errors="coerce")
    e = pd.to_numeric(event, errors="coerce").fillna(0)
    return int(((e == 1) & (t <= horizon)).sum())


def censored_before_horizon(time: pd.Series, event: pd.Series, horizon: float) -> int:
    t = pd.to_numeric(time, errors="coerce")
    e = pd.to_numeric(event, errors="coerce").fillna(0)
    return int(((e == 0) & (t < horizon)).sum())


def at_risk_at_horizon(time: pd.Series, horizon: float) -> int:
    t = pd.to_numeric(time, errors="coerce")
    return int((t >= horizon).sum())


def kl_distribution(series: pd.Series) -> str:
    x = pd.to_numeric(series, errors="coerce").dropna()
    if x.empty:
        return "Not available"
    counts = x.astype(int).value_counts().sort_index()
    denom = len(x)
    return "; ".join(f"KL {k}: {v} ({100 * v / denom:.1f}%)" for k, v in counts.items())


def enrich_oai_with_bmi(oai_core: pd.DataFrame) -> pd.DataFrame:
    raw = pd.read_csv(
        OAI_LANDMARK,
        usecols=["id", "side", "clinical00_p01bmi_num", "baseline_womac_pain_num", "baseline_womac_function_num"],
    )
    raw["side_core"] = raw["side"].map({"right": "R", "left": "L"}).fillna(raw["side"])
    raw = raw.rename(
        columns={
            "id": "patient_id",
            "clinical00_p01bmi_num": "bmi",
            "baseline_womac_pain_num": "womac_pain_baseline",
            "baseline_womac_function_num": "womac_function_baseline",
        }
    )
    merged = oai_core.merge(raw, left_on=["patient_id", "side"], right_on=["patient_id", "side_core"], how="left")
    if "side_x" in merged.columns:
        merged = merged.rename(columns={"side_x": "side"})
    return merged


def baseline_row(cohort: str, df: pd.DataFrame, schema_note: str) -> dict[str, str]:
    id_col = "patient_id" if "patient_id" in df.columns else "id"
    side_col = "side"
    event_col = "event_primary" if "event_primary" in df.columns else "event"
    time_col = "time_months" if "time_months" in df.columns else "time"

    if cohort == "CHECK":
        pain_landmark = "womac_pain_24m"
        function_landmark = "womac_function_24m"
        kl_landmark = "kl_24m"
        kl_change = "kl_delta_0_24m"
        bmi_col = "bmi"
        right_n = int((df["right_knee"] == 1).sum())
        pain_measure = "WOMAC pain at 24-month landmark"
    else:
        pain_landmark = "pain_landmark_0_10"
        function_landmark = "womac_function_baseline"
        kl_landmark = "kl_landmark"
        kl_change = "kl_change"
        bmi_col = "bmi"
        right_n = int(df[side_col].astype(str).str.upper().isin(["R", "RIGHT"]).sum())
        pain_measure = "Pain score at landmark, 0-10"

    n = len(df)
    events = int(pd.to_numeric(df[event_col], errors="coerce").fillna(0).sum())

    return {
        "Cohort": cohort,
        "Analysis context": schema_note,
        "Knees, n": str(n),
        "Participants/patients, n": str(df[id_col].nunique()),
        "Age, years, mean (SD)": fmt_mean_sd(df["age"]) if "age" in df else "Not available",
        "Female sex, n (%)": fmt_n_pct(pd.to_numeric(df["female"], errors="coerce").fillna(0).sum(), n)
        if "female" in df
        else "Not available",
        "Right knee, n (%)": fmt_n_pct(right_n, n),
        "BMI, kg/m2, mean (SD)": fmt_mean_sd(df[bmi_col]) if bmi_col in df else "Not available",
        "Pain measure used": pain_measure,
        "Pain at landmark, mean (SD)": fmt_mean_sd(df[pain_landmark]) if pain_landmark in df else "Not available",
        "WOMAC function, mean (SD)": fmt_mean_sd(df[function_landmark]) if function_landmark in df else "Not available",
        "KL grade at landmark, mean (SD)": fmt_mean_sd(df[kl_landmark]) if kl_landmark in df else "Not available",
        "KL grade at landmark, distribution": kl_distribution(df[kl_landmark]) if kl_landmark in df else "Not available",
        "0-24 month KL worsening >=1 grade, n (%)": fmt_n_pct((pd.to_numeric(df[kl_change], errors="coerce") >= 1).sum(), df[kl_change].notna().sum())
        if kl_change in df
        else "Not available",
        "Post-landmark TKA/KR events, n (%)": fmt_n_pct(events, n),
        "Follow-up, months, median (IQR)": fmt_median_iqr(df[time_col]),
    }


def outcome_risk_rows(cohort: str, df: pd.DataFrame, outcome: str, horizons: list[int]) -> list[dict[str, object]]:
    id_col = "patient_id" if "patient_id" in df.columns else "id"
    event_col = "event_primary" if "event_primary" in df.columns else "event"
    time_col = "time_months" if "time_months" in df.columns else "time"
    rows = []
    total_events = int(pd.to_numeric(df[event_col], errors="coerce").fillna(0).sum())
    for h in horizons:
        rows.append(
            {
                "Cohort": cohort,
                "Outcome definition": outcome,
                "Horizon, months after landmark": h,
                "Knees, n": len(df),
                "Participants/patients, n": df[id_col].nunique(),
                "Total post-landmark events, n": total_events,
                "Events by horizon, n": raw_count_by_horizon(df[time_col], df[event_col], h),
                "Censored before horizon, n": censored_before_horizon(df[time_col], df[event_col], h),
                "At risk at horizon, n": at_risk_at_horizon(df[time_col], h),
                "Crude cumulative event proportion": fmt_pct(raw_count_by_horizon(df[time_col], df[event_col], h) / len(df)),
                "Observed Kaplan-Meier risk": fmt_pct(km_risk(df[time_col], df[event_col], h)),
            }
        )
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    oai = enrich_oai_with_bmi(pd.read_csv(OAI_CORE))
    mrkr = pd.read_csv(MRKR_CORE)
    check = pd.read_csv(CHECK)

    baseline = pd.DataFrame(
        [
            baseline_row("OAI", oai, "Model F-core development/apparent validation"),
            baseline_row("MRKR", mrkr, "Model F-core transport validation"),
            baseline_row("CHECK", check, "CHECK-compatible common-change exploratory validation"),
        ]
    )

    horizons = [12, 24, 36, 60, 72]
    risk = pd.DataFrame(
        outcome_risk_rows("OAI", oai, "Target-knee KR/TKA after OAI 24-month landmark", horizons)
        + outcome_risk_rows("MRKR", mrkr, "Side-specific hardware-defined arthroplasty after MRKR landmark", horizons)
        + outcome_risk_rows("CHECK", check, "Post-landmark TKA in CHECK exploratory dataset", horizons)
    )

    long_baseline = baseline.melt(id_vars=["Cohort", "Analysis context"], var_name="Characteristic", value_name="Value")
    baseline_path = OUT / "three_cohort_baseline_characteristics.csv"
    risk_path = OUT / "three_cohort_outcome_risk_by_horizon.csv"
    xlsx_path = OUT / "three_cohort_baseline_and_outcome_risk_summary.xlsx"
    note_path = OUT / "three_cohort_baseline_and_outcome_risk_summary.md"

    baseline.to_csv(baseline_path, index=False)
    long_baseline.to_csv(OUT / "three_cohort_baseline_characteristics_long.csv", index=False)
    risk.to_csv(risk_path, index=False)

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        baseline.to_excel(writer, sheet_name="Baseline wide", index=False)
        long_baseline.to_excel(writer, sheet_name="Baseline long", index=False)
        risk.to_excel(writer, sheet_name="Outcome risk", index=False)

    note = [
        "# Three-cohort baseline and outcome-risk summary",
        "",
        "OAI and MRKR are summarized using the harmonized Model F-core transport datasets.",
        "CHECK is summarized using the CHECK-compatible exploratory validation dataset; its event counts are limited and it should not be described as a definitive full Model E external validation.",
        "",
        "Primary outputs:",
        f"- `{baseline_path.name}`",
        f"- `{risk_path.name}`",
        f"- `{xlsx_path.name}`",
        "",
        "Outcome risks are post-landmark cumulative risks. The Kaplan-Meier risk accounts for censoring before each horizon; the crude cumulative event proportion is provided for transparent denominators.",
    ]
    note_path.write_text("\n".join(note) + "\n", encoding="utf-8")

    print(f"Wrote {baseline_path}")
    print(f"Wrote {risk_path}")
    print(f"Wrote {xlsx_path}")
    print(f"Wrote {note_path}")


if __name__ == "__main__":
    main()
