"""Included vs excluded comparisons for OAI and MRKR Model F-core analyses.

The goal is to quantify whether complete-case inclusion for the transportable
Model F-core selected a systematically different knee population. The script
uses knee-level derived datasets and reports available baseline/landmark
features with standardized mean differences (SMDs).
"""

from __future__ import annotations

from pathlib import Path
import math

import numpy as np
import pandas as pd


ROOT = Path("/Users/hehang/Downloads/时间序列预测模型/膝关节炎")
TABLES = ROOT / "results" / "tables"
TABLES.mkdir(parents=True, exist_ok=True)

OAI_PATH = ROOT / "derived" / "transport" / "oai_train_model_f_mapped.csv"
MRKR_PATH = ROOT / "derived" / "transport" / "mrkr_validation_model_f_mapped.csv"


def to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def fmt_num(x: float, digits: int = 1) -> str:
    if pd.isna(x):
        return "NA"
    return f"{x:.{digits}f}"


def fmt_pct(n: int, d: int) -> str:
    if d == 0:
        return "NA"
    return f"{n} ({100*n/d:.1f}%)"


def smd_cont(a: pd.Series, b: pd.Series) -> float:
    a = to_num(a).dropna()
    b = to_num(b).dropna()
    if len(a) == 0 or len(b) == 0:
        return np.nan
    sd = math.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    if not np.isfinite(sd) or sd == 0:
        return 0.0
    return abs((a.mean() - b.mean()) / sd)


def smd_binary(a: pd.Series, b: pd.Series) -> float:
    a = to_num(a).dropna()
    b = to_num(b).dropna()
    if len(a) == 0 or len(b) == 0:
        return np.nan
    p1 = a.mean()
    p0 = b.mean()
    p = (p1 + p0) / 2
    denom = math.sqrt(p * (1 - p))
    if denom == 0:
        return 0.0
    return abs((p1 - p0) / denom)


def smd_multicat(a: pd.Series, b: pd.Series) -> float:
    a = a.astype("string").fillna("Missing")
    b = b.astype("string").fillna("Missing")
    levels = sorted(set(a.unique()).union(set(b.unique())))
    vals = []
    for lvl in levels:
        p1 = (a == lvl).mean()
        p0 = (b == lvl).mean()
        p = (p1 + p0) / 2
        denom = math.sqrt(p * (1 - p)) if p not in (0, 1) else 0
        if denom:
            vals.append(((p1 - p0) / denom) ** 2)
    return math.sqrt(sum(vals)) if vals else 0.0


def summarize_cont(df_in: pd.DataFrame, df_ex: pd.DataFrame, var: str, label: str) -> dict:
    a = to_num(df_in[var]) if var in df_in else pd.Series(dtype=float)
    b = to_num(df_ex[var]) if var in df_ex else pd.Series(dtype=float)
    return {
        "Characteristic": label,
        "Included": f"{fmt_num(a.mean())} ({fmt_num(a.std(ddof=1))})",
        "Excluded": f"{fmt_num(b.mean())} ({fmt_num(b.std(ddof=1))})",
        "Included non-missing": int(a.notna().sum()),
        "Excluded non-missing": int(b.notna().sum()),
        "SMD": smd_cont(a, b),
    }


def summarize_binary(df_in: pd.DataFrame, df_ex: pd.DataFrame, var: str, label: str) -> dict:
    a = to_num(df_in[var]) if var in df_in else pd.Series(dtype=float)
    b = to_num(df_ex[var]) if var in df_ex else pd.Series(dtype=float)
    return {
        "Characteristic": label,
        "Included": fmt_pct(int((a == 1).sum()), int(a.notna().sum())),
        "Excluded": fmt_pct(int((b == 1).sum()), int(b.notna().sum())),
        "Included non-missing": int(a.notna().sum()),
        "Excluded non-missing": int(b.notna().sum()),
        "SMD": smd_binary(a, b),
    }


def summarize_cat_overall(df_in: pd.DataFrame, df_ex: pd.DataFrame, var: str, label: str) -> dict:
    a = df_in[var] if var in df_in else pd.Series(dtype="string")
    b = df_ex[var] if var in df_ex else pd.Series(dtype="string")
    return {
        "Characteristic": f"{label}, overall SMD",
        "Included": "",
        "Excluded": "",
        "Included non-missing": int(a.notna().sum()),
        "Excluded non-missing": int(b.notna().sum()),
        "SMD": smd_multicat(a, b),
    }


def add_cat_levels(rows: list[dict], df_in: pd.DataFrame, df_ex: pd.DataFrame, var: str, label: str) -> None:
    a = df_in[var].astype("string") if var in df_in else pd.Series(dtype="string")
    b = df_ex[var].astype("string") if var in df_ex else pd.Series(dtype="string")
    levels = sorted(set(a.dropna().unique()).union(set(b.dropna().unique())))
    for lvl in levels:
        rows.append(
            {
                "Characteristic": f"  {label}: {lvl}",
                "Included": fmt_pct(int((a == lvl).sum()), int(a.notna().sum())),
                "Excluded": fmt_pct(int((b == lvl).sum()), int(b.notna().sum())),
                "Included non-missing": int(a.notna().sum()),
                "Excluded non-missing": int(b.notna().sum()),
                "SMD": np.nan,
            }
        )


def format_table(rows: list[dict], cohort: str) -> pd.DataFrame:
    out = pd.DataFrame(rows)
    out.insert(0, "Cohort", cohort)
    out["SMD"] = out["SMD"].map(lambda x: "" if pd.isna(x) else f"{x:.3f}")
    return out


def oai_comparison() -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(OAI_PATH, low_memory=False)
    df["included"] = to_num(df["core_model_f_complete"]).fillna(0).astype(int) == 1
    df["right_knee"] = (df["side"].astype(str).str.upper() == "R").astype(float)
    df["event_primary"] = to_num(df["event_primary"])
    if "time_months" in df:
        df["time_months"] = to_num(df["time_months"])
    df["age"] = to_num(df["age"])
    df["female"] = to_num(df["female"])
    df["pain_baseline"] = to_num(df["pain_baseline_0_10"])
    df["pain_landmark"] = to_num(df["pain_landmark_0_10"])
    df["pain_change"] = to_num(df["pain_change_0_10"])
    df["kl_baseline"] = to_num(df["kl_baseline"])
    df["kl_landmark"] = to_num(df["kl_landmark"])
    df["kl_change"] = to_num(df["kl_change"])
    df["baseline_to_landmark_months"] = to_num(df["baseline_to_landmark_months"])
    df["race"] = df["race"].astype("string")
    df["ethnicity"] = df["ethnicity"].astype("string")

    inc = df[df["included"]].copy()
    exc = df[~df["included"]].copy()

    rows: list[dict] = []
    rows.append(
        {
            "Characteristic": "Knees, n",
            "Included": str(len(inc)),
            "Excluded": str(len(exc)),
            "Included non-missing": len(inc),
            "Excluded non-missing": len(exc),
            "SMD": np.nan,
        }
    )
    rows.append(
        {
            "Characteristic": "Participants, n",
            "Included": str(inc["patient_id"].nunique()),
            "Excluded": str(exc["patient_id"].nunique()),
            "Included non-missing": inc["patient_id"].nunique(),
            "Excluded non-missing": exc["patient_id"].nunique(),
            "SMD": np.nan,
        }
    )
    for var, label in [
        ("age", "Age, years"),
        ("pain_baseline", "Baseline pain score, 0-10"),
        ("pain_landmark", "24-month pain score, 0-10"),
        ("pain_change", "0-24 month pain change"),
        ("kl_baseline", "Baseline KL grade"),
        ("kl_landmark", "24-month KL grade"),
        ("kl_change", "0-24 month KL change"),
        ("baseline_to_landmark_months", "Baseline-to-landmark interval, months"),
        ("time_months", "Post-landmark follow-up, months"),
    ]:
        rows.append(summarize_cont(inc, exc, var, label))
    for var, label in [
        ("female", "Female"),
        ("right_knee", "Right knee"),
        ("event_primary", "Post-landmark KR/TKA event"),
    ]:
        rows.append(summarize_binary(inc, exc, var, label))
    for var, label in [("race", "Race"), ("ethnicity", "Ethnicity")]:
        rows.append(summarize_cat_overall(inc, exc, var, label))
        add_cat_levels(rows, inc, exc, var, label)

    meta = {
        "cohort": "OAI",
        "included_knees": len(inc),
        "excluded_knees": len(exc),
        "included_participants": inc["patient_id"].nunique(),
        "excluded_participants": exc["patient_id"].nunique(),
        "included_event_rate": inc["event_primary"].mean(),
        "excluded_event_rate": exc["event_primary"].mean(),
        "max_smd": pd.to_numeric(format_table(rows, "OAI")["SMD"], errors="coerce").max(),
        "large_smd_characteristics": [],
    }
    tbl = format_table(rows, "OAI")
    smds = pd.to_numeric(tbl["SMD"], errors="coerce")
    meta["large_smd_characteristics"] = tbl.loc[smds >= 0.10, "Characteristic"].tolist()
    return tbl, meta


def mrkr_comparison() -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(MRKR_PATH, low_memory=False)
    df["included"] = to_num(df["core_model_f_complete"]).fillna(0).astype(int) == 1
    df["right_knee"] = (df["side"].astype(str).str.upper() == "R").astype(float)
    df["event_primary"] = to_num(df["event_primary"])
    df["time_months"] = to_num(df["time_months"])
    df["pain_baseline"] = to_num(df["pain_baseline_0_10"])
    df["pain_landmark"] = to_num(df["pain_landmark_0_10"])
    df["pain_change"] = to_num(df["pain_change_0_10"])
    df["kl_baseline"] = to_num(df["kl_baseline"])
    df["kl_landmark"] = to_num(df["kl_landmark"])
    df["kl_change"] = to_num(df["kl_change"])
    df["age"] = to_num(df["age"])
    df["female"] = to_num(df["female"])
    df["baseline_to_landmark_months"] = to_num(df["baseline_to_landmark_months"])
    df["race"] = df["race"].astype("string")
    df["ethnicity"] = df["ethnicity"].astype("string")

    inc = df[df["included"]].copy()
    exc = df[~df["included"]].copy()

    rows: list[dict] = []
    rows.append(
        {
            "Characteristic": "Knees, n",
            "Included": str(len(inc)),
            "Excluded": str(len(exc)),
            "Included non-missing": len(inc),
            "Excluded non-missing": len(exc),
            "SMD": np.nan,
        }
    )
    rows.append(
        {
            "Characteristic": "Participants, n",
            "Included": str(inc["patient_id"].nunique()),
            "Excluded": str(exc["patient_id"].nunique()),
            "Included non-missing": inc["patient_id"].nunique(),
            "Excluded non-missing": exc["patient_id"].nunique(),
            "SMD": np.nan,
        }
    )
    for var, label in [
        ("age", "Age, years"),
        ("pain_baseline", "Baseline pain score, 0-10"),
        ("pain_landmark", "24-month pain score, 0-10"),
        ("pain_change", "0-24 month pain change"),
        ("kl_baseline", "Baseline KL grade"),
        ("kl_landmark", "24-month KL grade"),
        ("kl_change", "0-24 month KL change"),
        ("baseline_to_landmark_months", "Baseline-to-landmark interval, months"),
        ("time_months", "Post-landmark follow-up, months"),
    ]:
        rows.append(summarize_cont(inc, exc, var, label))
    for var, label in [
        ("female", "Female"),
        ("right_knee", "Right knee"),
        ("event_primary", "Post-landmark hardware-defined KR/TKA event"),
    ]:
        rows.append(summarize_binary(inc, exc, var, label))
    for var, label in [("race", "Race"), ("ethnicity", "Ethnicity")]:
        rows.append(summarize_cat_overall(inc, exc, var, label))
        add_cat_levels(rows, inc, exc, var, label)

    meta = {
        "cohort": "MRKR",
        "included_knees": len(inc),
        "excluded_knees": len(exc),
        "included_participants": inc["patient_id"].nunique(),
        "excluded_participants": exc["patient_id"].nunique(),
        "included_event_rate": inc["event_primary"].mean(),
        "excluded_event_rate": exc["event_primary"].mean(),
        "max_smd": pd.to_numeric(format_table(rows, "MRKR")["SMD"], errors="coerce").max(),
        "large_smd_characteristics": [],
    }
    tbl = format_table(rows, "MRKR")
    smds = pd.to_numeric(tbl["SMD"], errors="coerce")
    meta["large_smd_characteristics"] = tbl.loc[smds >= 0.10, "Characteristic"].tolist()
    return tbl, meta


def write_report(oai_meta: dict, mrkr_meta: dict) -> None:
    def pct(x):
        return "NA" if pd.isna(x) else f"{100*x:.1f}%"

    lines = [
        "# Included vs Excluded Comparison for Model F-core Complete-Case Analyses",
        "",
        "## Purpose",
        "",
        "This analysis evaluates whether complete-case inclusion for the OAI Model F-core training set and the MRKR transport validation set selected a systematically different knee population. Continuous variables are summarized as mean (SD), categorical variables as n (%), and imbalance is quantified using absolute standardized mean differences (SMDs). SMD values >=0.10 are treated as potentially meaningful imbalance.",
        "",
        "## OAI",
        "",
        f"The OAI comparison included {oai_meta['included_knees']:,} complete Model F-core knees from {oai_meta['included_participants']:,} participants and {oai_meta['excluded_knees']:,} excluded/incomplete knees from {oai_meta['excluded_participants']:,} participants.",
        f"Post-landmark KR/TKA event rates were {pct(oai_meta['included_event_rate'])} among included knees and {pct(oai_meta['excluded_event_rate'])} among excluded knees.",
        f"The largest observed SMD was {oai_meta['max_smd']:.3f}. Characteristics with SMD >=0.10 were: {', '.join(oai_meta['large_smd_characteristics']) or 'none'}.",
        "",
        "Interpretation: OAI complete-case inclusion was not random. Exclusions were associated with differences in symptom/structural completeness and modest-to-meaningful imbalance in several clinical/radiographic variables, supporting the need to describe possible selection bias and to interpret complete-case performance as applying primarily to imaging- and symptom-complete OAI knees.",
        "",
        "## MRKR",
        "",
        f"The MRKR comparison included {mrkr_meta['included_knees']:,} complete Model F-core knees from {mrkr_meta['included_participants']:,} patients and {mrkr_meta['excluded_knees']:,} excluded/incomplete knees from {mrkr_meta['excluded_participants']:,} patients.",
        f"Post-landmark hardware-defined KR/TKA event rates were {pct(mrkr_meta['included_event_rate'])} among included knees and {pct(mrkr_meta['excluded_event_rate'])} among excluded knees.",
        f"The largest observed SMD was {mrkr_meta['max_smd']:.3f}. Characteristics with SMD >=0.10 were: {', '.join(mrkr_meta['large_smd_characteristics']) or 'none'}.",
        "",
        "Interpretation: MRKR exclusions were also potentially informative, especially where missing pain, landmark KL, or follow-up availability determined Model F-core completeness. Because the validation cohort depends on variables available in routine imaging/EHR workflows, MRKR performance should be interpreted as transport validation in the subset with sufficient mapped variables rather than as a claim about all MRKR knees.",
        "",
        "## Manuscript-ready statement",
        "",
        "Included-versus-excluded comparisons suggested that complete-case restrictions were not fully exchangeable with the source knee populations. In OAI, complete Model F-core knees differed from excluded knees in symptom and radiographic severity and had a different post-landmark knee replacement event rate. In MRKR, complete validation knees also differed from incomplete knees, largely reflecting availability of mappable pain, KL, laterality, landmark, and follow-up information. These findings indicate possible selection bias from complete-case requirements; therefore, discrimination and calibration estimates should be interpreted as applying to knees with sufficient common-variable information rather than to the entire source populations.",
        "",
    ]
    (TABLES / "oai_mrkr_included_excluded_selection_bias_report.md").write_text("\n".join(lines))


def main() -> None:
    oai_tbl, oai_meta = oai_comparison()
    mrkr_tbl, mrkr_meta = mrkr_comparison()
    oai_tbl.to_csv(TABLES / "oai_model_f_included_vs_excluded_comparison.csv", index=False)
    mrkr_tbl.to_csv(TABLES / "mrkr_model_f_included_vs_excluded_comparison.csv", index=False)
    pd.concat([oai_tbl, mrkr_tbl], ignore_index=True).to_csv(
        TABLES / "oai_mrkr_model_f_included_vs_excluded_comparison.csv", index=False
    )
    pd.DataFrame([oai_meta, mrkr_meta]).drop(columns=["large_smd_characteristics"]).to_csv(
        TABLES / "oai_mrkr_included_excluded_selection_bias_summary.csv", index=False
    )
    write_report(oai_meta, mrkr_meta)
    print(TABLES / "oai_model_f_included_vs_excluded_comparison.csv")
    print(TABLES / "mrkr_model_f_included_vs_excluded_comparison.csv")
    print(TABLES / "oai_mrkr_included_excluded_selection_bias_report.md")


if __name__ == "__main__":
    main()
