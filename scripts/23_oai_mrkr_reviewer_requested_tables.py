#!/usr/bin/env python3
"""Reviewer-requested cohort flow and Table 1 style summaries for OAI/MRKR."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "derived"
TABLES = ROOT / "results" / "tables"


def fmt_mean_sd(x: pd.Series) -> str:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if x.empty:
        return "NA"
    return f"{x.mean():.1f} ({x.std(ddof=1):.1f})"


def fmt_n_pct(mask: pd.Series, denom: int) -> str:
    n = int(mask.sum())
    pct = 100 * n / denom if denom else np.nan
    return f"{n} ({pct:.1f}%)"


def smd_cont(x1: pd.Series, x2: pd.Series) -> float:
    x1 = pd.to_numeric(x1, errors="coerce").dropna()
    x2 = pd.to_numeric(x2, errors="coerce").dropna()
    if len(x1) < 2 or len(x2) < 2:
        return np.nan
    pooled = np.sqrt((x1.var(ddof=1) + x2.var(ddof=1)) / 2)
    return (x1.mean() - x2.mean()) / pooled if pooled > 0 else np.nan


def smd_binary(p1: float, p2: float) -> float:
    pooled = np.sqrt((p1 * (1 - p1) + p2 * (1 - p2)) / 2)
    return (p1 - p2) / pooled if pooled > 0 else np.nan


def smd_multicat(s1: pd.Series, s2: pd.Series) -> float:
    cats = sorted(set(s1.dropna().astype(str)) | set(s2.dropna().astype(str)))
    if not cats:
        return np.nan
    p1 = np.array([(s1.astype(str) == c).mean() for c in cats])
    p2 = np.array([(s2.astype(str) == c).mean() for c in cats])
    return float(np.sqrt(np.sum((p1 - p2) ** 2)))


def normalize_race(x: object) -> str:
    if pd.isna(x):
        return "Unknown/not reported"
    s = str(x).strip()
    sl = s.lower()
    if sl in {"", "nan", "none", "unknown", "not reported", "missing", ".: missing form/menu"}:
        return "Unknown/not reported"
    if "other" in sl:
        return "Other race"
    if "black" in sl or "african" in sl:
        return "Black"
    if "white" in sl or "caucasian" in sl:
        return "White"
    if "asian" in sl:
        return "Asian"
    if "american indian" in sl or "alaska" in sl:
        return "American Indian/Alaska Native"
    if "native hawaiian" in sl or "pacific" in sl:
        return "Native Hawaiian/Pacific Islander"
    if "more than one" in sl or "multiple" in sl:
        return "More than one race"
    return s


def normalize_ethnicity(x: object) -> str:
    if pd.isna(x):
        return "Unknown/not reported"
    s = str(x).strip()
    sl = s.lower()
    if sl in {"", "nan", "none", "unknown", "not reported", "missing", ".: missing form/menu"}:
        return "Unknown/not reported"
    if sl.startswith("1:") or sl in {"1", "yes"}:
        return "Hispanic/Latino"
    if sl.startswith("0:") or sl in {"0", "no"}:
        return "Not Hispanic/Latino"
    if "hispanic" in sl and "not" not in sl and "non" not in sl:
        return "Hispanic/Latino"
    if "not hispanic" in sl or "non-hispanic" in sl:
        return "Not Hispanic/Latino"
    return s


def kl_group(x: pd.Series) -> pd.Series:
    return pd.to_numeric(x, errors="coerce").map(lambda v: "Missing" if pd.isna(v) else str(int(v)))


def table1() -> pd.DataFrame:
    oai = pd.read_csv(DERIVED / "transport" / "oai_train_model_f_core.csv")
    mrkr = pd.read_csv(DERIVED / "transport" / "mrkr_validation_model_f_core.csv")
    for df in (oai, mrkr):
        df["race_group"] = df["race"].map(normalize_race)
        df["ethnicity_group"] = df["ethnicity"].map(normalize_ethnicity)
        df["kl_group"] = kl_group(df["kl_baseline"])
        df["pain_group"] = pd.cut(
            pd.to_numeric(df["pain_landmark_0_10"], errors="coerce"),
            bins=[-np.inf, 0, 3, 6, np.inf],
            labels=["0", "1-3", "4-6", "7-10"],
        ).astype(str)

    rows: list[dict[str, object]] = []

    def add(label: str, oai_val: str, mrkr_val: str, smd: float | None) -> None:
        rows.append(
            {
                "Characteristic": label,
                "OAI Model F-core (n=3104 knees)": oai_val,
                "MRKR validation (n=3412 knees)": mrkr_val,
                "SMD": "" if smd is None or pd.isna(smd) else f"{abs(smd):.3f}",
            }
        )

    add("Knees, n", f"{len(oai)}", f"{len(mrkr)}", None)
    add("Participants/patients, n", f"{oai['patient_id'].nunique()}", f"{mrkr['patient_id'].nunique()}", None)
    add("Age, years, mean (SD)", fmt_mean_sd(oai["age"]), fmt_mean_sd(mrkr["age"]), smd_cont(oai["age"], mrkr["age"]))
    add("Female sex, n (%)", fmt_n_pct(oai["female"].eq(1), len(oai)), fmt_n_pct(mrkr["female"].eq(1), len(mrkr)), smd_binary(oai["female"].mean(), mrkr["female"].mean()))
    add("Right knee, n (%)", fmt_n_pct(oai["side_label"].eq("right"), len(oai)), fmt_n_pct(mrkr["side_label"].eq("right"), len(mrkr)), smd_binary(oai["side_label"].eq("right").mean(), mrkr["side_label"].eq("right").mean()))
    add("Landmark pain score, 0-10, mean (SD)", fmt_mean_sd(oai["pain_landmark_0_10"]), fmt_mean_sd(mrkr["pain_landmark_0_10"]), smd_cont(oai["pain_landmark_0_10"], mrkr["pain_landmark_0_10"]))
    add("Baseline KL grade, mean (SD)", fmt_mean_sd(oai["kl_baseline"]), fmt_mean_sd(mrkr["kl_baseline"]), smd_cont(oai["kl_baseline"], mrkr["kl_baseline"]))
    add("KL worsening >=1 grade, n (%)", fmt_n_pct(pd.to_numeric(oai["kl_change"], errors="coerce").ge(1), len(oai)), fmt_n_pct(pd.to_numeric(mrkr["kl_change"], errors="coerce").ge(1), len(mrkr)), smd_binary(pd.to_numeric(oai["kl_change"], errors="coerce").ge(1).mean(), pd.to_numeric(mrkr["kl_change"], errors="coerce").ge(1).mean()))
    add("Primary event, n (%)", fmt_n_pct(oai["event_primary"].eq(1), len(oai)), fmt_n_pct(mrkr["event_primary"].eq(1), len(mrkr)), smd_binary(oai["event_primary"].mean(), mrkr["event_primary"].mean()))
    add("Follow-up, months, median (IQR)", f"{oai['time_months'].median():.1f} ({oai['time_months'].quantile(.25):.1f}-{oai['time_months'].quantile(.75):.1f})", f"{mrkr['time_months'].median():.1f} ({mrkr['time_months'].quantile(.25):.1f}-{mrkr['time_months'].quantile(.75):.1f})", None)

    add("Race, overall SMD", "", "", smd_multicat(oai["race_group"], mrkr["race_group"]))
    for cat in ["White", "Black", "Asian", "American Indian/Alaska Native", "Native Hawaiian/Pacific Islander", "More than one race", "Other race", "Unknown/not reported"]:
        add(f"  {cat}", fmt_n_pct(oai["race_group"].eq(cat), len(oai)), fmt_n_pct(mrkr["race_group"].eq(cat), len(mrkr)), None)

    add("Ethnicity, overall SMD", "", "", smd_multicat(oai["ethnicity_group"], mrkr["ethnicity_group"]))
    for cat in ["Hispanic/Latino", "Not Hispanic/Latino", "Unknown/not reported"]:
        add(f"  {cat}", fmt_n_pct(oai["ethnicity_group"].eq(cat), len(oai)), fmt_n_pct(mrkr["ethnicity_group"].eq(cat), len(mrkr)), None)

    add("Baseline KL distribution, overall SMD", "", "", smd_multicat(oai["kl_group"], mrkr["kl_group"]))
    for cat in ["0", "1", "2", "3", "4"]:
        add(f"  KL {cat}", fmt_n_pct(oai["kl_group"].eq(cat), len(oai)), fmt_n_pct(mrkr["kl_group"].eq(cat), len(mrkr)), None)

    return pd.DataFrame(rows)


def flow_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    oai_raw = pd.read_csv(DERIVED / "OAI" / "oai_24m_landmark_dataset.csv", low_memory=False)
    oai_mapped = pd.read_csv(DERIVED / "transport" / "oai_train_model_f_mapped.csv")
    oai_core = pd.read_csv(DERIVED / "transport" / "oai_train_model_f_core.csv")
    oai_e = pd.read_csv(DERIVED / "validation" / "oai_docx_plan_common_complete_dataset.csv")

    start = oai_raw
    first = start[start["analysis_eligible_first_pass"].eq(1)]
    no_pre = first[first["event_before_or_at_landmark"].eq(0)]
    fu = no_pre[no_pre["time_from_landmark_months"].gt(0)]
    pain24 = fu[fu["womac_pain_24m"].notna()]
    core_req_cols = [
        "subject_v00age_num",
        "enrollee_p02sex_num",
        "side",
        "womac_pain_24m",
        "xray_sq_v00xrkl_num",
        "xray_kl_delta_0_24m",
    ]
    core_from_eligible = pain24[pain24[core_req_cols].notna().all(axis=1)]
    oai_rows = [
        ("OAI knee rows assembled", len(start), start["id"].nunique(), ""),
        ("Exclude baseline/prior knee replacement", len(start) - len(first), start.loc[~start.index.isin(first.index), "id"].nunique(), "Baseline or prior KR/TKA flag"),
        ("Exclude target-knee KR/TKA before or at 24-month landmark", len(first) - len(no_pre), first.loc[~first.index.isin(no_pre.index), "id"].nunique(), ""),
        ("Exclude no post-landmark follow-up", len(no_pre) - len(fu), no_pre.loc[~no_pre.index.isin(fu.index), "id"].nunique(), "time_from_landmark_months <= 0 or missing"),
        ("Exclude missing 24-month pain", len(fu) - len(pain24), fu.loc[~fu.index.isin(pain24.index), "id"].nunique(), "Needed for landmark eligibility"),
        ("Exclude missing Model F-core predictors", len(pain24) - len(core_from_eligible), pain24.loc[~pain24.index.isin(core_from_eligible.index), "id"].nunique(), "Age, sex, side, landmark pain, baseline KL, or KL change"),
        ("OAI Model F-core training set", len(oai_core), oai_core["patient_id"].nunique(), f"Events={int(oai_core['event_primary'].sum())}"),
        ("OAI Model E common-complete set", len(oai_e), oai_e["id"].nunique(), f"Events={int(oai_e['event'].sum())}; complete symptoms, KL, JSN, BMI"),
    ]
    oai_flow = pd.DataFrame(oai_rows, columns=["Step", "Knees", "Participants/patients", "Reason/detail"])

    mrkr_all = pd.read_csv(DERIVED / "MRKR" / "mrkr_transport_knee_dataset.csv")
    mrkr_mapped = pd.read_csv(DERIVED / "transport" / "mrkr_validation_model_f_mapped.csv")
    mrkr_core = pd.read_csv(DERIVED / "transport" / "mrkr_validation_model_f_core.csv")
    df = mrkr_all.copy()
    with_fu = df[pd.to_numeric(df["time_hardware_months"], errors="coerce").gt(0)]
    with_side = with_fu[with_fu["side"].isin(["L", "R"])]
    with_pain = with_side[with_side["pain_24"].notna()]
    with_kl = with_pain[with_pain[["kl_0", "kl_24", "kl_change"]].notna().all(axis=1)]
    with_demo = with_kl[with_kl[["age", "female"]].notna().all(axis=1)]
    mrkr_rows = [
        ("MRKR knee-level baseline-landmark pairs assembled", len(df), df["empi_anon"].nunique(), "Derived from side-specific radiographs with no hardware at baseline"),
        ("Exclude no positive hardware follow-up", len(df) - len(with_fu), df.loc[~df.index.isin(with_fu.index), "empi_anon"].nunique(), "time_hardware_months <= 0 or missing"),
        ("Exclude missing/ambiguous laterality", len(with_fu) - len(with_side), with_fu.loc[~with_fu.index.isin(with_side.index), "empi_anon"].nunique(), ""),
        ("Exclude missing landmark pain", len(with_side) - len(with_pain), with_side.loc[~with_side.index.isin(with_pain.index), "empi_anon"].nunique(), "Nearest knee pain score required"),
        ("Exclude missing baseline/landmark KL or KL change", len(with_pain) - len(with_kl), with_pain.loc[~with_pain.index.isin(with_kl.index), "empi_anon"].nunique(), "Model-inferred KL needed"),
        ("Exclude missing age/sex", len(with_kl) - len(with_demo), with_kl.loc[~with_kl.index.isin(with_demo.index), "empi_anon"].nunique(), ""),
        ("MRKR Model F-core validation set", len(mrkr_core), mrkr_core["patient_id"].nunique(), f"Hardware events={int(mrkr_core['event_primary'].sum())}"),
    ]
    mrkr_flow = pd.DataFrame(mrkr_rows, columns=["Step", "Knees", "Participants/patients", "Reason/detail"])
    return oai_flow, mrkr_flow


def missingness_summary() -> pd.DataFrame:
    rows = []
    for cohort, path in [
        ("OAI mapped", DERIVED / "transport" / "oai_train_model_f_mapped.csv"),
        ("MRKR mapped", DERIVED / "transport" / "mrkr_validation_model_f_mapped.csv"),
    ]:
        df = pd.read_csv(path)
        for col in ["age", "female", "side_label", "pain_landmark_0_10", "pain_baseline_0_10", "kl_baseline", "kl_landmark", "kl_change", "time_months"]:
            rows.append(
                {
                    "cohort": cohort,
                    "variable": col,
                    "n": len(df),
                    "missing_n": int(df[col].isna().sum()),
                    "missing_pct": df[col].isna().mean(),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    table1().to_csv(TABLES / "oai_mrkr_reviewer_table1_baseline_smd.csv", index=False)
    oai_flow, mrkr_flow = flow_tables()
    oai_flow.to_csv(TABLES / "oai_reviewer_inclusion_exclusion_flow.csv", index=False)
    mrkr_flow.to_csv(TABLES / "mrkr_reviewer_inclusion_exclusion_flow.csv", index=False)
    missingness_summary().to_csv(TABLES / "oai_mrkr_reviewer_missingness_summary.csv", index=False)
    print("Wrote reviewer-requested flow, Table 1, and missingness summaries.")


if __name__ == "__main__":
    main()
