#!/usr/bin/env python3
"""Build an MRKR knee-level transport dataset for OAI-derived validation.

The MRKR source is not a scheduled cohort like OAI. This script therefore
constructs an approximate 24-month landmark dataset from real-world radiograph,
pain, demographic, and CPT tables.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "MRKR" / "tables"
DERIVED = ROOT / "derived" / "MRKR"
RESULTS = ROOT / "results" / "tables"

BASELINE_TO_LANDMARK_MIN_DAYS = 548  # 18 months
BASELINE_TO_LANDMARK_TARGET_DAYS = 730  # 24 months
BASELINE_TO_LANDMARK_MAX_DAYS = 1095  # 36 months
PAIN_MATCH_TOLERANCE_DAYS = 180

# Surgical CPT codes for knee arthroplasty. Code 01402 is anesthesia for TKA
# and is intentionally not used as a surgical outcome definition.
KNEE_ARTHROPLASTY_CPT_CODES = {
    "27438",  # patella arthroplasty with prosthesis
    "27440",  # tibial plateau arthroplasty
    "27442",  # femoral condyles or tibial plateau(s)
    "27445",  # hinge prosthesis
    "27446",  # unicompartmental arthroplasty
    "27447",  # total knee arthroplasty
    "27486",  # revision TKA, one component
    "27487",  # revision TKA, femoral and tibial components
}
PRIMARY_TKA_CPT_CODES = {"27447"}


def month_diff(later: pd.Series, earlier: pd.Series) -> pd.Series:
    return (later - earlier).dt.days / 30.4375


def normalize_side(value: object) -> str | float:
    if pd.isna(value):
        return np.nan
    text = str(value).strip().lower()
    if text in {"l", "left", "lt"}:
        return "L"
    if text in {"r", "right", "rt"}:
        return "R"
    if text in {"b", "bilateral", "both", "bl"}:
        return "B"
    return np.nan


def read_demographics() -> pd.DataFrame:
    demo = pd.read_csv(TABLES / "MRKR_demographics.csv", dtype={"empi_anon": "int64"})
    demo["female"] = demo["sex"].str.lower().eq("female").astype("Int64")
    return demo


def build_image_observations() -> pd.DataFrame:
    cols = [
        "empi_anon",
        "StudyDate_anon",
        "age_at_exam",
        "laterality",
        "view_position",
        "weight_bearing",
        "arthroplasty",
        "L_KLG_inference",
        "R_KLG_inference",
    ]
    image = pd.read_csv(TABLES / "MRKR_image_metadata.csv", usecols=cols)
    image["exam_date"] = pd.to_datetime(image["StudyDate_anon"], errors="coerce")
    image["arthroplasty_side"] = image["arthroplasty"].map(normalize_side)
    image["image_side"] = image["laterality"].map(normalize_side)

    knee_rows: list[pd.DataFrame] = []
    for side, kl_col in (("L", "L_KLG_inference"), ("R", "R_KLG_inference")):
        side_mask = (
            image["image_side"].isin([side, "B"])
            | image[kl_col].notna()
            | image["arthroplasty_side"].isin([side, "B"])
        )
        z = image.loc[
            side_mask,
            ["empi_anon", "exam_date", "age_at_exam", "view_position", "weight_bearing", "arthroplasty_side", kl_col],
        ].copy()
        z["side"] = side
        z["klg"] = pd.to_numeric(z[kl_col], errors="coerce")
        z["arthroplasty_seen"] = z["arthroplasty_side"].isin([side, "B"])
        z["weight_bearing"] = pd.to_numeric(z["weight_bearing"], errors="coerce").fillna(0).astype(int)
        knee_rows.append(
            z[
                [
                    "empi_anon",
                    "side",
                    "exam_date",
                    "age_at_exam",
                    "klg",
                    "arthroplasty_seen",
                    "view_position",
                    "weight_bearing",
                ]
            ]
        )

    knee = pd.concat(knee_rows, ignore_index=True).dropna(subset=["exam_date"])
    # Multiple images can belong to the same knee/date. Use the maximum KL and
    # any observed arthroplasty hardware to keep date-level records conservative.
    return (
        knee.groupby(["empi_anon", "side", "exam_date"], as_index=False)
        .agg(
            age_at_exam=("age_at_exam", "median"),
            klg=("klg", "max"),
            arthroplasty_seen=("arthroplasty_seen", "max"),
            any_weight_bearing=("weight_bearing", "max"),
            image_rows=("klg", "size"),
        )
        .sort_values(["empi_anon", "side", "exam_date"])
        .reset_index(drop=True)
    )


def select_landmark_pairs(knee_obs: pd.DataFrame) -> pd.DataFrame:
    no_hardware = knee_obs.loc[~knee_obs["arthroplasty_seen"] & knee_obs["klg"].notna()].copy()
    baseline = (
        no_hardware.sort_values("exam_date")
        .groupby(["empi_anon", "side"], as_index=False)
        .first()
        .rename(
            columns={
                "exam_date": "baseline_date",
                "age_at_exam": "age_baseline",
                "klg": "kl_0",
                "any_weight_bearing": "baseline_weight_bearing",
                "image_rows": "baseline_image_rows",
            }
        )
    )

    candidates = no_hardware.merge(
        baseline[["empi_anon", "side", "baseline_date"]],
        on=["empi_anon", "side"],
        how="inner",
    )
    candidates["baseline_to_exam_days"] = (candidates["exam_date"] - candidates["baseline_date"]).dt.days
    candidates = candidates.loc[
        candidates["baseline_to_exam_days"].between(
            BASELINE_TO_LANDMARK_MIN_DAYS, BASELINE_TO_LANDMARK_MAX_DAYS
        )
    ].copy()
    candidates["target_distance_days"] = (
        candidates["baseline_to_exam_days"] - BASELINE_TO_LANDMARK_TARGET_DAYS
    ).abs()
    landmark = (
        candidates.sort_values(["empi_anon", "side", "target_distance_days", "exam_date"])
        .groupby(["empi_anon", "side"], as_index=False)
        .first()
        .rename(
            columns={
                "exam_date": "landmark_date",
                "age_at_exam": "age",
                "klg": "kl_24",
                "any_weight_bearing": "landmark_weight_bearing",
                "image_rows": "landmark_image_rows",
            }
        )
    )

    pair = baseline.merge(
        landmark[
            [
                "empi_anon",
                "side",
                "landmark_date",
                "age",
                "kl_24",
                "baseline_to_exam_days",
                "target_distance_days",
                "landmark_weight_bearing",
                "landmark_image_rows",
            ]
        ],
        on=["empi_anon", "side"],
        how="inner",
    )
    pair["baseline_to_landmark_months"] = pair["baseline_to_exam_days"] / 30.4375
    pair["kl_change"] = pair["kl_24"] - pair["kl_0"]
    pair["knee_id"] = "MRKR_" + pair["empi_anon"].astype(str) + "_" + pair["side"]
    return pair


def build_hardware_outcome(pair: pd.DataFrame, knee_obs: pd.DataFrame) -> pd.DataFrame:
    hardware = knee_obs.loc[knee_obs["arthroplasty_seen"], ["empi_anon", "side", "exam_date"]].copy()
    merged = hardware.merge(
        pair[["empi_anon", "side", "landmark_date"]],
        on=["empi_anon", "side"],
        how="inner",
    )
    post = merged.loc[merged["exam_date"] > merged["landmark_date"]].copy()
    first_event = (
        post.sort_values("exam_date")
        .groupby(["empi_anon", "side"], as_index=False)
        .first()
        .rename(columns={"exam_date": "hardware_event_date"})
    )
    first_event = first_event[["empi_anon", "side", "hardware_event_date"]]
    last_image = (
        knee_obs.groupby(["empi_anon", "side"], as_index=False)["exam_date"]
        .max()
        .rename(columns={"exam_date": "last_image_date"})
    )
    out = pair.merge(first_event, on=["empi_anon", "side"], how="left").merge(
        last_image, on=["empi_anon", "side"], how="left"
    )
    out["event_hardware_after_landmark"] = out["hardware_event_date"].notna().astype(int)
    out["time_hardware_months"] = np.where(
        out["event_hardware_after_landmark"].eq(1),
        month_diff(out["hardware_event_date"], out["landmark_date"]),
        month_diff(out["last_image_date"], out["landmark_date"]),
    )
    return out


def expand_pain_by_side() -> pd.DataFrame:
    pain = pd.read_csv(
        TABLES / "MRKR_pain.csv",
        usecols=["empi_anon", "date_anon", "pain_score", "pain_location", "laterality"],
    )
    pain["pain_date"] = pd.to_datetime(pain["date_anon"], errors="coerce")
    pain["pain_score"] = pd.to_numeric(pain["pain_score"], errors="coerce")
    pain["side_norm"] = pain["laterality"].map(normalize_side)
    pain = pain.dropna(subset=["pain_date", "pain_score", "side_norm"])

    expanded = []
    for side in ("L", "R"):
        z = pain.loc[pain["side_norm"].isin([side, "B"]), ["empi_anon", "pain_date", "pain_score"]].copy()
        z["side"] = side
        expanded.append(z)
    out = pd.concat(expanded, ignore_index=True)
    # Multiple same-day pain records are collapsed to the maximum score, because
    # the validation model should capture clinically meaningful pain severity.
    return (
        out.groupby(["empi_anon", "side", "pain_date"], as_index=False)["pain_score"]
        .max()
        .sort_values(["empi_anon", "side", "pain_date"])
    )


def nearest_pain(
    target: pd.DataFrame,
    pain_index: dict[tuple[int, str], tuple[np.ndarray, np.ndarray]],
    target_date_col: str,
    suffix: str,
) -> pd.DataFrame:
    pieces = []
    for (empi, side), t in target[["empi_anon", "side", target_date_col]].groupby(["empi_anon", "side"]):
        p = pain_index.get((int(empi), str(side)))
        if p is None:
            z = t.copy()
            z[f"pain_{suffix}"] = np.nan
            z[f"pain_date_{suffix}"] = pd.NaT
            z[f"pain_day_distance_{suffix}"] = np.nan
        else:
            z = t.copy()
            p_dates, p_scores = p
            chosen_score = []
            chosen_date = []
            chosen_delta = []
            for date in z[target_date_col].to_numpy(dtype="datetime64[ns]"):
                deltas = np.abs((p_dates - date).astype("timedelta64[D]").astype(float))
                idx = int(np.argmin(deltas))
                if deltas[idx] <= PAIN_MATCH_TOLERANCE_DAYS:
                    chosen_score.append(p_scores[idx])
                    chosen_date.append(pd.Timestamp(p_dates[idx]))
                    chosen_delta.append(deltas[idx])
                else:
                    chosen_score.append(np.nan)
                    chosen_date.append(pd.NaT)
                    chosen_delta.append(np.nan)
            z[f"pain_{suffix}"] = chosen_score
            z[f"pain_date_{suffix}"] = chosen_date
            z[f"pain_day_distance_{suffix}"] = chosen_delta
        pieces.append(z)
    return pd.concat(pieces, ignore_index=True)


def attach_pain(pair: pd.DataFrame) -> pd.DataFrame:
    pain = expand_pain_by_side()
    pain_index = {
        (int(empi), str(side)): (
            g["pain_date"].to_numpy(dtype="datetime64[ns]"),
            g["pain_score"].to_numpy(),
        )
        for (empi, side), g in pain.groupby(["empi_anon", "side"], sort=False)
    }
    key = pair[["empi_anon", "side", "baseline_date", "landmark_date"]].copy()
    base = nearest_pain(key, pain_index, "baseline_date", "0")
    land = nearest_pain(key, pain_index, "landmark_date", "24")
    out = pair.merge(
        base[["empi_anon", "side", "pain_0", "pain_date_0", "pain_day_distance_0"]],
        on=["empi_anon", "side"],
        how="left",
    ).merge(
        land[["empi_anon", "side", "pain_24", "pain_date_24", "pain_day_distance_24"]],
        on=["empi_anon", "side"],
        how="left",
    )
    out["pain_change"] = out["pain_24"] - out["pain_0"]
    out["pain_24_group"] = pd.cut(
        out["pain_24"],
        bins=[-np.inf, 0, 3, 6, np.inf],
        labels=["0", "1-3", "4-6", "7-10"],
    )
    return out


def build_cpt_outcomes(pair: pd.DataFrame) -> pd.DataFrame:
    arthro_rows = []
    last_dates = []
    usecols = ["empi_anon", "cpt_code", "date_anon", "age_at_procedure"]
    for chunk in pd.read_csv(TABLES / "MRKR_CPT.csv", usecols=usecols, dtype={"cpt_code": "string"}, chunksize=500_000):
        chunk["cpt_date"] = pd.to_datetime(chunk["date_anon"], errors="coerce")
        chunk = chunk.dropna(subset=["cpt_date"])
        last_dates.append(chunk.groupby("empi_anon", as_index=False)["cpt_date"].max())
        arthro = chunk.loc[chunk["cpt_code"].isin(KNEE_ARTHROPLASTY_CPT_CODES)].copy()
        if not arthro.empty:
            arthro["cpt_primary_tka_code"] = arthro["cpt_code"].isin(PRIMARY_TKA_CPT_CODES).astype(int)
            arthro_rows.append(arthro[["empi_anon", "cpt_code", "cpt_date", "cpt_primary_tka_code"]])

    if last_dates:
        last_cpt = (
            pd.concat(last_dates, ignore_index=True)
            .groupby("empi_anon", as_index=False)["cpt_date"]
            .max()
            .rename(columns={"cpt_date": "last_cpt_date"})
        )
    else:
        last_cpt = pd.DataFrame(columns=["empi_anon", "last_cpt_date"])

    out = pair.merge(last_cpt, on="empi_anon", how="left")
    if not arthro_rows:
        out["cpt_arthroplasty_after_landmark"] = 0
        out["cpt_primary_tka_after_landmark"] = 0
        out["cpt_event_date"] = pd.NaT
        out["cpt_event_code"] = pd.NA
        out["time_cpt_months"] = month_diff(out["last_cpt_date"], out["landmark_date"])
        return out

    arthro_all = pd.concat(arthro_rows, ignore_index=True)
    merged = arthro_all.merge(pair[["empi_anon", "landmark_date"]].drop_duplicates(), on="empi_anon", how="inner")
    post = merged.loc[merged["cpt_date"] > merged["landmark_date"]].copy()
    first_any = (
        post.sort_values("cpt_date")
        .groupby("empi_anon", as_index=False)
        .first()
        .rename(columns={"cpt_date": "cpt_event_date", "cpt_code": "cpt_event_code"})
    )
    first_primary = (
        post.loc[post["cpt_primary_tka_code"].eq(1)]
        .sort_values("cpt_date")
        .groupby("empi_anon", as_index=False)
        .first()[["empi_anon", "cpt_date"]]
        .rename(columns={"cpt_date": "cpt_primary_tka_event_date"})
    )
    out = out.merge(
        first_any[["empi_anon", "cpt_event_date", "cpt_event_code"]],
        on="empi_anon",
        how="left",
    ).merge(first_primary, on="empi_anon", how="left")
    out["cpt_arthroplasty_after_landmark"] = out["cpt_event_date"].notna().astype(int)
    out["cpt_primary_tka_after_landmark"] = out["cpt_primary_tka_event_date"].notna().astype(int)
    out["time_cpt_months"] = np.where(
        out["cpt_arthroplasty_after_landmark"].eq(1),
        month_diff(out["cpt_event_date"], out["landmark_date"]),
        month_diff(out["last_cpt_date"], out["landmark_date"]),
    )
    return out


def add_scaled_variables(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["pain_0", "pain_24", "pain_change", "kl_0", "kl_24", "kl_change"]:
        mean = out[col].mean(skipna=True)
        sd = out[col].std(skipna=True)
        out[f"{col}_z"] = (out[col] - mean) / sd if sd and not np.isnan(sd) else np.nan
    out["side"] = pd.Categorical(out["side"], categories=["R", "L"])
    out["side_label"] = out["side"].map({"R": "right", "L": "left"})
    out["model_f_complete"] = (
        out[
            [
                "time_hardware_months",
                "event_hardware_after_landmark",
                "age",
                "female",
                "side",
                "pain_24",
                "kl_0",
                "kl_change",
            ]
        ]
        .notna()
        .all(axis=1)
        & out["time_hardware_months"].gt(0)
    ).astype(int)
    return out


def write_dictionary() -> None:
    rows = [
        ("empi_anon", "MRKR de-identified patient identifier."),
        ("knee_id", "MRKR knee-level identifier constructed as MRKR_<empi_anon>_<side>."),
        ("side", "Target knee side: L or R."),
        ("age", "Age at landmark radiograph."),
        ("female", "1 for female, 0 for male."),
        ("baseline_date", "Earliest side-specific radiograph date with inferred KL and no arthroplasty hardware."),
        ("landmark_date", "Radiograph closest to 24 months after baseline within the 18-36 month window."),
        ("baseline_to_landmark_months", "Observed months between baseline and landmark radiographs."),
        ("pain_0", "Nearest 0-10 knee pain score within 180 days of baseline. Bilateral scores are mapped to both knees."),
        ("pain_24", "Nearest 0-10 knee pain score within 180 days of landmark."),
        ("pain_change", "pain_24 minus pain_0."),
        ("pain_24_group", "Landmark pain severity group: 0, 1-3, 4-6, or 7-10."),
        ("kl_0", "Baseline side-specific MRKR model-inferred Kellgren-Lawrence grade."),
        ("kl_24", "Landmark side-specific MRKR model-inferred Kellgren-Lawrence grade."),
        ("kl_change", "kl_24 minus kl_0."),
        ("event_hardware_after_landmark", "Primary knee-side outcome: arthroplasty hardware first observed on target knee after landmark."),
        ("time_hardware_months", "Months from landmark to hardware event or last target-knee radiograph."),
        ("cpt_arthroplasty_after_landmark", "Sensitivity patient-level outcome: knee arthroplasty CPT code after landmark, not side-specific."),
        ("cpt_primary_tka_after_landmark", "Sensitivity patient-level outcome: CPT 27447 after landmark, not side-specific."),
        ("time_cpt_months", "Months from landmark to first knee arthroplasty CPT event or last CPT record."),
        ("model_f_complete", "Complete-case flag for Model F transport variables and positive hardware follow-up time."),
    ]
    pd.DataFrame(rows, columns=["variable", "definition"]).to_csv(
        DERIVED / "mrkr_transport_data_dictionary.csv", index=False
    )


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    def row(name: str, value: object) -> dict[str, object]:
        return {"metric": name, "value": value}

    complete = df.loc[df["model_f_complete"].eq(1)]
    rows = [
        row("knee_rows", len(df)),
        row("patients", df["empi_anon"].nunique()),
        row("model_f_complete_knees", len(complete)),
        row("model_f_complete_patients", complete["empi_anon"].nunique()),
        row("hardware_events_after_landmark_complete", int(complete["event_hardware_after_landmark"].sum())),
        row("cpt_arthroplasty_events_after_landmark_complete", int(complete["cpt_arthroplasty_after_landmark"].sum())),
        row("cpt_primary_tka_events_after_landmark_complete", int(complete["cpt_primary_tka_after_landmark"].sum())),
        row("median_baseline_to_landmark_months", complete["baseline_to_landmark_months"].median()),
        row("median_hardware_followup_months", complete["time_hardware_months"].median()),
        row("mean_age_complete", complete["age"].mean()),
        row("female_pct_complete", complete["female"].mean()),
        row("pain_24_nonmissing_pct", df["pain_24"].notna().mean()),
        row("pain_0_nonmissing_pct", df["pain_0"].notna().mean()),
        row("kl_change_mean_complete", complete["kl_change"].mean()),
    ]
    return pd.DataFrame(rows)


def main() -> None:
    DERIVED.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    demographics = read_demographics()
    knee_obs = build_image_observations()
    pair = select_landmark_pairs(knee_obs)
    pair = build_hardware_outcome(pair, knee_obs)
    pair = attach_pain(pair)
    pair = build_cpt_outcomes(pair)
    pair = pair.merge(demographics, on="empi_anon", how="left")
    pair = add_scaled_variables(pair)

    ordered_cols = [
        "empi_anon",
        "knee_id",
        "side",
        "side_label",
        "sex",
        "female",
        "race",
        "ethnicity",
        "age",
        "age_baseline",
        "baseline_date",
        "landmark_date",
        "baseline_to_landmark_months",
        "baseline_weight_bearing",
        "landmark_weight_bearing",
        "pain_0",
        "pain_date_0",
        "pain_day_distance_0",
        "pain_24",
        "pain_date_24",
        "pain_day_distance_24",
        "pain_change",
        "pain_24_group",
        "kl_0",
        "kl_24",
        "kl_change",
        "pain_0_z",
        "pain_24_z",
        "pain_change_z",
        "kl_0_z",
        "kl_24_z",
        "kl_change_z",
        "event_hardware_after_landmark",
        "hardware_event_date",
        "last_image_date",
        "time_hardware_months",
        "cpt_arthroplasty_after_landmark",
        "cpt_primary_tka_after_landmark",
        "cpt_event_date",
        "cpt_event_code",
        "cpt_primary_tka_event_date",
        "last_cpt_date",
        "time_cpt_months",
        "model_f_complete",
    ]
    ordered_cols = [c for c in ordered_cols if c in pair.columns]
    pair = pair[ordered_cols + [c for c in pair.columns if c not in ordered_cols]]
    pair.to_csv(DERIVED / "mrkr_transport_knee_dataset.csv", index=False)
    summarize(pair).to_csv(RESULTS / "mrkr_transport_dataset_summary.csv", index=False)
    write_dictionary()

    print(f"Wrote {DERIVED / 'mrkr_transport_knee_dataset.csv'}")
    print(f"Knees: {len(pair):,}; patients: {pair['empi_anon'].nunique():,}")
    print(f"Model F complete knees: {int(pair['model_f_complete'].sum()):,}")
    print(
        "Primary hardware events in complete set: "
        f"{int(pair.loc[pair['model_f_complete'].eq(1), 'event_hardware_after_landmark'].sum()):,}"
    )


if __name__ == "__main__":
    main()
