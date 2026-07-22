#!/usr/bin/env python3
"""Clinical-translation upgrade analyses for the stage-linked OA manuscript.

This script adds reviewer-facing analyses requested for clinical translation,
model interpretability, recalibration, and deployability. It does not overwrite
the existing manuscript package.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.special import expit, logit
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path("/Users/hehang/Downloads/时间序列预测模型/膝关节炎")
BASE = ROOT / "stage_specific_progression_framework" / "complete_project_analysis"
DATA = ROOT / "stage_specific_progression_framework" / "data_reorganized"
OUT = BASE / "three_stage_bridge_transport_manuscript" / "clinical_translation_upgrade_20260722"
TABLES = OUT / "tables"
FIGS = OUT / "figures"

COL = {
    "blue": "#2F6F97",
    "red": "#C83E50",
    "green": "#2E8B57",
    "gold": "#E3B23C",
    "gray": "#6B6B6B",
    "light": "#D9EAF7",
    "purple": "#6A4C93",
}


def ensure_dirs() -> None:
    for folder in [OUT, TABLES, FIGS]:
        folder.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")


def safe_auc(y: np.ndarray, p: np.ndarray) -> float:
    if len(np.unique(y)) < 2:
        return np.nan
    return float(roc_auc_score(y, p))


def calibration_intercept_slope(y: np.ndarray, p: np.ndarray) -> tuple[float, float]:
    y = np.asarray(y, dtype=int)
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    if len(np.unique(y)) < 2:
        return np.nan, np.nan
    try:
        fit = sm.Logit(y, sm.add_constant(logit(p))).fit(disp=False, maxiter=200)
        return float(fit.params[0]), float(fit.params[1])
    except Exception:
        return np.nan, np.nan


def metric_dict(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    y = np.asarray(y, dtype=int)
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    intercept, slope = calibration_intercept_slope(y, p)
    return {
        "auc": safe_auc(y, p),
        "brier": float(brier_score_loss(y, p)),
        "observed_risk": float(np.mean(y)),
        "mean_predicted_risk": float(np.mean(p)),
        "oe_ratio": float(np.mean(y) / np.mean(p)) if np.mean(p) > 0 else np.nan,
        "calibration_intercept": intercept,
        "calibration_slope": slope,
    }


def bootstrap_metrics(df: pd.DataFrame, y_col: str, p_col: str, group_col: str,
                      n_boot: int = 400, seed: int = 20260722) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    group_values = df[group_col].astype(str).to_numpy()
    groups = pd.unique(group_values)
    group_to_idx = {g: np.flatnonzero(group_values == g) for g in groups}
    y_all = df[y_col].to_numpy()
    p_all = df[p_col].to_numpy()
    rows: list[dict[str, float]] = []
    for _ in range(n_boot):
        sampled = rng.choice(groups, size=len(groups), replace=True)
        idx = np.concatenate([group_to_idx[g] for g in sampled])
        y = y_all[idx]
        if len(np.unique(y)) < 2:
            continue
        rows.append(metric_dict(y, p_all[idx]))
    b = pd.DataFrame(rows)
    out = {}
    for key in ["auc", "brier", "observed_risk", "mean_predicted_risk", "oe_ratio",
                "calibration_intercept", "calibration_slope"]:
        if key in b and b[key].notna().any():
            out[f"{key}_l"] = float(b[key].quantile(0.025))
            out[f"{key}_u"] = float(b[key].quantile(0.975))
        else:
            out[f"{key}_l"] = np.nan
            out[f"{key}_u"] = np.nan
    return out


def fmt_ci(row: pd.Series, key: str, digits: int = 3) -> str:
    val = row.get(key, np.nan)
    lo = row.get(f"{key}_l", np.nan)
    hi = row.get(f"{key}_u", np.nan)
    if pd.isna(val):
        return ""
    if pd.isna(lo) or pd.isna(hi):
        return f"{val:.{digits}f}"
    return f"{val:.{digits}f} ({lo:.{digits}f}-{hi:.{digits}f})"


def mean_sd(series: pd.Series) -> str:
    x = pd.to_numeric(series, errors="coerce").dropna()
    if len(x) == 0:
        return "NA"
    return f"{x.mean():.1f} ({x.std(ddof=1):.1f})"


def n_pct(series: pd.Series) -> str:
    x = pd.to_numeric(series, errors="coerce").dropna()
    if len(x) == 0:
        return "NA"
    n = int((x == 1).sum())
    return f"{n} ({100 * n / len(x):.1f}%)"


def smd(a: pd.Series, b: pd.Series, binary: bool = False) -> float:
    a = pd.to_numeric(a, errors="coerce").dropna()
    b = pd.to_numeric(b, errors="coerce").dropna()
    if len(a) == 0 or len(b) == 0:
        return np.nan
    if binary:
        pa, pb = a.mean(), b.mean()
        pooled = math.sqrt((pa * (1 - pa) + pb * (1 - pb)) / 2)
        return (pa - pb) / pooled if pooled else np.nan
    pooled = math.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    return (a.mean() - b.mean()) / pooled if pooled else np.nan


def make_oai_outcome(df: pd.DataFrame, horizon: int = 60) -> pd.DataFrame:
    d = df.copy()
    d["time_months"] = pd.to_numeric(d["time_months"], errors="coerce")
    d["event_primary"] = pd.to_numeric(d["event_primary"], errors="coerce")
    eligible = (d["time_months"] >= horizon) | ((d["event_primary"] == 1) & (d["time_months"] <= horizon))
    d = d[eligible].copy()
    d[f"event_{horizon}m"] = ((d["event_primary"] == 1) & (d["time_months"] <= horizon)).astype(int)
    d["right_knee"] = d["side_label"].astype(str).str.lower().eq("right").astype(int)
    return d


def oai_incremental_analysis(oai: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = make_oai_outcome(oai, 60)
    d = d[d["core_model_f_complete"] == 1].copy()
    featuresets = [
        ("Model 1: demographics", ["age", "female", "right_knee"]),
        ("Model 2: + symptoms", ["age", "female", "right_knee", "pain_landmark_0_10"]),
        ("Model 3: + radiographic severity", ["age", "female", "right_knee", "pain_landmark_0_10", "kl_landmark"]),
        ("Model 4: + longitudinal change", [
            "age", "female", "right_knee", "pain_landmark_0_10", "kl_landmark",
            "pain_change_0_10", "kl_change",
        ]),
        ("Model 5: final penalized transportable model", [
            "age", "female", "right_knee", "pain_landmark_0_10", "kl_landmark",
            "pain_change_0_10", "kl_change",
        ]),
    ]
    y = d["event_60m"].to_numpy().astype(int)
    groups = d["patient_id"].astype(str).to_numpy()
    rows = []
    pred_frames = []
    previous_auc = np.nan
    previous_brier = np.nan

    for i, (name, features) in enumerate(featuresets, start=1):
        pred = np.full(len(d), np.nan)
        outer = GroupKFold(n_splits=5)
        for train_idx, test_idx in outer.split(d[features], y, groups):
            num_pipe = Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ])
            pre = ColumnTransformer([("num", num_pipe, features)], remainder="drop")
            if i < 5:
                clf = LogisticRegression(penalty="l2", C=1.0, solver="lbfgs", max_iter=5000)
                pipe = Pipeline([("pre", pre), ("model", clf)])
                pipe.fit(d.iloc[train_idx][features], y[train_idx])
            else:
                pipe = Pipeline([
                    ("pre", pre),
                    ("model", LogisticRegression(penalty="l2", solver="lbfgs", max_iter=5000)),
                ])
                inner = GroupKFold(n_splits=3)
                grid = GridSearchCV(
                    pipe,
                    {"model__C": [0.03, 0.1, 0.3, 1.0, 3.0, 10.0]},
                    scoring="neg_brier_score",
                    cv=inner,
                    n_jobs=1,
                )
                grid.fit(d.iloc[train_idx][features], y[train_idx], groups=groups[train_idx])
                pipe = grid.best_estimator_
            pred[test_idx] = pipe.predict_proba(d.iloc[test_idx][features])[:, 1]

        tmp = pd.DataFrame({
            "model": name,
            "patient_id": d["patient_id"].astype(str).to_numpy(),
            "knee_id": d["knee_id"].astype(str).to_numpy(),
            "y": y,
            "predicted_risk": pred,
        })
        metrics = metric_dict(y, pred)
        metrics.update(bootstrap_metrics(tmp, "y", "predicted_risk", "patient_id", n_boot=200, seed=20260722 + i))
        ll = float(np.sum(y * np.log(np.clip(pred, 1e-6, 1 - 1e-6)) +
                          (1 - y) * np.log(np.clip(1 - pred, 1e-6, 1 - 1e-6))))
        row = {
            "domain_step": i,
            "model": name,
            "predictor_domains": "; ".join(features),
            "knees": len(d),
            "patients": d["patient_id"].nunique(),
            "events": int(y.sum()),
            "event_rate": float(y.mean()),
            "auc": metrics["auc"],
            "auc_95ci": fmt_ci(pd.Series(metrics), "auc"),
            "delta_auc": metrics["auc"] - previous_auc if not pd.isna(previous_auc) else np.nan,
            "brier": metrics["brier"],
            "brier_95ci": fmt_ci(pd.Series(metrics), "brier"),
            "delta_brier": metrics["brier"] - previous_brier if not pd.isna(previous_brier) else np.nan,
            "calibration_intercept": metrics["calibration_intercept"],
            "calibration_slope": metrics["calibration_slope"],
            "observed_risk": metrics["observed_risk"],
            "mean_predicted_risk": metrics["mean_predicted_risk"],
            "o_over_e": metrics["oe_ratio"],
            "cv_log_likelihood": ll,
        }
        rows.append(row)
        pred_frames.append(tmp)
        previous_auc = metrics["auc"]
        previous_brier = metrics["brier"]

    out = pd.DataFrame(rows)
    out["incremental_lr_statistic_vs_previous_oof"] = np.nan
    for idx in range(1, len(out)):
        out.loc[idx, "incremental_lr_statistic_vs_previous_oof"] = 2 * (
            out.loc[idx, "cv_log_likelihood"] - out.loc[idx - 1, "cv_log_likelihood"]
        )
    return out, pd.concat(pred_frames, ignore_index=True)


def oai_threshold_table(pred_df: pd.DataFrame) -> pd.DataFrame:
    d = pred_df[pred_df["model"] == "Model 5: final penalized transportable model"].copy()
    rows = []
    for threshold in [0.10, 0.20, 0.30]:
        high = d["predicted_risk"] >= threshold
        y = d["y"].astype(int)
        tp = int((high & (y == 1)).sum())
        fp = int((high & (y == 0)).sum())
        fn = int((~high & (y == 1)).sum())
        tn = int((~high & (y == 0)).sum())
        rows.append({
            "threshold": threshold,
            "high_risk_knees": int(high.sum()),
            "high_risk_percent": float(high.mean()),
            "events_captured": tp,
            "events_captured_percent": float(tp / max(int(y.sum()), 1)),
            "sensitivity": float(tp / max(tp + fn, 1)),
            "specificity": float(tn / max(tn + fp, 1)),
            "ppv": float(tp / max(tp + fp, 1)),
            "npv": float(tn / max(tn + fn, 1)),
            "net_benefit": float(tp / len(d) - fp / len(d) * threshold / (1 - threshold)),
        })
    return pd.DataFrame(rows)


def oai_coefficient_stability(oai: pd.DataFrame, n_boot: int = 300) -> pd.DataFrame:
    d = make_oai_outcome(oai, 60)
    d = d[d["core_model_f_complete"] == 1].copy()
    features = ["age", "female", "right_knee", "pain_landmark_0_10", "kl_landmark", "pain_change_0_10", "kl_change"]
    y_col = "event_60m"
    rng = np.random.default_rng(20260722)
    patient_values = d["patient_id"].astype(str).to_numpy()
    patients = pd.unique(patient_values)
    patient_to_idx = {p: np.flatnonzero(patient_values == p) for p in patients}
    coefs = []
    for b in range(n_boot):
        sampled = rng.choice(patients, size=len(patients), replace=True)
        idx = np.concatenate([patient_to_idx[p] for p in sampled])
        boot = d.iloc[idx]
        if boot[y_col].nunique() < 2:
            continue
        pipe = Pipeline([
            ("pre", ColumnTransformer([
                ("num", Pipeline([
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", StandardScaler()),
                ]), features),
            ])),
            ("model", LogisticRegression(penalty="l2", C=0.3, solver="lbfgs", max_iter=5000)),
        ])
        pipe.fit(boot[features], boot[y_col].astype(int))
        row = {"bootstrap": b}
        for term, coef in zip(features, pipe.named_steps["model"].coef_[0]):
            row[term] = coef
        coefs.append(row)
    coef_df = pd.DataFrame(coefs)
    rows = []
    for term in features:
        vals = coef_df[term].dropna()
        rows.append({
            "term": term,
            "median_coefficient": float(vals.median()),
            "ci_2_5": float(vals.quantile(0.025)),
            "ci_97_5": float(vals.quantile(0.975)),
            "sign_consistency_percent": float(100 * max((vals > 0).mean(), (vals < 0).mean())),
            "nonzero_selection_frequency_percent": 100.0,
            "bootstrap_repetitions": len(vals),
            "note": "Ridge-penalized model; coefficients are shrunken but not selected to exact zero.",
        })
    return pd.DataFrame(rows)


def gbm_interpretability(oai: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = make_oai_outcome(oai, 60)
    d = d[d["core_model_f_complete"] == 1].copy()
    features = ["age", "female", "right_knee", "pain_landmark_0_10", "kl_landmark", "pain_change_0_10", "kl_change"]
    y = d["event_60m"].astype(int).to_numpy()
    X = d[features].copy()
    pre = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    model = Pipeline([
        ("pre", ColumnTransformer([("num", pre, features)])),
        ("model", HistGradientBoostingClassifier(max_iter=150, learning_rate=0.04, max_leaf_nodes=15, random_state=20260722)),
    ])
    model.fit(X, y)
    p = model.predict_proba(X)[:, 1]
    perf = pd.DataFrame([{
        "model": "Gradient boosting interpretability benchmark",
        "scope": "Secondary explanatory analysis only; not selected as the deployable model.",
        **metric_dict(y, p),
    }])
    perm = permutation_importance(model, X, y, scoring="roc_auc", n_repeats=40, random_state=20260722, n_jobs=1)
    importance = pd.DataFrame({
        "feature": features,
        "permutation_auc_drop_mean": perm.importances_mean,
        "permutation_auc_drop_sd": perm.importances_std,
    }).sort_values("permutation_auc_drop_mean", ascending=False)
    return perf, importance


def secondary_rf_shap(oai: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    try:
        import shap
    except Exception:
        return pd.DataFrame([{
            "status": "SHAP not available",
            "note": "The shap package could not be imported in the active Python environment.",
        }]), None

    d = make_oai_outcome(oai, 60)
    d = d[d["core_model_f_complete"] == 1].copy()
    features = ["age", "female", "right_knee", "pain_landmark_0_10", "kl_landmark", "pain_change_0_10", "kl_change"]
    X = d[features].copy()
    y = d["event_60m"].astype(int).to_numpy()
    imputer = SimpleImputer(strategy="median")
    X_imp = pd.DataFrame(imputer.fit_transform(X), columns=features)
    rf = RandomForestClassifier(
        n_estimators=300,
        min_samples_leaf=20,
        max_features="sqrt",
        class_weight="balanced_subsample",
        random_state=20260722,
        n_jobs=-1,
    )
    rf.fit(X_imp, y)

    rng = np.random.default_rng(20260722)
    background_idx = rng.choice(np.arange(len(X_imp)), size=min(200, len(X_imp)), replace=False)
    explain_idx = rng.choice(np.arange(len(X_imp)), size=min(500, len(X_imp)), replace=False)
    explainer = shap.TreeExplainer(rf, data=X_imp.iloc[background_idx], model_output="probability")
    shap_values = explainer(X_imp.iloc[explain_idx], check_additivity=False)
    values = shap_values.values
    if values.ndim == 3:
        values = values[:, :, 1]
    mean_abs = np.abs(values).mean(axis=0)
    shap_table = pd.DataFrame({
        "feature": features,
        "mean_absolute_shap_probability": mean_abs,
    }).sort_values("mean_absolute_shap_probability", ascending=False)
    shap_table["status"] = "Computed for secondary random-forest interpretability benchmark"
    shap_table["note"] = "SHAP values are on the probability scale; this model is not the deployable model."

    ordered = shap_table["feature"].tolist()
    values_df = pd.DataFrame(values, columns=features)
    plot_data = []
    for feature in ordered:
        vals = values_df[feature].to_numpy()
        raw = X_imp.iloc[explain_idx][feature].to_numpy()
        if np.nanmax(raw) > np.nanmin(raw):
            raw_scaled = (raw - np.nanmin(raw)) / (np.nanmax(raw) - np.nanmin(raw))
        else:
            raw_scaled = np.zeros_like(raw)
        for v, r in zip(vals, raw_scaled):
            plot_data.append({"feature": feature, "shap": v, "value_scaled": r})
    plot_df = pd.DataFrame(plot_data)

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.3), gridspec_kw={"width_ratios": [0.9, 1.1]})
    top = shap_table.sort_values("mean_absolute_shap_probability").tail(7)
    axes[0].barh(top["feature"], top["mean_absolute_shap_probability"], color=COL["purple"])
    axes[0].set_xlabel("Mean |SHAP|")
    axes[0].set_title("A. Global importance")
    y_map = {feature: i for i, feature in enumerate(ordered[::-1])}
    rng2 = np.random.default_rng(13)
    y_pos = plot_df["feature"].map(y_map).to_numpy() + rng2.normal(0, 0.07, len(plot_df))
    sc = axes[1].scatter(plot_df["shap"], y_pos, c=plot_df["value_scaled"], cmap="viridis", s=8, alpha=0.55, linewidths=0)
    axes[1].axvline(0, color="#333333", lw=0.9, ls="--")
    axes[1].set_yticks(range(len(ordered)))
    axes[1].set_yticklabels(ordered[::-1])
    axes[1].set_xlabel("SHAP contribution to predicted probability")
    axes[1].set_title("B. SHAP distribution")
    cbar = fig.colorbar(sc, ax=axes[1], fraction=0.046, pad=0.04)
    cbar.set_label("Feature value (scaled)")
    fig.suptitle("Secondary nonlinear model SHAP explanation", fontsize=12, weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.91])
    fig.savefig(FIGS / "figure_s22_secondary_rf_shap_interpretability.png", dpi=600)
    fig.savefig(FIGS / "figure_s22_secondary_rf_shap_interpretability.pdf")
    plt.close(fig)
    return shap_table, plot_df


def check_missingness_bias() -> pd.DataFrame:
    raw = read_csv(ROOT / "derived" / "CHECK" / "check_knee_level_first_pass.csv")
    d = pd.DataFrame({
        "patient_id": raw["nsin"].astype(str),
        "knee_id": raw["knee_id"].astype(str),
        "age": pd.to_numeric(raw["baseline_age"], errors="coerce"),
        "female": pd.to_numeric(raw["sex_code"], errors="coerce").eq(2).astype(float),
        "bmi": pd.to_numeric(raw["baseline_bmi"], errors="coerce"),
        "pain": pd.to_numeric(raw["baseline_womac_pain"], errors="coerce"),
        "function": pd.to_numeric(raw["baseline_womac_function"], errors="coerce"),
        "baseline_kl1": pd.to_numeric(raw["kl_t0"], errors="coerce").eq(1).astype(float),
        "kl_t0": pd.to_numeric(raw["kl_t0"], errors="coerce"),
        "kl_t8": pd.to_numeric(raw["kl_t8"], errors="coerce"),
    })
    d = d[d["kl_t0"].isin([0, 1])].copy()
    d["available_96m_radiograph"] = d["kl_t8"].notna().astype(int)
    rows = []
    variables = [
        ("age", "Age", False),
        ("female", "Female", True),
        ("bmi", "BMI", False),
        ("pain", "Baseline WOMAC pain", False),
        ("function", "Baseline WOMAC function", False),
        ("baseline_kl1", "Baseline KL1", True),
    ]
    avail = d[d["available_96m_radiograph"] == 1]
    miss = d[d["available_96m_radiograph"] == 0]
    for var, label, binary in variables:
        rows.append({
            "variable": label,
            "available_96m_knees": len(avail),
            "missing_96m_knees": len(miss),
            "available_96m": n_pct(avail[var]) if binary else mean_sd(avail[var]),
            "missing_96m": n_pct(miss[var]) if binary else mean_sd(miss[var]),
            "smd_available_minus_missing": smd(avail[var], miss[var], binary=binary),
        })
    return pd.DataFrame(rows)


def pain_cutoff_and_timepoint_audit() -> tuple[pd.DataFrame, pd.DataFrame]:
    check = read_csv(ROOT / "derived" / "CHECK" / "check_knee_level_first_pass.csv")
    check24 = read_csv(BASE / "check_incident_oa_analysis" / "tables" / "check_incident_oa_24m_analysis_dataset.csv")
    oai_landmark = read_csv(ROOT / "derived" / "OAI" / "oai_24m_landmark_dataset.csv")
    oai_core = read_csv(DATA / "oai_plan_model_f_core.csv")

    c_early = check[pd.to_numeric(check["kl_t0"], errors="coerce").isin([0, 1])].copy()
    oai_early = oai_landmark[
        pd.to_numeric(oai_landmark["xray_sq_v00xrkl_num"], errors="coerce").isin([0, 1])
        & pd.to_numeric(oai_landmark["xray_24m_v03xrkl_num"], errors="coerce").notna()
    ].copy()
    rows = [
        {
            "analysis": "CHECK pain/KL display groups",
            "pain_variable": "baseline_womac_pain",
            "scale": "CHECK original WOMAC pain 0-20; higher=worse",
            "cutoff_rule": "High pain defined as > cohort median in baseline KL0/1 analytic population",
            "numeric_cutoff": float(pd.to_numeric(c_early["baseline_womac_pain"], errors="coerce").median()),
            "high_pain_knees": int((pd.to_numeric(c_early["baseline_womac_pain"], errors="coerce") > pd.to_numeric(c_early["baseline_womac_pain"], errors="coerce").median()).sum()),
            "analytic_knees": int(pd.to_numeric(c_early["baseline_womac_pain"], errors="coerce").notna().sum()),
        },
        {
            "analysis": "CHECK 24m final model input",
            "pain_variable": "pain",
            "scale": "CHECK analysis dataset retains original WOMAC pain scale used by the model script",
            "cutoff_rule": "Continuous model predictor; dichotomy used only for display groups",
            "numeric_cutoff": np.nan,
            "high_pain_knees": np.nan,
            "analytic_knees": int(len(check24)),
        },
        {
            "analysis": "OAI early KL0/1 directional replication",
            "pain_variable": "baseline_womac_pain_num",
            "scale": "OAI baseline WOMAC pain 0-20; higher=worse",
            "cutoff_rule": "High pain defined as > OAI KL0/1 subgroup median in bridge script",
            "numeric_cutoff": float(pd.to_numeric(oai_early["baseline_womac_pain_num"], errors="coerce").median()),
            "high_pain_knees": int((pd.to_numeric(oai_early["baseline_womac_pain_num"], errors="coerce") > pd.to_numeric(oai_early["baseline_womac_pain_num"], errors="coerce").median()).sum()),
            "analytic_knees": int(pd.to_numeric(oai_early["baseline_womac_pain_num"], errors="coerce").notna().sum()),
        },
        {
            "analysis": "OAI/MRKR transportable arthroplasty model",
            "pain_variable": "pain_landmark_0_10",
            "scale": "Harmonized 0-10 pain score; higher=worse",
            "cutoff_rule": "Continuous deployable model input; display strata use clinically labelled bins when needed",
            "numeric_cutoff": np.nan,
            "high_pain_knees": np.nan,
            "analytic_knees": int(oai_core["pain_landmark_0_10"].notna().sum()),
        },
    ]

    audit = pd.DataFrame([
        {
            "analysis": "OAI early bridge directional replication",
            "radiograph_origin": "Baseline screening/radiograph KL and exact 24-month follow-up KL",
            "columns_used": "xray_sq_v00xrkl_num -> xray_24m_v03xrkl_num",
            "time_origin": "OAI baseline",
            "clinical_interpretation": "Early KL0/1 to incident definite radiographic OA at 24 months",
        },
        {
            "analysis": "OAI arthroplasty model development",
            "radiograph_origin": "24-month landmark KL",
            "columns_used": "kl_landmark in oai_plan_model_f_core.csv",
            "time_origin": "OAI 24-month landmark",
            "clinical_interpretation": "Predicts target-knee TKA/KR within 60 months after landmark",
        },
        {
            "analysis": "OAI downstream KL-risk gradient in bridge figure",
            "radiograph_origin": "Baseline KL in the current bridge script; landmark KL sensitivity added here",
            "columns_used": "kl_baseline and kl_landmark",
            "time_origin": "Baseline for original gradient; 24-month landmark for sensitivity",
            "clinical_interpretation": "Shows increasing surgical risk across radiographic states; manuscript should label baseline vs landmark explicitly",
        },
        {
            "analysis": "MRKR transport/recalibration",
            "radiograph_origin": "Closest radiograph to 24-month landmark window",
            "columns_used": "kl_landmark in mrkr_plan_model_f_core.csv",
            "time_origin": "MRKR landmark radiograph",
            "clinical_interpretation": "Transport of OAI prognostic index to 24/36-month real-world arthroplasty horizons",
        },
    ])
    return pd.DataFrame(rows), audit


def oai_kl_gradient_sensitivity(oai: pd.DataFrame) -> pd.DataFrame:
    d = make_oai_outcome(oai, 60)

    def kl_cat(v: float) -> str:
        if pd.isna(v):
            return "Missing"
        if v in [0, 1]:
            return "KL0/1"
        if v == 2:
            return "KL2"
        if v == 3:
            return "KL3"
        if v >= 4:
            return "KL4"
        return "Other"

    rows = []
    for source, col in [("Baseline KL", "kl_baseline"), ("24-month landmark KL", "kl_landmark")]:
        d["kl_category"] = pd.to_numeric(d[col], errors="coerce").map(kl_cat)
        for cat in ["KL0/1", "KL2", "KL3", "KL4"]:
            g = d[d["kl_category"] == cat]
            rows.append({
                "kl_timepoint": source,
                "kl_category": cat,
                "knees": len(g),
                "patients": g["patient_id"].nunique(),
                "events_60m": int(g["event_60m"].sum()),
                "risk_60m": float(g["event_60m"].mean()) if len(g) else np.nan,
            })
    return pd.DataFrame(rows)


def mrkr_early_event_sensitivity(mrkr: pd.DataFrame, pred: pd.DataFrame) -> pd.DataFrame:
    core = mrkr[["patient_id", "knee_id", "time_months", "event_primary"]].copy()
    core["patient_id"] = core["patient_id"].astype(str)
    core["knee_id"] = core["knee_id"].astype(str)
    rows = []
    for horizon in [24, 36]:
        ph = pred[pred["target_horizon_months"] == horizon].copy()
        ph["patient_id"] = ph["patient_id"].astype(str)
        ph["knee_id"] = ph["knee_id"].astype(str)
        merged = ph.merge(core, on=["patient_id", "knee_id"], how="left")
        for exclusion in [0, 6, 12]:
            keep = ~((merged["event_primary"] == 1) & (merged["time_months"] <= exclusion))
            subset = merged[keep].copy()
            subset["y_sensitivity"] = ((subset["event_primary"] == 1) & (subset["time_months"] <= horizon)).astype(int)
            base_lp = None
            for method in ["none", "intercept_recalibration", "logistic_recalibration"]:
                d = subset[subset["recalibration_method"] == method].copy()
                d["predicted_risk"] = np.clip(d["predicted_risk"], 1e-6, 1 - 1e-6)
                m = metric_dict(d["y_sensitivity"].to_numpy(), d["predicted_risk"].to_numpy())
                boot = bootstrap_metrics(
                    d.rename(columns={"y_sensitivity": "y_boot"}),
                    "y_boot",
                    "predicted_risk",
                    "patient_id",
                    n_boot=200,
                    seed=20260722 + horizon + exclusion,
                )
                m.update(boot)
                alpha = beta = np.nan
                if method == "none":
                    base_lp = logit(d["predicted_risk"].to_numpy())
                    alpha, beta = m["calibration_intercept"], m["calibration_slope"]
                elif base_lp is not None:
                    pass
                rows.append({
                    "target_horizon_months": horizon,
                    "excluded_events_within_months": exclusion,
                    "recalibration_method": method,
                    "knees": len(d),
                    "patients": d["patient_id"].nunique(),
                    "events": int(d["y_sensitivity"].sum()),
                    "observed_risk": m["observed_risk"],
                    "mean_predicted_risk": m["mean_predicted_risk"],
                    "auc": m["auc"],
                    "auc_95ci": fmt_ci(pd.Series(m), "auc"),
                    "brier": m["brier"],
                    "brier_95ci": fmt_ci(pd.Series(m), "brier"),
                    "oe_ratio": m["oe_ratio"],
                    "calibration_intercept": m["calibration_intercept"],
                    "calibration_slope": m["calibration_slope"],
                    "recalibration_alpha_if_updating_original_index": alpha,
                    "recalibration_beta_if_updating_original_index": beta,
                })
    return pd.DataFrame(rows)


def make_figures(incremental: pd.DataFrame, missing: pd.DataFrame, mrkr_sens: pd.DataFrame,
                 kl_grad: pd.DataFrame, coef_stability: pd.DataFrame,
                 gbm_importance: pd.DataFrame) -> None:
    plt.rcParams.update({
        "font.family": "Arial",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
    })

    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8))
    x = np.arange(len(incremental))
    axes[0].plot(x, incremental["auc"], marker="o", color=COL["blue"], lw=2)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels([f"M{i}" for i in incremental["domain_step"]])
    axes[0].set_ylabel("OOF AUC")
    axes[0].set_title("A. Discrimination by predictor domain")
    axes[0].grid(axis="y", alpha=0.25)
    axes[1].plot(x, incremental["brier"], marker="o", color=COL["red"], lw=2)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([f"M{i}" for i in incremental["domain_step"]])
    axes[1].set_ylabel("OOF Brier score")
    axes[1].set_title("B. Probability accuracy")
    axes[1].grid(axis="y", alpha=0.25)
    fig.suptitle("OAI 60-month TKA/KR predictor-domain incremental value", weight="bold", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.savefig(FIGS / "figure_s15_oai_predictor_domain_incremental_value.png", dpi=600)
    fig.savefig(FIGS / "figure_s15_oai_predictor_domain_incremental_value.pdf")
    plt.close(fig)

    m = missing.sort_values("smd_available_minus_missing")
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    ax.axvspan(-0.1, 0.1, color=COL["light"], alpha=0.45)
    ax.axvline(-0.1, color=COL["gray"], ls="--", lw=1)
    ax.axvline(0.1, color=COL["gray"], ls="--", lw=1)
    ax.scatter(m["smd_available_minus_missing"], m["variable"], color=COL["blue"], s=48)
    ax.set_xlabel("SMD: 96m radiograph available minus missing")
    ax.set_title("CHECK 96-month radiograph availability audit", fontsize=11, weight="bold")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGS / "figure_s16_check_96m_radiograph_missingness_smd.png", dpi=600)
    fig.savefig(FIGS / "figure_s16_check_96m_radiograph_missingness_smd.pdf")
    plt.close(fig)

    plot_df = mrkr_sens[mrkr_sens["recalibration_method"].isin(["none", "logistic_recalibration"])].copy()
    labels = {"none": "Original OAI index", "logistic_recalibration": "Logistic recalibration"}
    colors = {"none": COL["gray"], "logistic_recalibration": COL["red"]}
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.8), sharex=True)
    for method, d in plot_df.groupby("recalibration_method"):
        d24 = d[d["target_horizon_months"] == 24]
        axes[0].plot(d24["excluded_events_within_months"], d24["brier"], marker="o", label=labels[method], color=colors[method])
        d36 = d[d["target_horizon_months"] == 36]
        axes[1].plot(d36["excluded_events_within_months"], d36["brier"], marker="o", label=labels[method], color=colors[method])
    for ax, h in zip(axes, [24, 36]):
        ax.set_title(f"{h}-month target")
        ax.set_xlabel("Excluded events within first x months")
        ax.set_ylabel("Brier score")
        ax.grid(axis="y", alpha=0.25)
    axes[1].legend(frameon=False, fontsize=8)
    fig.suptitle("MRKR early-event exclusion sensitivity", weight="bold", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.savefig(FIGS / "figure_s17_mrkr_early_event_exclusion_sensitivity.png", dpi=600)
    fig.savefig(FIGS / "figure_s17_mrkr_early_event_exclusion_sensitivity.pdf")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.7, 4.2))
    for source, color in [("Baseline KL", COL["gray"]), ("24-month landmark KL", COL["blue"])]:
        d = kl_grad[kl_grad["kl_timepoint"] == source]
        ax.plot(d["kl_category"], d["risk_60m"] * 100, marker="o", lw=2, color=color, label=source)
    ax.set_ylabel("Observed 60m TKA/KR risk (%)")
    ax.set_title("OAI KL timepoint sensitivity for downstream risk gradient", fontsize=11, weight="bold")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIGS / "figure_s18_oai_kl_timepoint_gradient_sensitivity.png", dpi=600)
    fig.savefig(FIGS / "figure_s18_oai_kl_timepoint_gradient_sensitivity.pdf")
    plt.close(fig)

    c = coef_stability.sort_values("median_coefficient")
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    y = np.arange(len(c))
    ax.errorbar(
        c["median_coefficient"],
        y,
        xerr=[c["median_coefficient"] - c["ci_2_5"], c["ci_97_5"] - c["median_coefficient"]],
        fmt="o",
        color=COL["blue"],
        ecolor=COL["gray"],
        capsize=3,
    )
    ax.axvline(0, color="#333333", ls="--", lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels(c["term"])
    ax.set_xlabel("Bootstrap coefficient, standardized scale")
    ax.set_title("OAI final model coefficient stability", fontsize=11, weight="bold")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGS / "figure_s19_oai_final_model_coefficient_stability.png", dpi=600)
    fig.savefig(FIGS / "figure_s19_oai_final_model_coefficient_stability.pdf")
    plt.close(fig)

    top = gbm_importance.sort_values("permutation_auc_drop_mean").tail(7)
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    ax.barh(top["feature"], top["permutation_auc_drop_mean"], xerr=top["permutation_auc_drop_sd"], color=COL["purple"])
    ax.set_xlabel("Permutation AUC drop")
    ax.set_title("Secondary nonlinear model interpretability benchmark", fontsize=11, weight="bold")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGS / "figure_s20_gbm_permutation_importance_interpretability.png", dpi=600)
    fig.savefig(FIGS / "figure_s20_gbm_permutation_importance_interpretability.pdf")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    ax.axis("off")
    boxes = [
        (0.10, "OAI fixed\nprognostic index", COL["blue"]),
        (0.34, "MRKR target\nhorizon split", COL["gold"]),
        (0.58, "Patient-grouped\nOOF recalibration", COL["red"]),
        (0.82, "Held-out\nabsolute risk", COL["green"]),
    ]
    for x0, label, color in boxes:
        ax.text(x0, 0.55, label, ha="center", va="center", fontsize=10,
                bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=color, lw=2))
    for start, end in [(0.20, 0.28), (0.44, 0.52), (0.68, 0.76)]:
        ax.annotate("", xy=(end, 0.55), xytext=(start, 0.55),
                    arrowprops=dict(arrowstyle="->", lw=2, color="#444444"))
    ax.text(0.58, 0.16, "Recalibration fitted in training patients and evaluated in held-out patients", ha="center", fontsize=8.5, color="#444444")
    ax.set_title("MRKR recalibration workflow for deployable absolute-risk updating", fontsize=12, weight="bold")
    fig.tight_layout()
    fig.savefig(FIGS / "figure_s21_mrkr_oof_recalibration_workflow.png", dpi=600)
    fig.savefig(FIGS / "figure_s21_mrkr_oof_recalibration_workflow.pdf")
    plt.close(fig)


def make_summary_md(paths: dict[str, Path]) -> None:
    text = f"""# Clinical translation upgrade analysis summary

Generated on 2026-07-22.

## Main additions

1. OAI predictor-domain incremental analysis separates demographics, symptoms, radiographic severity, longitudinal change, and the final penalized model.
2. MRKR early-event exclusion sensitivity evaluates whether near-term arthroplasty events already on the surgical pathway drive transport performance.
3. CHECK 96-month radiograph availability is audited with baseline SMDs to address potential informative attrition.
4. Pain-cutoff and KL-timepoint audits clarify scale, threshold rules, and the distinction between OAI baseline KL and 24-month landmark KL.
5. A secondary nonlinear interpretability benchmark is reported by permutation importance; this is not promoted as the deployable model.

## Key output folders

- Tables: `{TABLES}`
- Figures: `{FIGS}`

## Recommended manuscript placement

- Main text/Table 4 extension: `table_s15_oai_predictor_domain_incremental_value.csv`
- Supplement: S15-S21 tables and figures generated in this folder.
- Methods: explicitly state that the deployable research calculator should use the OAI 60-month final penalized model only; MRKR recalibration is target-setting evidence, not a standalone calculator.
"""
    (OUT / "clinical_translation_upgrade_summary.md").write_text(text, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    oai = read_csv(DATA / "oai_plan_model_f_core.csv")
    mrkr = read_csv(DATA / "mrkr_plan_model_f_core.csv")
    pred = read_csv(BASE / "tables" / "oai_to_mrkr_transport_predictions.csv")

    incremental, incremental_pred = oai_incremental_analysis(oai)
    write_csv(incremental, TABLES / "table_s15_oai_predictor_domain_incremental_value.csv")
    write_csv(incremental_pred, TABLES / "machine_readable_oai_incremental_oof_predictions.csv")

    threshold = oai_threshold_table(incremental_pred)
    write_csv(threshold, TABLES / "table_s16_oai_clinical_threshold_utility.csv")

    coef_stability = oai_coefficient_stability(oai, n_boot=200)
    write_csv(coef_stability, TABLES / "table_s17_oai_final_model_coefficient_stability.csv")

    gbm_perf, gbm_importance = gbm_interpretability(oai)
    write_csv(gbm_perf, TABLES / "table_s18_secondary_gbm_interpretability_performance.csv")
    write_csv(gbm_importance, TABLES / "table_s19_secondary_gbm_permutation_importance.csv")

    shap_table, shap_plot = secondary_rf_shap(oai)
    write_csv(shap_table, TABLES / "table_s25_secondary_rf_shap_importance.csv")
    if shap_plot is not None:
        write_csv(shap_plot, TABLES / "machine_readable_secondary_rf_shap_values_sample.csv")

    missing = check_missingness_bias()
    write_csv(missing, TABLES / "table_s20_check_96m_radiograph_availability_bias.csv")

    pain, timepoint = pain_cutoff_and_timepoint_audit()
    write_csv(pain, TABLES / "table_s21_pain_cutoff_scale_harmonization_audit.csv")
    write_csv(timepoint, TABLES / "table_s22_oai_kl_timepoint_audit.csv")

    kl_grad = oai_kl_gradient_sensitivity(oai)
    write_csv(kl_grad, TABLES / "table_s23_oai_kl_timepoint_gradient_sensitivity.csv")

    mrkr_sens = mrkr_early_event_sensitivity(mrkr, pred)
    write_csv(mrkr_sens, TABLES / "table_s24_mrkr_early_event_exclusion_sensitivity.csv")

    make_figures(incremental, missing, mrkr_sens, kl_grad, coef_stability, gbm_importance)
    make_summary_md({})
    print(f"Wrote clinical translation upgrade outputs to: {OUT}")


if __name__ == "__main__":
    main()
