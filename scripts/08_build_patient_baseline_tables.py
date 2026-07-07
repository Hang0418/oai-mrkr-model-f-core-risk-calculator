#!/usr/bin/env python3
"""Create patient-level baseline datasets and Table 1 summaries for OAI/CHECK."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "derived"
BASELINE = DERIVED / "baseline"
RESULTS = ROOT / "results" / "tables"
META = ROOT / "metadata"


def first_nonmissing(series: pd.Series) -> float:
    values = series.dropna()
    return values.iloc[0] if len(values) else np.nan


def side_pivot(
    df: pd.DataFrame,
    id_col: str,
    side_col: str,
    value_cols: list[str],
    prefix: str = "",
) -> pd.DataFrame:
    parts = []
    for value_col in value_cols:
        if value_col not in df.columns:
            continue
        pivot = df.pivot_table(index=id_col, columns=side_col, values=value_col, aggfunc="first")
        pivot.columns = [f"{prefix}{str(side).lower()}_{value_col}" for side in pivot.columns]
        parts.append(pivot)
    if not parts:
        return pd.DataFrame(index=df[id_col].drop_duplicates())
    return pd.concat(parts, axis=1)


def build_oai() -> pd.DataFrame:
    knee = pd.read_csv(DERIVED / "OAI" / "oai_knee_level_first_pass.csv", low_memory=False)
    knee["patient_id"] = knee["id"].astype(str)

    person = (
        knee.groupby("patient_id")
        .agg(
            cohort=("id", lambda _: "OAI"),
            n_knees=("side", "count"),
            baseline_age=("subject_v00age_num", first_nonmissing),
            sex_code=("enrollee_p02sex_num", first_nonmissing),
            baseline_bmi=("clinical00_p01bmi_num", first_nonmissing),
            any_baseline_prior_kr=("exclude_baseline_kr_any", "max"),
            any_kr_event=("outcome_kr_event", "max"),
            first_kr_days=("outcome_kr_days", "min"),
            first_kr_month=("outcome_kr_days", lambda s: s.min() / 30.4375 if s.notna().any() else np.nan),
            max_baseline_womac_pain=("baseline_womac_pain_num", "max"),
            mean_baseline_womac_pain=("baseline_womac_pain_num", "mean"),
            max_baseline_womac_function=("baseline_womac_function_num", "max"),
            mean_baseline_womac_function=("baseline_womac_function_num", "mean"),
            max_baseline_womac_stiffness=("baseline_womac_stiffness_num", "max"),
            mean_baseline_womac_stiffness=("baseline_womac_stiffness_num", "mean"),
            max_baseline_womac_total=("baseline_womac_total_num", "max"),
            mean_baseline_womac_total=("baseline_womac_total_num", "mean"),
            any_knee_pain_past12m=("baseline_knee_pain_past12m_num", "max"),
            any_knee_pain_ever=("baseline_knee_pain_ever_num", "max"),
            max_baseline_screening_kl=("baseline_screening_kl_num", "max"),
            max_xray_kl_grade=("xray_sq_v00xrkl_num", "max"),
            max_screening_jsn_medial=("baseline_screening_jsn_medial_num", "max"),
            max_screening_jsn_lateral=("baseline_screening_jsn_lateral_num", "max"),
        )
        .reset_index()
    )

    side_cols = side_pivot(
        knee,
        id_col="patient_id",
        side_col="side",
        value_cols=[
            "baseline_womac_pain_num",
            "baseline_womac_function_num",
            "baseline_womac_stiffness_num",
            "baseline_womac_total_num",
            "baseline_knee_pain_past12m_num",
            "baseline_screening_kl_num",
            "xray_sq_v00xrkl_num",
            "baseline_screening_jsn_medial_num",
            "baseline_screening_jsn_lateral_num",
            "outcome_kr_event",
            "outcome_kr_days",
        ],
    ).reset_index()
    out = person.merge(side_cols, on="patient_id", how="left")
    return out


def build_check() -> pd.DataFrame:
    knee = pd.read_csv(DERIVED / "CHECK" / "check_knee_level_first_pass.csv", low_memory=False)
    knee["patient_id"] = knee["nsin"].astype(str)

    person = (
        knee.groupby("patient_id")
        .agg(
            cohort=("source_cohort", lambda _: "CHECK"),
            n_knees=("side", "count"),
            baseline_age=("baseline_age", first_nonmissing),
            sex_code=("sex_code", first_nonmissing),
            baseline_bmi=("baseline_bmi", first_nonmissing),
            any_tka_through_t8=("tka_through_t8", "max"),
            first_tka_month=("tka_month", "min"),
            max_baseline_womac_pain=("baseline_womac_pain", "max"),
            mean_baseline_womac_pain=("baseline_womac_pain", "mean"),
            max_baseline_womac_function=("baseline_womac_function", "max"),
            mean_baseline_womac_function=("baseline_womac_function", "mean"),
            max_baseline_womac_stiffness=("baseline_womac_stiffness", "max"),
            mean_baseline_womac_stiffness=("baseline_womac_stiffness", "mean"),
            max_baseline_womac_total=("baseline_womac_total", "max"),
            mean_baseline_womac_total=("baseline_womac_total", "mean"),
            any_knee_pain_flag=("baseline_knee_pain_flag", "max"),
            max_baseline_kl=("kl_t0", "max"),
            max_jsn_medial=("jsn_medial_t0", "max"),
            max_jsn_lateral=("jsn_lateral_t0", "max"),
            any_kl_progression_t0_t5=("kl_progression_t0_t5", "max"),
            any_kl_progression_t0_t8=("kl_progression_t0_t8", "max"),
        )
        .reset_index()
    )

    side_cols = side_pivot(
        knee,
        id_col="patient_id",
        side_col="side",
        value_cols=[
            "baseline_womac_pain",
            "baseline_womac_function",
            "baseline_womac_stiffness",
            "baseline_womac_total",
            "baseline_knee_pain_flag",
            "kl_t0",
            "jsn_medial_t0",
            "jsn_lateral_t0",
            "tka_through_t8",
            "tka_month",
            "kl_progression_t0_t5",
            "kl_progression_t0_t8",
        ],
    ).reset_index()
    out = person.merge(side_cols, on="patient_id", how="left")
    return out


def fmt_cont(series: pd.Series) -> str:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) == 0:
        return "NA"
    q1, median, q3 = s.quantile([0.25, 0.5, 0.75])
    return f"{s.mean():.2f} ({s.std(ddof=1):.2f}); median {median:.2f} [{q1:.2f}, {q3:.2f}]"


def fmt_binary(series: pd.Series) -> str:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) == 0:
        return "NA"
    n = int((s == 1).sum())
    return f"{n} ({n / len(s) * 100:.1f}%)"


def fmt_code_counts(series: pd.Series) -> str:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) == 0:
        return "NA"
    counts = s.value_counts().sort_index()
    total = len(s)
    return "; ".join(f"{int(code)}: {int(n)} ({n / total * 100:.1f}%)" for code, n in counts.items())


def summarize(oai: pd.DataFrame, check: pd.DataFrame) -> pd.DataFrame:
    rows = []
    specs = [
        ("Participants, n", "n", None),
        ("Age, years", "continuous", "baseline_age"),
        ("Sex code, n (%)", "counts", "sex_code"),
        ("BMI, kg/m2", "continuous", "baseline_bmi"),
        ("WOMAC pain, max of knees", "continuous", "max_baseline_womac_pain"),
        ("WOMAC function, max of knees", "continuous", "max_baseline_womac_function"),
        ("WOMAC stiffness, max of knees", "continuous", "max_baseline_womac_stiffness"),
        ("WOMAC total, max of knees", "continuous", "max_baseline_womac_total"),
        ("Any baseline knee pain, n (%)", "binary_any", None),
        ("Baseline KL/structural score, max of knees", "continuous_structural", None),
        ("Any KR/TKA event, n (%)", "binary_event", None),
    ]
    cohorts = {"OAI": oai, "CHECK": check}
    for label, kind, col in specs:
        row = {"characteristic": label}
        for cohort, df in cohorts.items():
            if kind == "n":
                value = str(len(df))
            elif kind == "continuous":
                value = fmt_cont(df[col])
            elif kind == "counts":
                value = fmt_code_counts(df[col])
            elif kind == "binary_any":
                c = "any_knee_pain_past12m" if cohort == "OAI" else "any_knee_pain_flag"
                value = fmt_binary(df[c])
            elif kind == "continuous_structural":
                c = "max_xray_kl_grade" if cohort == "OAI" else "max_baseline_kl"
                value = fmt_cont(df[c])
            elif kind == "binary_event":
                c = "any_kr_event" if cohort == "OAI" else "any_tka_through_t8"
                value = fmt_binary(df[c])
            else:
                value = "NA"
            row[cohort] = value
        rows.append(row)
    return pd.DataFrame(rows)


def harmonize(oai: pd.DataFrame, check: pd.DataFrame) -> pd.DataFrame:
    oai_common = pd.DataFrame(
        {
            "cohort": oai["cohort"],
            "patient_id": oai["patient_id"],
            "n_knees": oai["n_knees"],
            "baseline_age": oai["baseline_age"],
            "sex_code_original": oai["sex_code"],
            "baseline_bmi": oai["baseline_bmi"],
            "max_baseline_womac_pain": oai["max_baseline_womac_pain"],
            "mean_baseline_womac_pain": oai["mean_baseline_womac_pain"],
            "max_baseline_womac_function": oai["max_baseline_womac_function"],
            "mean_baseline_womac_function": oai["mean_baseline_womac_function"],
            "max_baseline_womac_stiffness": oai["max_baseline_womac_stiffness"],
            "mean_baseline_womac_stiffness": oai["mean_baseline_womac_stiffness"],
            "max_baseline_womac_total": oai["max_baseline_womac_total"],
            "mean_baseline_womac_total": oai["mean_baseline_womac_total"],
            "any_baseline_knee_pain": oai["any_knee_pain_past12m"],
            "max_baseline_kl_grade": oai["max_xray_kl_grade"],
            "max_baseline_jsn_medial": oai["max_screening_jsn_medial"],
            "max_baseline_jsn_lateral": oai["max_screening_jsn_lateral"],
            "any_kr_or_tka_event": oai["any_kr_event"],
            "first_event_month": oai["first_kr_month"],
            "event_definition": "OAI KR/TKA outcome",
        }
    )
    check_common = pd.DataFrame(
        {
            "cohort": check["cohort"],
            "patient_id": check["patient_id"],
            "n_knees": check["n_knees"],
            "baseline_age": check["baseline_age"],
            "sex_code_original": check["sex_code"],
            "baseline_bmi": check["baseline_bmi"],
            "max_baseline_womac_pain": check["max_baseline_womac_pain"],
            "mean_baseline_womac_pain": check["mean_baseline_womac_pain"],
            "max_baseline_womac_function": check["max_baseline_womac_function"],
            "mean_baseline_womac_function": check["mean_baseline_womac_function"],
            "max_baseline_womac_stiffness": check["max_baseline_womac_stiffness"],
            "mean_baseline_womac_stiffness": check["mean_baseline_womac_stiffness"],
            "max_baseline_womac_total": check["max_baseline_womac_total"],
            "mean_baseline_womac_total": check["mean_baseline_womac_total"],
            "any_baseline_knee_pain": check["any_knee_pain_flag"],
            "max_baseline_kl_grade": check["max_baseline_kl"],
            "max_baseline_jsn_medial": check["max_jsn_medial"],
            "max_baseline_jsn_lateral": check["max_jsn_lateral"],
            "any_kr_or_tka_event": check["any_tka_through_t8"],
            "first_event_month": check["first_tka_month"],
            "event_definition": "CHECK side-specific TKA through T8",
        }
    )
    return pd.concat([oai_common, check_common], ignore_index=True)


def write_dictionary() -> None:
    rows = [
        ("patient_id", "Patient/participant identifier within each cohort."),
        ("cohort", "Source cohort: OAI or CHECK."),
        ("n_knees", "Number of knee records represented for the patient."),
        ("baseline_age", "Baseline age in years."),
        ("sex_code", "Original cohort-specific sex code; confirm coding before publication."),
        ("baseline_bmi", "Baseline body mass index."),
        ("max_baseline_womac_pain", "Higher/worse baseline WOMAC pain value across knees."),
        ("mean_baseline_womac_pain", "Mean baseline WOMAC pain value across knees."),
        ("max_baseline_womac_function", "Higher/worse baseline WOMAC function value across knees."),
        ("max_baseline_womac_stiffness", "Higher/worse baseline WOMAC stiffness value across knees."),
        ("max_baseline_womac_total", "Higher/worse baseline WOMAC total value across knees."),
        ("any_knee_pain_past12m", "OAI patient-level indicator of any knee pain in the past 12 months."),
        ("any_knee_pain_flag", "CHECK patient-level indicator of any baseline knee pain flag."),
        ("max_xray_kl_grade", "OAI maximum baseline KL grade across knees, where available."),
        ("max_baseline_kl", "CHECK maximum baseline KL grade across knees."),
        ("any_kr_event", "OAI patient-level indicator of any knee replacement event."),
        ("any_tka_through_t8", "CHECK patient-level indicator of any TKA through T8."),
        ("any_kr_or_tka_event", "Harmonized event indicator; outcome definition differs by cohort."),
        ("first_event_month", "Approximate first KR/TKA event month."),
        ("event_definition", "Text description of the cohort-specific event definition."),
        ("left_* / right_*", "Side-specific baseline or outcome variables for the left/right knee."),
    ]
    with (META / "patient_baseline_dictionary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["variable", "description"])
        writer.writerows(rows)


def main() -> None:
    BASELINE.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)

    oai = build_oai()
    check = build_check()
    combined = pd.concat([oai, check], ignore_index=True, sort=False)
    common = harmonize(oai, check)
    table1 = summarize(oai, check)

    oai.to_csv(BASELINE / "oai_patient_baseline.csv", index=False)
    check.to_csv(BASELINE / "check_patient_baseline.csv", index=False)
    combined.to_csv(BASELINE / "combined_patient_baseline.csv", index=False)
    common.to_csv(BASELINE / "combined_patient_baseline_common.csv", index=False)
    table1.to_csv(RESULTS / "patient_baseline_table1.csv", index=False)
    write_dictionary()

    print(f"OAI patient baseline rows: {len(oai):,}")
    print(f"CHECK patient baseline rows: {len(check):,}")
    print(f"Combined patient baseline rows: {len(combined):,}")
    print(f"Common baseline rows: {len(common):,}")
    print(f"Wrote {RESULTS / 'patient_baseline_table1.csv'}")


if __name__ == "__main__":
    main()
