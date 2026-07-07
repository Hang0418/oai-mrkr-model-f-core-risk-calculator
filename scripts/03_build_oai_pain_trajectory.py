#!/usr/bin/env python3
"""Build OAI longitudinal knee pain/function trajectories.

Creates one row per participant-knee-visit using available AllClinical tables.
Values are parsed from OAI "code: label" strings into numeric columns when
possible. Visit months are approximate and should be confirmed for final models.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_CLINICAL = ROOT / "raw" / "OAI" / "AllClinical_ASCII"
DERIVED = ROOT / "derived" / "OAI"
RESULTS = ROOT / "results" / "tables"


VISIT_MONTHS_APPROX = {
    "00": 0,
    "01": 12,
    "03": 24,
    "05": 36,
    "06": 48,
    "07": 60,
    "08": 72,
    "10": 96,
    "12": 120,
    "13": 144,
    "14": 168,
}

SIDE_SUFFIXES = {
    "right": {
        "side_code": 1,
        "womac_pain": "WOMKPR",
        "womac_function": "WOMADLR",
        "womac_stiffness": "WOMSTFR",
        "womac_total": "WOMTSR",
        "koos_pain": "KOOSKPR",
        "koos_symptom": "KOOSYMR",
        "koos_function": "KOOSFSR",
        "pain_frequency": "RPWKTYP",
        "pain_past30d": "RPWKPRV",
    },
    "left": {
        "side_code": 2,
        "womac_pain": "WOMKPL",
        "womac_function": "WOMADLL",
        "womac_stiffness": "WOMSTFL",
        "womac_total": "WOMTSL",
        "koos_pain": "KOOSKPL",
        "koos_symptom": "KOOSYML",
        "koos_function": "KOOSFSL",
        "pain_frequency": "LPWKTYP",
        "pain_past30d": "LPWKPRV",
    },
}

VISIT_RE = re.compile(r"(\d{2})", re.IGNORECASE)
NUMBER_RE = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)")


def numeric_code(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if text == "" or text.startswith(".") or text.lower() in {"nan", "missing"}:
        return None
    match = NUMBER_RE.match(text)
    return float(match.group(1)) if match else None


def visit_code_from_path(path: Path) -> str:
    match = VISIT_RE.search(path.stem)
    return match.group(1) if match else ""


def read_table(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="|", dtype=str, keep_default_na=False)


def build_long() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    clinical_files = sorted(RAW_CLINICAL.glob("*.txt"))

    for path in clinical_files:
        visit_code = visit_code_from_path(path)
        if visit_code not in VISIT_MONTHS_APPROX:
            continue
        prefix = f"V{visit_code}"
        table = read_table(path)
        id_col = "ID" if "ID" in table.columns else "id"
        available_columns = set(table.columns)

        for _, source in table.iterrows():
            participant_id = source[id_col]
            for side, spec in SIDE_SUFFIXES.items():
                row = {
                    "id": participant_id,
                    "side": side,
                    "side_code": spec["side_code"],
                    "visit_code": visit_code,
                    "visit_month_approx": VISIT_MONTHS_APPROX[visit_code],
                    "source_table": path.name,
                }
                has_any = False
                for clean_name, suffix in spec.items():
                    if clean_name == "side_code":
                        continue
                    var = f"{prefix}{suffix}"
                    row[f"{clean_name}_var"] = var
                    if var in available_columns:
                        raw = source[var]
                        row[f"{clean_name}_raw"] = raw
                        row[clean_name] = numeric_code(raw)
                        has_any = has_any or row[clean_name] is not None
                    else:
                        row[f"{clean_name}_raw"] = ""
                        row[clean_name] = None
                if has_any:
                    rows.append(row)

    return pd.DataFrame(rows)


def write_summary(df: pd.DataFrame) -> None:
    summary = (
        df.groupby(["visit_code", "visit_month_approx", "side"], dropna=False)
        .agg(
            rows=("id", "size"),
            participants=("id", "nunique"),
            womac_pain_nonmissing=("womac_pain", lambda x: int(x.notna().sum())),
            womac_function_nonmissing=("womac_function", lambda x: int(x.notna().sum())),
            koos_pain_nonmissing=("koos_pain", lambda x: int(x.notna().sum())),
        )
        .reset_index()
        .sort_values(["visit_month_approx", "side"])
    )
    summary.to_csv(RESULTS / "oai_pain_trajectory_summary.csv", index=False)


def main() -> None:
    DERIVED.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    df = build_long()
    out = DERIVED / "oai_pain_trajectory_long.csv"
    df.to_csv(out, index=False)
    write_summary(df)

    print(f"Wrote {len(df)} participant-knee-visit rows to {out}")
    print(f"Participants: {df['id'].nunique()}")
    print(f"Visits: {', '.join(sorted(df['visit_code'].unique()))}")


if __name__ == "__main__":
    main()
