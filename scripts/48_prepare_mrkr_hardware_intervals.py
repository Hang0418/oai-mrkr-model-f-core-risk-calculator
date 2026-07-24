#!/usr/bin/env python3
"""Reconstruct MRKR hardware-detection intervals using the cohort builder's date-level rules."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "tables" / "latest_framework"
OUT.mkdir(parents=True, exist_ok=True)


def load_builder():
    path = ROOT / "scripts" / "16_build_mrkr_transport_dataset.py"
    spec = importlib.util.spec_from_file_location("mrkr_builder", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> None:
    builder = load_builder()
    observations = builder.build_image_observations()
    raw = pd.read_csv(
        ROOT / "derived" / "MRKR" / "mrkr_transport_knee_dataset.csv",
        parse_dates=["landmark_date", "hardware_event_date"],
    )
    core = pd.read_csv(ROOT / "derived" / "transport" / "mrkr_validation_model_f_core.csv")
    events = raw.loc[
        raw["knee_id"].isin(core["knee_id"])
        & raw["event_hardware_after_landmark"].eq(1),
        ["empi_anon", "side", "knee_id", "landmark_date", "hardware_event_date"],
    ].copy()

    candidates = observations.merge(events, on=["empi_anon", "side"], how="inner")
    candidates = candidates.loc[
        candidates["exam_date"].ge(candidates["landmark_date"])
        & candidates["exam_date"].lt(candidates["hardware_event_date"])
        & ~candidates["arthroplasty_seen"]
    ]
    last_negative = candidates.groupby("knee_id", as_index=False)["exam_date"].max()
    last_negative = last_negative.rename(columns={"exam_date": "last_negative_date"})
    events = events.merge(last_negative, on="knee_id", how="left")
    events["last_negative_date"] = events["last_negative_date"].fillna(events["landmark_date"])
    events["interval_left_months"] = (
        events["last_negative_date"] - events["landmark_date"]
    ).dt.days / 30.4375
    events["interval_right_months"] = (
        events["hardware_event_date"] - events["landmark_date"]
    ).dt.days / 30.4375

    nearest = pd.read_csv(
        ROOT / "results" / "tables" / "reviewer_round2_hardware_nearest_cpt_matches.csv",
        parse_dates=["nearest_cpt_date"],
    )
    keep = [
        "knee_id",
        "nearest_cpt_date",
        "difference_days",
        "abs_difference_days",
        "laterality_match",
    ]
    events = events.merge(nearest[keep], on="knee_id", how="left")
    events["cpt_months"] = (
        events["nearest_cpt_date"] - events["landmark_date"]
    ).dt.days / 30.4375
    events["cpt_within_interval_90"] = (
        events["cpt_months"].notna()
        & events["abs_difference_days"].le(90)
        & events["cpt_months"].gt(events["interval_left_months"])
        & events["cpt_months"].le(events["interval_right_months"])
    )
    events.to_csv(OUT / "latest_mrkr_hardware_detection_intervals.csv", index=False)

    interval_days = (
        events["interval_right_months"] - events["interval_left_months"]
    ) * 30.4375
    print(interval_days.describe(percentiles=[0.25, 0.5, 0.75]).to_string())
    print("Intervals >365 days:", int(interval_days.gt(365).sum()))
    print(
        "Intervals crossing 24 months:",
        int(
            (
                events["interval_left_months"].lt(24)
                & events["interval_right_months"].gt(24)
            ).sum()
        ),
    )
    print("CPT dates eligible for hybrid timing:", int(events["cpt_within_interval_90"].sum()))


if __name__ == "__main__":
    main()
