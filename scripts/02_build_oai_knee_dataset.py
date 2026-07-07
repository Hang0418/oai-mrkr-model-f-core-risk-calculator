#!/usr/bin/env python3
"""Build an initial OAI knee-level analytic dataset.

The output is a reproducible first-pass dataset for the TKA/KR prediction
workflow. It keeps selected raw fields and creates standardized numeric
versions where OAI stores values as "code: label" strings.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "OAI"
DERIVED = ROOT / "derived" / "OAI"
META = ROOT / "metadata" / "OAI"
RESULTS = ROOT / "results" / "tables"


FILES = {
    "enrollees": RAW / "General_ASCII" / "Enrollees.txt",
    "subject": RAW / "General_ASCII" / "SubjectChar00.txt",
    "clinical00": RAW / "AllClinical_ASCII" / "AllClinical00.txt",
    "outcomes": RAW / "Outcomes_ASCII" / "OUTCOMES99.txt",
    "xray_sq": RAW
    / "X-Ray Image Assessments_ASCII"
    / "XR Knee Semi-Quant"
    / "KXR_SQ_BU00.txt",
    "xray_jsw": RAW
    / "X-Ray Image Assessments_ASCII"
    / "XR Knee Quant JSW"
    / "kxr_qjsw_duryea00.txt",
}


SIDE_SPECS = {
    "right": {
        "side_code": 1,
        "side_label": "Right",
        "outcome_prefix": "V99ERK",
        "pain": {
            "knee_pain_ever": "P01KPNREV",
            "knee_pain_past12m": "P01KPNR12",
            "womac_pain": "V00WOMKPR",
            "womac_function": "V00WOMADLR",
            "womac_stiffness": "V00WOMSTFR",
            "womac_total": "V00WOMTSR",
            "koos_pain": "V00KOOSKPR",
            "koos_symptom": "V00KOOSYMR",
            "koos_function": "V00KOOSFSR",
            "pain_frequency": "V00RPWKTYP",
            "pain_past30d": "V00RPWKPRV",
        },
        "injury": {
            "prior_knee_injury": "P01INJR",
            "prior_knee_surgery": "P01KSURGR",
            "prior_meniscus_injury": "P01MENRINJ",
            "prior_arthroscopy_injury": "P01ARTRINJ",
            "other_knee_surgery": "P01OTSURGR",
        },
        "baseline_kr": {
            "prior_partial_or_total_kr": "P01PMRKRCV",
            "prior_kr_surgery": "P01KRSR",
            "eligible_prior_kr": "V00EKRSR",
            "past7d_kr": "V00P7RKRCV",
        },
        "subject_xray": {
            "screening_xray_koa": "P01RXRKOA",
            "screening_xray_koa_alt": "P01RXRKOA2",
            "screening_kl": "P01SVXRRKR",
            "screening_jsn_lateral": "P01SVRKJSL",
            "screening_jsn_medial": "P01SVRKJSM",
            "screening_osteophyte": "P01SVRKOST",
        },
    },
    "left": {
        "side_code": 2,
        "side_label": "Left",
        "outcome_prefix": "V99ELK",
        "pain": {
            "knee_pain_ever": "P01KPNLEV",
            "knee_pain_past12m": "P01KPNL12",
            "womac_pain": "V00WOMKPL",
            "womac_function": "V00WOMADLL",
            "womac_stiffness": "V00WOMSTFL",
            "womac_total": "V00WOMTSL",
            "koos_pain": "V00KOOSKPL",
            "koos_symptom": "V00KOOSYML",
            "koos_function": "V00KOOSFSL",
            "pain_frequency": "V00LPWKTYP",
            "pain_past30d": "V00LPWKPRV",
        },
        "injury": {
            "prior_knee_injury": "P01INJL",
            "prior_knee_surgery": "P01KSURGL",
            "prior_meniscus_injury": "P01MENLINJ",
            "prior_arthroscopy_injury": "P01ARTLINJ",
            "other_knee_surgery": "P01OTSURGL",
        },
        "baseline_kr": {
            "prior_partial_or_total_kr": "P01PMLKRCV",
            "prior_kr_surgery": "P01KRSL",
            "eligible_prior_kr": "V00EKRSL",
            "past7d_kr": "V00P7LKRCV",
        },
        "subject_xray": {
            "screening_xray_koa": "P01LXRKOA",
            "screening_xray_koa_alt": "P01LXRKOA2",
            "screening_kl": "P01SVXRLKR",
            "screening_jsn_lateral": "P01SVLKJSL",
            "screening_jsn_medial": "P01SVLKJSM",
            "screening_osteophyte": "P01SVLKOST",
        },
    },
}


PERSON_VARS = {
    "enrollees": [
        "P02HISP",
        "P02RACE",
        "P02SEX",
        "V00CHRTHLF",
        "V00COHORT",
        "V00SITE",
    ],
    "subject": [
        "V00AGE",
        "V00EDCV",
        "V00INCOME",
        "V00INCOME2",
        "V00PASE",
        "V00MEDINS",
        "P02ACTRISK",
        "P02ELGRISK",
        "P02IKPRISK",
        "P02KRS3",
        "P02STMED",
        "P02WTGA",
    ],
    "clinical00": [
        "P01HEIGHT",
        "P01WEIGHT",
        "P01BMI",
        "V00AGE",
        "V00NSAIDS",
        "V00NSAIDRX",
        "V00RXANALG",
        "V00RXCOX2",
        "V00RXNARC",
        "V00KPMED",
        "P01KPMED",
        "P02KPMED",
    ],
}


MISSING_PREFIXES = (".", ".:")
NUMBER_RE = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)")


def read_oai(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="|", dtype=str, keep_default_na=False)


def value_or_blank(row: pd.Series, column: str) -> str:
    if column not in row.index:
        return ""
    value = row[column]
    return "" if pd.isna(value) else str(value)


def numeric_code(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if text == "" or text.startswith(MISSING_PREFIXES) or text.lower() in {"nan", "missing"}:
        return None
    match = NUMBER_RE.match(text)
    if not match:
        return None
    return float(match.group(1))


def is_yes(value: object) -> int | None:
    code = numeric_code(value)
    if code is None:
        return None
    if code == 1:
        return 1
    if code == 0:
        return 0
    return None


def clean_date(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if text == "" or text.startswith(MISSING_PREFIXES):
        return ""
    return text


def add_person_vars(row: dict[str, object], source: pd.Series, var_names: list[str], prefix: str) -> None:
    for var in var_names:
        raw = value_or_blank(source, var)
        clean_name = var.lower()
        row[f"{prefix}_{clean_name}_raw"] = raw
        row[f"{prefix}_{clean_name}_num"] = numeric_code(raw)


def add_side_vars(row: dict[str, object], source: pd.Series, mapping: dict[str, str], prefix: str) -> None:
    for clean_name, var in mapping.items():
        raw = value_or_blank(source, var)
        row[f"{prefix}_{clean_name}_var"] = var
        row[f"{prefix}_{clean_name}_raw"] = raw
        row[f"{prefix}_{clean_name}_num"] = numeric_code(raw)


def side_rows_from_xray(df: pd.DataFrame, side_code: int) -> pd.DataFrame:
    side_num = df["SIDE"].map(numeric_code)
    return df.loc[side_num == side_code].copy()


def build_dataset() -> pd.DataFrame:
    enrollees = read_oai(FILES["enrollees"]).set_index("ID", drop=False)
    subject = read_oai(FILES["subject"]).set_index("ID", drop=False)
    clinical = read_oai(FILES["clinical00"]).set_index("ID", drop=False)
    outcomes = read_oai(FILES["outcomes"]).set_index("id", drop=False)
    xray_sq = read_oai(FILES["xray_sq"])
    xray_jsw = read_oai(FILES["xray_jsw"])

    xray_sq_by_side = {
        side: side_rows_from_xray(xray_sq, spec["side_code"]).set_index("ID", drop=False)
        for side, spec in SIDE_SPECS.items()
    }
    xray_jsw_by_side = {
        side: side_rows_from_xray(xray_jsw, spec["side_code"]).set_index("ID", drop=False)
        for side, spec in SIDE_SPECS.items()
    }

    ids = sorted(set(enrollees.index) | set(subject.index) | set(clinical.index) | set(outcomes.index))
    rows: list[dict[str, object]] = []

    for participant_id in ids:
        enrollee = enrollees.loc[participant_id] if participant_id in enrollees.index else pd.Series(dtype=object)
        subj = subject.loc[participant_id] if participant_id in subject.index else pd.Series(dtype=object)
        clin = clinical.loc[participant_id] if participant_id in clinical.index else pd.Series(dtype=object)
        out = outcomes.loc[participant_id] if participant_id in outcomes.index else pd.Series(dtype=object)

        for side, spec in SIDE_SPECS.items():
            row: dict[str, object] = {
                "id": participant_id,
                "side": side,
                "side_code": spec["side_code"],
                "side_label": spec["side_label"],
            }

            add_person_vars(row, enrollee, PERSON_VARS["enrollees"], "enrollee")
            add_person_vars(row, subj, PERSON_VARS["subject"], "subject")
            add_person_vars(row, clin, PERSON_VARS["clinical00"], "clinical00")
            add_side_vars(row, clin, spec["pain"], "baseline")
            add_side_vars(row, clin, spec["injury"], "baseline")
            add_side_vars(row, clin, spec["baseline_kr"], "baseline")
            add_side_vars(row, subj, spec["subject_xray"], "baseline")

            outcome_prefix = spec["outcome_prefix"]
            kr_date = value_or_blank(out, f"{outcome_prefix}DATE")
            kr_days = value_or_blank(out, f"{outcome_prefix}DAYS")
            kr_confirm = value_or_blank(out, f"{outcome_prefix}RPCF")
            kr_prior_baseline = value_or_blank(out, f"{outcome_prefix}BLRP")
            kr_visit_self_report = value_or_blank(out, f"{outcome_prefix}VSRP")
            kr_visit_adjudicated = value_or_blank(out, f"{outcome_prefix}VSAF")

            row.update(
                {
                    "outcome_kr_date_raw": clean_date(kr_date),
                    "outcome_kr_days_raw": kr_days,
                    "outcome_kr_days": numeric_code(kr_days),
                    "outcome_kr_confirm_raw": kr_confirm,
                    "outcome_kr_confirm_code": numeric_code(kr_confirm),
                    "outcome_kr_prior_baseline_raw": kr_prior_baseline,
                    "outcome_kr_prior_baseline": is_yes(kr_prior_baseline),
                    "outcome_kr_visit_self_report_raw": kr_visit_self_report,
                    "outcome_kr_visit_adjudicated_raw": kr_visit_adjudicated,
                }
            )
            row["outcome_kr_event"] = int(bool(row["outcome_kr_date_raw"]) and (row["outcome_kr_days"] or 0) > 0)

            sq = (
                xray_sq_by_side[side].loc[participant_id]
                if participant_id in xray_sq_by_side[side].index
                else pd.Series(dtype=object)
            )
            for var in [
                "V00XRKL",
                "V00XRJSM",
                "V00XRJSL",
                "V00XROSTM",
                "V00XROSTL",
                "V00XRSCFM",
                "V00XRSCFL",
            ]:
                raw = value_or_blank(sq, var)
                row[f"xray_sq_{var.lower()}_raw"] = raw
                row[f"xray_sq_{var.lower()}_num"] = numeric_code(raw)

            jsw = (
                xray_jsw_by_side[side].loc[participant_id]
                if participant_id in xray_jsw_by_side[side].index
                else pd.Series(dtype=object)
            )
            for var in ["V00MCMJSW", "V00JSW175", "V00JSW200", "V00JSW250", "V00JSW300", "V00XMJSW"]:
                raw = value_or_blank(jsw, var)
                row[f"xray_jsw_{var.lower()}_raw"] = raw
                row[f"xray_jsw_{var.lower()}"] = numeric_code(raw)

            baseline_kr_flags = [
                row.get("baseline_prior_kr_surgery_num"),
                row.get("baseline_eligible_prior_kr_num"),
            ]
            row["exclude_baseline_kr_any"] = int(any(value == 1 for value in baseline_kr_flags if value is not None))
            row["analysis_eligible_first_pass"] = int(row["exclude_baseline_kr_any"] == 0)
            row["analysis_complete_core_first_pass"] = int(
                row["analysis_eligible_first_pass"] == 1
                and row.get("baseline_womac_pain_num") is not None
                and row.get("xray_sq_v00xrkl_num") is not None
            )

            rows.append(row)

    return pd.DataFrame(rows)


def write_dictionary(df: pd.DataFrame) -> None:
    rows = []
    for column in df.columns:
        if column.endswith("_raw"):
            role = "raw OAI value"
        elif column.endswith("_num") or column.endswith("_code") or column in {
            "side_code",
            "outcome_kr_days",
            "outcome_kr_event",
            "exclude_baseline_kr_any",
            "analysis_eligible_first_pass",
        }:
            role = "derived numeric/code"
        elif column.endswith("_var"):
            role = "source OAI variable name"
        else:
            role = "identifier/label"
        rows.append({"variable": column, "role": role})
    with (META / "oai_knee_dataset_dictionary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["variable", "role"])
        writer.writeheader()
        writer.writerows(rows)


def write_summary(df: pd.DataFrame) -> None:
    eligible = df.loc[df["analysis_eligible_first_pass"] == 1].copy()
    summary_rows = [
        {"metric": "knee_rows_total", "value": len(df)},
        {"metric": "participant_count", "value": df["id"].nunique()},
        {"metric": "eligible_knee_rows_first_pass", "value": len(eligible)},
        {"metric": "excluded_baseline_kr_knees", "value": int(df["exclude_baseline_kr_any"].sum())},
        {"metric": "kr_events_total", "value": int(df["outcome_kr_event"].sum())},
        {"metric": "kr_events_eligible_first_pass", "value": int(eligible["outcome_kr_event"].sum())},
        {
            "metric": "eligible_with_baseline_womac_pain",
            "value": int(eligible["baseline_womac_pain_num"].notna().sum()),
        },
        {
            "metric": "eligible_with_baseline_xray_kl",
            "value": int(eligible["xray_sq_v00xrkl_num"].notna().sum()),
        },
        {
            "metric": "eligible_with_baseline_jsw",
            "value": int(eligible["xray_jsw_v00mcmjsw"].notna().sum()),
        },
        {
            "metric": "complete_core_first_pass",
            "value": int(df["analysis_complete_core_first_pass"].sum()),
        },
        {
            "metric": "complete_core_kr_events_first_pass",
            "value": int(df.loc[df["analysis_complete_core_first_pass"] == 1, "outcome_kr_event"].sum()),
        },
    ]

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(RESULTS / "oai_knee_dataset_summary.csv", index=False)

    by_side = (
        df.groupby(["side", "analysis_eligible_first_pass"], dropna=False)
        .agg(knees=("id", "size"), participants=("id", "nunique"), kr_events=("outcome_kr_event", "sum"))
        .reset_index()
    )
    by_side.to_csv(RESULTS / "oai_knee_dataset_by_side.csv", index=False)


def main() -> None:
    DERIVED.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    df = build_dataset()
    output_path = DERIVED / "oai_knee_level_first_pass.csv"
    df.to_csv(output_path, index=False)
    write_dictionary(df)
    write_summary(df)

    print(f"Wrote {len(df)} knee-level rows to {output_path}")
    print(f"Participants: {df['id'].nunique()}")
    print(f"First-pass eligible knees: {int(df['analysis_eligible_first_pass'].sum())}")
    print(f"KR/TKA events, all knees: {int(df['outcome_kr_event'].sum())}")
    print(
        "KR/TKA events, first-pass eligible knees: "
        f"{int(df.loc[df['analysis_eligible_first_pass'] == 1, 'outcome_kr_event'].sum())}"
    )


if __name__ == "__main__":
    main()
