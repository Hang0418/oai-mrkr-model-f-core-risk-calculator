#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"
LATEST = TABLES / "latest_framework"


def binary_auc(y: np.ndarray, score: np.ndarray) -> float:
    ok = np.isfinite(y) & np.isfinite(score)
    y = y[ok].astype(int)
    score = score[ok]
    n1 = int((y == 1).sum())
    n0 = int((y == 0).sum())
    if not n1 or not n0:
        return np.nan
    ranks = pd.Series(score).rank(method="average").to_numpy()
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def time_auc(time: np.ndarray, event: np.ndarray, score: np.ndarray, horizon: float) -> float:
    status = np.full(len(time), np.nan)
    status[(event == 1) & (time <= horizon)] = 1
    status[time > horizon] = 0
    return binary_auc(status, score)


def km_risk(time: np.ndarray, event: np.ndarray, horizon: float) -> tuple[float, float, float]:
    order = np.argsort(time)
    time = np.asarray(time, dtype=float)[order]
    event = np.asarray(event, dtype=int)[order]
    surv = 1.0
    greenwood = 0.0
    for t in np.unique(time[(event == 1) & (time <= horizon)]):
        n = int((time >= t).sum())
        d = int(((time == t) & (event == 1)).sum())
        if n == 0:
            continue
        surv *= 1 - d / n
        if n > d:
            greenwood += d / (n * (n - d))
    se = surv * np.sqrt(greenwood)
    risk = 1 - surv
    return risk, max(0.0, risk - 1.96 * se), min(1.0, risk + 1.96 * se)


def grouped_calibration(
    data: pd.DataFrame,
    risk_col: str,
    time_col: str,
    event_col: str,
    id_col: str,
    horizon: float,
    groups: int = 10,
) -> pd.DataFrame:
    d = data.copy()
    d["group"] = pd.qcut(d[risk_col], groups, labels=False, duplicates="drop") + 1
    rows = []
    for group, z in d.groupby("group", sort=True):
        risk, low, high = km_risk(z[time_col].to_numpy(), z[event_col].to_numpy(), horizon)
        rows.append(
            {
                "group": int(group),
                "knees": len(z),
                "patients": z[id_col].nunique(),
                "events_by_horizon": int(((z[event_col] == 1) & (z[time_col] <= horizon)).sum()),
                "mean_predicted_risk": z[risk_col].mean(),
                "observed_risk": risk,
                "observed_lower_95": low,
                "observed_upper_95": high,
            }
        )
    return pd.DataFrame(rows)


def prepare_oai() -> None:
    d = pd.read_csv(TABLES / "reviewer_round2_oai_cv_predictions.csv")
    horizons = [12, 24, 36, 60]
    estimates = {
        h: time_auc(d.time.to_numpy(), d.event.to_numpy(), d.risk_e_60m.to_numpy(), h)
        for h in horizons
    }
    ids = d.id.unique()
    rng = np.random.default_rng(20260723)
    boot = {h: [] for h in horizons}
    by_id = {pid: np.flatnonzero(d.id.to_numpy() == pid) for pid in ids}
    for _ in range(500):
        sampled = rng.choice(ids, size=len(ids), replace=True)
        idx = np.concatenate([by_id[pid] for pid in sampled])
        for h in horizons:
            boot[h].append(
                time_auc(
                    d.time.to_numpy()[idx],
                    d.event.to_numpy()[idx],
                    d.risk_e_60m.to_numpy()[idx],
                    h,
                )
            )
    rows = []
    for h in horizons:
        values = np.asarray(boot[h], dtype=float)
        rows.append(
            {
                "horizon_months": h,
                "auc": estimates[h],
                "lower_95": np.nanquantile(values, 0.025),
                "upper_95": np.nanquantile(values, 0.975),
                "events": int(((d.event == 1) & (d.time <= h)).sum()),
                "at_risk": int((d.time >= h).sum()),
                "evaluation": "Pooled participant-level 10-fold out-of-sample predictions",
                "interval_method": "500 participant-clustered bootstrap resamples",
            }
        )
    pd.DataFrame(rows).to_csv(LATEST / "revised_figure3_oai_cv_horizon_auc.csv", index=False)

    deciles = grouped_calibration(d, "risk_e_60m", "time", "event", "id", 60)
    deciles.to_csv(LATEST / "revised_figure3_oai_cv_calibration_deciles.csv", index=False)

    d["risk_quartile"] = pd.qcut(d.risk_e_60m, 4, labels=["Q1", "Q2", "Q3", "Q4"])
    d.to_csv(LATEST / "revised_figure3_oai_cv_risk_predictions.csv", index=False)
    rows = []
    for quartile, z in d.groupby("risk_quartile", observed=True):
        rows.append(
            {
                "risk_quartile": quartile,
                "knees": len(z),
                "participants": z.id.nunique(),
                "events_total": int(z.event.sum()),
                "events_by_60m": int(((z.event == 1) & (z.time <= 60)).sum()),
                "risk_min": z.risk_e_60m.min(),
                "risk_max": z.risk_e_60m.max(),
                **{f"at_risk_{h}m": int((z.time >= h).sum()) for h in [0, 24, 60, 120]},
            }
        )
    pd.DataFrame(rows).to_csv(LATEST / "revised_figure3_oai_cv_quartile_summary.csv", index=False)


def prepare_mrkr() -> None:
    d = pd.read_csv(TABLES / "reviewer_round2_mrkr_oos_predictions.csv")
    original = grouped_calibration(
        d, "risk_original_24m", "time_months", "event_primary", "patient_id", 24
    )
    original["analysis"] = "Original OAI-derived Model F-core"
    updated = grouped_calibration(
        d, "risk_oos_24m", "time_months", "event_primary", "patient_id", 24
    )
    updated["analysis"] = "Pooled out-of-sample recalibrated predictions"
    pd.concat([original, updated], ignore_index=True).to_csv(
        LATEST / "revised_figure5_mrkr_calibration_deciles.csv", index=False
    )

    strict = pd.read_csv(TABLES / "oai_mrkr_plan_mrkr_strict_sensitivity_24m.csv")
    rng = np.random.default_rng(20260724)
    rows = []
    for cutoff in [0, 3, 6, 12]:
        z = d.copy() if cutoff == 0 else d.loc[
            ~((d.event_primary == 1) & (d.time_months <= cutoff))
        ].copy()
        observed, low, high = km_risk(z.time_months.to_numpy(), z.event_primary.to_numpy(), 24)
        patients = z.patient_id.unique()
        by_id = {pid: np.flatnonzero(z.patient_id.to_numpy() == pid) for pid in patients}
        auc_boot = []
        for _ in range(300):
            sampled = rng.choice(patients, size=len(patients), replace=True)
            idx = np.concatenate([by_id[pid] for pid in sampled])
            auc_boot.append(
                time_auc(
                    z.time_months.to_numpy()[idx],
                    z.event_primary.to_numpy()[idx],
                    z.lp_f.to_numpy()[idx],
                    24,
                )
            )
        point = strict.loc[strict.cutoff_months.eq(cutoff)].iloc[0]
        rows.append(
            {
                "cutoff_months": cutoff,
                "definition": "Full cohort" if cutoff == 0 else f"Exclude ≤{cutoff} months",
                "knees": len(z),
                "patients": z.patient_id.nunique(),
                "events_by_24m": int(((z.event_primary == 1) & (z.time_months <= 24)).sum()),
                "observed_24m": observed,
                "observed_lower_95": low,
                "observed_upper_95": high,
                "auc_24m": point.auc_24m,
                "auc_lower_95": np.nanquantile(auc_boot, 0.025),
                "auc_upper_95": np.nanquantile(auc_boot, 0.975),
            }
        )
    pd.DataFrame(rows).to_csv(LATEST / "revised_figure5_mrkr_early_sensitivity.csv", index=False)


def main() -> None:
    prepare_oai()
    prepare_mrkr()
    print(LATEST)


if __name__ == "__main__":
    main()
