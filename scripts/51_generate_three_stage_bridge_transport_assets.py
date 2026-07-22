from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.transforms as mtransforms
import statsmodels.api as sm
from sklearn.base import clone
from sklearn.metrics import roc_curve, roc_auc_score, brier_score_loss
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, GroupKFold


BASE = Path("/Users/hehang/Downloads/时间序列预测模型/膝关节炎/stage_specific_progression_framework/complete_project_analysis")
OUT = BASE / "three_stage_bridge_transport_manuscript"
FIGS = OUT / "figures"
TABLES = OUT / "tables"
SUPP_FIGS = OUT / "supplementary_figures"
SUPP_TABLES = OUT / "supplementary_tables"
MANUSCRIPT = OUT / "manuscript"
EXTERNAL_FIGURE1 = Path("/Users/hehang/Downloads/Figure1_stage_linked_framework_highres.pdf")

COL = {"blue": "#2F6F97", "red": "#C83E50", "green": "#2E8B57", "gold": "#F2C14E", "gray": "#6B6B6B", "light": "#EAF3F8"}


def ensure_dirs() -> None:
    for d in [FIGS, TABLES, SUPP_FIGS, SUPP_TABLES, MANUSCRIPT]:
        d.mkdir(parents=True, exist_ok=True)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return np.nan, np.nan
    p = k / n
    den = 1 + z**2 / n
    cen = (p + z**2 / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / den
    return max(0, cen - half), min(1, cen + half)


def calibration_points(y, p, q: int = 10) -> pd.DataFrame:
    d = pd.DataFrame({"y": y, "p": p})
    d["bin"] = pd.qcut(d.p, q=q, duplicates="drop")
    out = d.groupby("bin", observed=True).agg(pred=("p", "mean"), obs=("y", "mean"), n=("y", "size"), events=("y", "sum")).reset_index()
    ci = out.apply(lambda r: wilson(int(r.events), int(r.n)), axis=1, result_type="expand")
    out["lo"] = ci[0]
    out["hi"] = ci[1]
    return out


def logit(p):
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def logistic_update_params(y, p) -> pd.DataFrame:
    y = pd.Series(np.asarray(y, dtype=float), name="y")
    lp = pd.Series(logit(p), name="lp")
    fit = sm.GLM(y, sm.add_constant(lp), family=sm.families.Binomial()).fit()
    ci = fit.conf_int()
    return pd.DataFrame(
        {
            "parameter": ["alpha", "beta"],
            "estimate": [fit.params["const"], fit.params["lp"]],
            "lo": [ci.loc["const", 0], ci.loc["lp", 0]],
            "hi": [ci.loc["const", 1], ci.loc["lp", 1]],
        }
    )


def cluster_boot_auc(y, p, patient_id, n_boot: int = 300, seed: int = 20260717) -> tuple[float, float, float]:
    y = np.asarray(y)
    p = np.asarray(p)
    patient_id = np.asarray(patient_id)
    auc = roc_auc_score(y, p)
    rng = np.random.default_rng(seed)
    patients = np.unique(patient_id)
    vals = []
    patient_to_idx = {pid: np.where(patient_id == pid)[0] for pid in patients}
    for _ in range(n_boot):
        sampled = rng.choice(patients, size=len(patients), replace=True)
        idx = np.concatenate([patient_to_idx[pid] for pid in sampled])
        if len(np.unique(y[idx])) < 2:
            continue
        vals.append(roc_auc_score(y[idx], p[idx]))
    lo, hi = np.quantile(vals, [0.025, 0.975])
    return auc, lo, hi


def cluster_boot_brier(y, p, patient_id, n_boot: int = 300, seed: int = 20260717) -> tuple[float, float, float]:
    y = np.asarray(y)
    p = np.asarray(p)
    patient_id = np.asarray(patient_id)
    brier = brier_score_loss(y, p)
    rng = np.random.default_rng(seed)
    patients = np.unique(patient_id)
    vals = []
    patient_to_idx = {pid: np.where(patient_id == pid)[0] for pid in patients}
    for _ in range(n_boot):
        sampled = rng.choice(patients, size=len(patients), replace=True)
        idx = np.concatenate([patient_to_idx[pid] for pid in sampled])
        vals.append(brier_score_loss(y[idx], p[idx]))
    lo, hi = np.quantile(vals, [0.025, 0.975])
    return brier, lo, hi


def net_benefit(y, p, thresholds) -> pd.DataFrame:
    rows = []
    y = np.asarray(y)
    p = np.asarray(p)
    n = len(y)
    er = y.mean()
    for pt in thresholds:
        pos = p >= pt
        tp = ((pos) & (y == 1)).sum()
        fp = ((pos) & (y == 0)).sum()
        rows.append({"threshold": pt, "model": tp / n - fp / n * pt / (1 - pt), "all": er - (1 - er) * pt / (1 - pt), "none": 0.0})
    return pd.DataFrame(rows)


def fmt(x, digits=3):
    try:
        return f"{float(x):.{digits}f}"
    except Exception:
        return str(x)


def save_table(df: pd.DataFrame, path: Path) -> None:
    df.fillna("").to_csv(path, index=False)


def save_main_figure(fig, stem: str) -> None:
    fig.savefig(FIGS / f"{stem}.png", dpi=600, facecolor="white", bbox_inches="tight")
    fig.savefig(FIGS / f"{stem}.tiff", dpi=600, facecolor="white", bbox_inches="tight")
    fig.savefig(FIGS / f"{stem}.pdf", facecolor="white", bbox_inches="tight")


def save_supp_figure(fig, stem: str) -> None:
    fig.savefig(SUPP_FIGS / f"{stem}.png", dpi=600, facecolor="white", bbox_inches="tight")
    fig.savefig(SUPP_FIGS / f"{stem}.pdf", facecolor="white", bbox_inches="tight")


def model_display(name: str) -> str:
    mapping = {
        "traditional_penalized_logistic": "Penalized LR",
        "traditional_logistic_longitudinal": "Longitudinal LR",
        "traditional_logistic_clinical_radiographic": "Clinical-radiographic LR",
        "traditional_logistic_enhanced": "Enhanced LR",
        "traditional_logistic_pain_kl_group": "Pain-KL group LR",
        "machine_learning_random_forest": "Random forest",
        "machine_learning_gradient_boosting": "Gradient boosting",
        "traditional_logistic_discordance": "Pain-KL model",
        "traditional_logistic_base": "Base LR",
        "logistic_regression": "Logistic regression",
        "random_forest": "Random forest",
        "gradient_boosting": "Gradient boosting",
    }
    return mapping.get(str(name), str(name).replace("_", " ").title())


def build_tables() -> None:
    # Table 1: split MRKR 24 and 36 months as requested.
    table1 = pd.DataFrame(
        [
            ["Knees, n", 1598, 775, 2415, 2363, 1944],
            ["Participants/patients, n", 853, 484, 1310, 1588, 1359],
            ["Age, mean (SD)", "55.8 (5.2)", "61.5 (10.0)", "62.5 (9.0)", "63.8 (11.3)", "63.8 (11.3)"],
            ["Female, n (%)", "1256 (78.6%)", "438 (56.5%)", "1472 (61.0%)", "1684 (71.3%)", "Not separately summarized"],
            ["BMI, mean (SD)", "26.1 (4.0)", "27.8 (4.6)", "Not included in transport index", "Not available", "Not available"],
            ["WOMAC pain score, 0-20, mean (SD)", "4.9 (3.4)", "2.1 (3.0)", "1.5 (1.8)", "3.3 (3.4)", "3.3 (3.4)"],
            ["Function, mean (SD)", "15.5 (11.6)", "6.9 (9.6)", "Not included in transport index", "Not available", "Not available"],
            ["KL distribution", "KL0: 1098; KL1: 500", "KL0: 501; KL1: 274", "KL0/1: 326; KL2: 1060; KL3: 731; KL4: 298", "KL0/1: 360; KL2: 751; KL3: 801; KL4: 451", "Same source cohort; eligibility differs by 36m follow-up"],
            ["Outcome definition", "Incident KL >=2", "Incident KL >=2", "Target-knee TKA/KR", "Hardware arthroplasty", "Hardware arthroplasty"],
            ["Events, n (%)", "24m KL >=2: 185/1598 (11.6%)", "24m KL >=2: 49/775 (6.3%)", "60m TKA/KR: 279/2415 (11.6%)", "24m arthroplasty: 855/2363 (36.2%)", "36m arthroplasty: 935/1944 (48.1%)"],
        ],
        columns=["Characteristic", "CHECK early cohort", "OAI early bridge subgroup", "OAI 60m model cohort", "MRKR 24m cohort", "MRKR 36m cohort"],
    )
    save_table(table1, TABLES / "table1_cohort_characteristics_and_analytic_populations.csv")

    table2 = pd.DataFrame(
        [
            ["CHECK", "Symptomatic KL0/1", "Baseline", "KL >=2", "24/60/96m", "Early transition"],
            ["OAI bridge", "KL0/1", "Baseline", "KL >=2", "24m", "Directional replication"],
            ["OAI model", "Knees spanning KL0-4 at 24m landmark, predominantly KL >=2", "Baseline and 0-24m variables assessed before landmark", "Target-knee TKA/KR", "60m", "Model development; patient-grouped CV"],
            ["MRKR", "Real-world radiograph cohort", "Index radiograph", "Hardware arthroplasty", "24/36m", "Cross-horizon prognostic-index transport and horizon-specific recalibration"],
        ],
        columns=["Analysis", "Entry state", "Predictor window", "Outcome", "Horizon", "Role and validation strategy"],
    )
    save_table(table2, TABLES / "table2_stage_specific_study_design.csv")

    # Table 3, combined bridge evidence in three readable sections.
    smd = pd.read_csv(BASE / "reviewer_revised_manuscript/supplementary_tables/table_s7_check_oai_state_alignment_smd.csv")
    risk = pd.read_csv(BASE / "check_incident_oa_analysis/tables/check_incident_oa_risk_by_pain_kl_group.csv")
    oai_early = pd.read_csv(BASE / "check_oai_bridge_analysis/tables/bridge_oai_early_subgroup_incident_roa_risk.csv")
    klrisk = pd.read_csv(BASE / "check_oai_bridge_analysis/tables/bridge_oai_baseline_kl_60m_tka_risk.csv")
    ordf = pd.read_csv(BASE / "check_oai_bridge_analysis/tables/bridge_oai_kl_state_tka_adjusted_or.csv")
    rows = []
    for _, r in smd.iterrows():
        check_value = r["CHECK incident KL>=2"]
        if r["Measure"] == "KL distribution at bridge state":
            check_value = "KL2: 374 (93.5%); KL3: 18 (4.5%); KL5/TKA: 8 (2.0%)"
        rows.append({
            "Section": "A. Radiographic state alignment and clinical differences",
            "Measure": r["Measure"],
            "CHECK": check_value,
            "OAI": r["OAI baseline KL2"],
            "Effect estimate": r["Estimate"] if pd.notna(r["Estimate"]) else "",
            "95% CI / P": "",
        })
    groups = ["Low pain / KL0", "High pain / KL0", "Low pain / KL1", "High pain / KL1"]
    check24 = risk[risk.horizon_months == 24]
    for g in groups:
        c = check24[check24.pain_kl_group == g].iloc[0]
        o = oai_early[oai_early.group == g].iloc[0]
        rows.append({
            "Section": "B. Directional replication of 24m incident KL >=2",
            "Measure": g,
            "CHECK": f"{int(c.events)}/{int(c.knees)} ({100*c.risk:.1f}%)",
            "OAI": f"{int(o.events)}/{int(o.knees)} ({100*o.risk:.1f}%)",
            "Effect estimate": f"Difference {100*(o.risk-c.risk):.1f} pp",
            "95% CI / P": "",
        })
    for _, r in klrisk.iterrows():
        orrow = ordf[ordf.term == r.kl_category]
        if len(orrow):
            or_text = f"OR {orrow.or_vs_KL0_1.iloc[0]:.2f}"
            ci = f"{orrow.ci_lower_95.iloc[0]:.2f}-{orrow.ci_upper_95.iloc[0]:.2f}; P={orrow.p_value.iloc[0]:.3g}"
        else:
            or_text = "Reference"
            ci = ""
        rows.append({
            "Section": "C. OAI downstream 60m TKA/KR gradient",
            "Measure": r.kl_category,
            "CHECK": "",
            "OAI": f"{int(r.events_60m)}/{int(r.knees)} ({100*r.risk_60m:.1f}%)",
            "Effect estimate": or_text,
            "95% CI / P": ci,
        })
    save_table(pd.DataFrame(rows), TABLES / "table3_bridge_analysis.csv")

    # Table 4, add intercept-only recalibration rows.
    main = pd.read_csv(BASE / "reviewer_revised_manuscript/tables/table4_model_performance_transport_summary.csv")
    transport = pd.read_csv(BASE / "tables/table_oai_to_mrkr_transport_recalibration.csv")
    rows = main[main.Analysis.isin(["CHECK 24m", "CHECK 60m", "CHECK 96m", "OAI 60m TKA/KR"])].to_dict("records")
    for h in [24, 36]:
        for method, label, valid in [
            ("none", "Original OAI prognostic index", "Transport evaluation"),
            ("intercept_recalibration", "Intercept-only recalibration", "MRKR recalibration"),
            ("logistic_recalibration", "Logistic recalibration", "MRKR recalibration"),
        ]:
            r = transport[(transport.target_horizon_months == h) & (transport.recalibration_method == method)].iloc[0]
            rows.append(
                {
                    "Analysis": f"OAI index -> MRKR {h}m",
                    "Model": label,
                    "AUC (95% CI)": fmt(r.auc, 3),
                    "Brier (95% CI)": fmt(r.brier, 3),
                    "Intercept": fmt(0 if abs(r.calibration_intercept) < 0.005 else r.calibration_intercept, 2),
                    "Slope": fmt(r.calibration_slope, 2),
                    "O/E": fmt(r.oe_ratio, 2),
                    "Validation": valid,
                }
            )
    out = pd.DataFrame(rows)
    out = out.rename(columns={"Intercept": "Calibration intercept", "Slope": "Calibration slope"})
    for col in ["Calibration intercept", "Calibration slope", "O/E"]:
        if col in out.columns:
            out[col] = out[col].astype(str).str.replace("-0.00", "0.00", regex=False).str.replace("-0.0", "0.0", regex=False)
    save_table(out, TABLES / "table4_model_performance_and_transport.csv")


def make_figure1() -> None:
    if EXTERNAL_FIGURE1.exists():
        stem = "figure1_overall_study_design_stage_linked_framework"
        shutil.copy2(EXTERNAL_FIGURE1, FIGS / f"{stem}.pdf")
        prefix = FIGS / f"{stem}_render"
        subprocess.run(
            ["pdftoppm", "-png", "-singlefile", "-r", "600", str(EXTERNAL_FIGURE1), str(prefix)],
            check=True,
        )
        rendered = FIGS / f"{stem}_render.png"
        shutil.move(str(rendered), FIGS / f"{stem}.png")
        try:
            from PIL import Image

            with Image.open(FIGS / f"{stem}.png") as im:
                im.save(FIGS / f"{stem}.tiff", compression="tiff_lzw")
        except Exception:
            pass
        return

    fig, axes = plt.subplots(3, 1, figsize=(12, 7.2), gridspec_kw={"height_ratios": [1.0, 1.25, 0.95]})
    ax = axes[0]
    ax.axis("off")
    x = [0.08, 0.33, 0.58, 0.83]
    labels = ["CHECK\nsymptomatic KL0/1", "Incident definite\nradiographic OA\nKL ≥2", "OAI KL 0–4 cohort\npredominantly KL ≥2\n60-month TKA/KR prediction", "MRKR real-world cohort\ntransport and recalibration"]
    colors = [COL["green"], COL["blue"], "#D97A25", COL["red"]]
    for xi, lab, c in zip(x, labels, colors):
        ax.text(xi, 0.55, lab, ha="center", va="center", bbox=dict(boxstyle="round,pad=.4", fc="white", ec=c, lw=2), fontsize=11)
    for a, b in zip(x[:-1], x[1:]):
        ax.annotate("", xy=(b - 0.09, 0.55), xytext=(a + 0.09, 0.55), arrowprops=dict(arrowstyle="->", lw=1.8, linestyle="--"))
    ax.text(0.5, 0.92, "A. Population-level stage-linked framework", ha="center", weight="bold", fontsize=13)
    ax.text(0.5, 0.12, "Dashed arrows indicate population-level stage linkage, not individual-level follow-up or cohort exchangeability.", ha="center", fontsize=10, color=COL["gray"])

    ax = axes[1]
    ax.axis("off")
    timeline = [
        ("CHECK", ["Baseline", "24 m", "60 m", "96 m"], COL["blue"]),
        ("OAI", ["Baseline", "0-24 m\npredictors", "24 m\nlandmark", "60 m\nTKA/KR"], "#D97A25"),
        ("MRKR", ["Index\nradiograph", "24 m\narthroplasty", "36 m\narthroplasty"], COL["red"]),
    ]
    for i, (name, points, color) in enumerate(timeline):
        y0 = 0.78 - i * 0.28
        xs = np.linspace(0.28, 0.88, len(points))
        ax.text(0.10, y0, name, weight="bold", fontsize=12, va="center")
        ax.plot([xs[0], xs[-1]], [y0, y0], color=color, lw=2, alpha=0.9)
        for j, (xi, lab) in enumerate(zip(xs, points)):
            ax.scatter(xi, y0, s=80, color="white", edgecolor=color, lw=2, zorder=3)
            ax.text(xi, y0 - 0.095, lab, ha="center", va="top", fontsize=9)
            if j < len(xs) - 1:
                ax.annotate("", xy=(xs[j + 1] - 0.035, y0), xytext=(xi + 0.035, y0), arrowprops=dict(arrowstyle="->", color=color, lw=1.6))
    ax.text(0.5, 0.98, "B. Time origins and outcome horizons", ha="center", weight="bold", fontsize=13)

    ax = axes[2]
    ax.axis("off")
    boxes = [
        ("CHECK", "24 m: 1,598 knees\n60 m: 1,510 knees\n96 m: 1,460 knees", COL["blue"]),
        ("OAI", "2,415 knees\n1,310 participants\n279 target-knee TKA/KR events", "#D97A25"),
        ("MRKR", "24 m: 2,363 knees; 1,588 patients\n36 m: 1,944 knees; 1,359 patients", COL["red"]),
    ]
    for xi, (title, body, color) in zip([0.18, 0.50, 0.82], boxes):
        ax.text(xi, 0.72, title, ha="center", va="center", weight="bold", color=color, fontsize=12)
        ax.text(xi, 0.36, body, ha="center", va="center", fontsize=10.5, bbox=dict(boxstyle="round,pad=.45", fc="white", ec=color, lw=1.5))
    ax.text(0.5, 0.98, "C. Analytic denominators", ha="center", weight="bold", fontsize=13)
    fig.tight_layout()
    save_main_figure(fig, "figure1_overall_study_design_stage_linked_framework")
    plt.close(fig)


def make_figure2() -> None:
    summary = pd.read_csv(BASE / "check_incident_oa_analysis/tables/check_incident_oa_cohort_event_summary.csv")
    risk = pd.read_csv(BASE / "check_incident_oa_analysis/tables/check_incident_oa_risk_by_pain_kl_group.csv")
    pred = pd.read_csv(BASE / "check_incident_oa_analysis/tables/check_incident_oa_internal_validation_predictions.csv")
    d24 = pred[(pred.horizon_months == 24) & (pred.model == "traditional_penalized_logistic")]
    dat24 = pd.read_csv(BASE / "check_incident_oa_analysis/tables/check_incident_oa_24m_analysis_dataset.csv")
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    x = np.arange(len(summary))
    y = summary.event_rate * 100
    err = np.array([[100 * (r.event_rate - wilson(int(r.events), int(r.knees))[0]) for _, r in summary.iterrows()], [100 * (wilson(int(r.events), int(r.knees))[1] - r.event_rate) for _, r in summary.iterrows()]])
    axes[0, 0].bar(x, y, color=COL["blue"], width=0.72)
    axes[0, 0].errorbar(x, y, yerr=err, fmt="none", ecolor="#333", capsize=4)
    axes[0, 0].set_xticks(x); axes[0, 0].set_xticklabels([f"{h} m" for h in summary.horizon_months])
    axes[0, 0].set_ylim(0, 44)
    axes[0, 0].set_ylabel("Observed incident KL ≥2 (%)")
    axes[0, 0].set_title("A. Observed incident KL ≥2 proportions")
    for i, r in summary.iterrows():
        label_y = y.iloc[i] + err[1, i] + 1.35
        axes[0, 0].text(
            i + 0.018,
            label_y,
            f"{100*r.event_rate:.1f}%\n{int(r.events):,}/{int(r.knees):,}",
            ha="center",
            va="bottom",
            fontsize=8,
            bbox=dict(boxstyle="square,pad=0.08", fc="white", ec="none", alpha=0.78),
        )

    fit_dat = dat24.dropna(subset=["outcome", "pain", "kl1", "age", "female", "bmi", "function", "right_knee"]).copy()
    xdat = fit_dat[["pain", "kl1", "age", "female", "bmi", "function", "right_knee"]].copy()
    xdat["pain_x_kl1"] = xdat["pain"] * xdat["kl1"]
    fit = sm.GLM(fit_dat["outcome"], sm.add_constant(xdat), family=sm.families.Binomial()).fit()
    pain_grid = np.linspace(dat24.pain.min(), dat24.pain.max(), 120)
    for kl1, color, label in [(0, COL["green"], "KL0"), (1, COL["red"], "KL1")]:
        grid = pd.DataFrame({
            "pain": pain_grid,
            "kl1": kl1,
            "age": fit_dat.age.median(),
            "female": fit_dat.female.median(),
            "bmi": fit_dat.bmi.median(),
            "function": fit_dat.function.median(),
            "right_knee": fit_dat.right_knee.median(),
        })
        grid["pain_x_kl1"] = grid["pain"] * grid["kl1"]
        sf = fit.get_prediction(sm.add_constant(grid, has_constant="add")).summary_frame(alpha=0.05)
        axes[0, 1].plot(pain_grid, sf["mean"] * 100, color=color, lw=2.6, label=label)
        axes[0, 1].fill_between(pain_grid, sf["mean_ci_lower"] * 100, sf["mean_ci_upper"] * 100, color=color, alpha=0.065, lw=0)
    axes[0, 1].set_xlabel("Baseline WOMAC pain score, 0-20")
    axes[0, 1].set_ylabel("Predicted 24-month KL ≥2 risk (%)")
    axes[0, 1].set_title("B. Adjusted continuous pain-risk association")
    axes[0, 1].legend(title="Baseline KL", fontsize=8)

    fpr, tpr, _ = roc_curve(d24.y, d24.predicted_risk)
    auc, lo, hi = cluster_boot_auc(d24.y, d24.predicted_risk, d24.patient_id)
    axes[1, 0].plot(fpr, tpr, color=COL["blue"], lw=2.3)
    axes[1, 0].plot([0, 1], [0, 1], ls="--", color=COL["gray"], alpha=0.75)
    axes[1, 0].set_xlim(-0.01, 1.01); axes[1, 0].set_ylim(-0.01, 1.01)
    axes[1, 0].set_xlabel("1 − Specificity"); axes[1, 0].set_ylabel("Sensitivity")
    axes[1, 0].set_title("C. Patient-grouped out-of-fold ROC")
    axes[1, 0].text(0.52, 0.22, "AUC 0.786 (95% CI 0.746–0.826)\n1,598 knees; 185 events", transform=axes[1, 0].transAxes, fontsize=8.5, bbox=dict(boxstyle="round,pad=.25", fc="white", ec="none", alpha=0.85))

    cal = calibration_points(d24.y, d24.predicted_risk)
    axes[1, 1].plot([0, 1], [0, 1], ls="--", color=COL["gray"], alpha=0.62, lw=1)
    axes[1, 1].errorbar(cal.pred, cal.obs, yerr=[cal.obs - cal.lo, cal.hi - cal.obs], marker="o", markersize=4.4, color=COL["blue"], ecolor=COL["gray"], capsize=2)
    axes[1, 1].set_xlim(0, 0.55); axes[1, 1].set_ylim(0, 0.55)
    axes[1, 1].plot(cal.pred, cal.obs, color=COL["blue"], lw=0.7)
    axes[1, 1].set_xlabel("Predicted risk"); axes[1, 1].set_ylabel("Observed risk")
    axes[1, 1].set_title("D. 24-month out-of-fold calibration")
    axes[1, 1].text(0.62, 0.14, "Intercept 0.28\nSlope 1.17\nBrier 0.089", transform=axes[1, 1].transAxes, fontsize=8.5, bbox=dict(boxstyle="round,pad=.25", fc="white", ec="none", alpha=0.85))
    for ax in axes.ravel():
        ax.grid(alpha=0.15)
    fig.suptitle("Figure 2. CHECK early structural transition", weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    save_main_figure(fig, "figure2_check_early_structural_transition")
    plt.close(fig)


def make_figure3() -> None:
    risk = pd.read_csv(BASE / "check_incident_oa_analysis/tables/check_incident_oa_risk_by_pain_kl_group.csv")
    oai_early = pd.read_csv(BASE / "check_oai_bridge_analysis/tables/bridge_oai_early_subgroup_incident_roa_risk.csv")
    klrisk = pd.read_csv(BASE / "check_oai_bridge_analysis/tables/bridge_oai_baseline_kl_60m_tka_risk.csv")
    ordf = pd.read_csv(BASE / "check_oai_bridge_analysis/tables/bridge_oai_kl_state_tka_adjusted_or.csv")
    smd = pd.read_csv(BASE / "reviewer_revised_manuscript/supplementary_tables/table_s7_check_oai_state_alignment_smd.csv")
    fig = plt.figure(figsize=(13.5, 8))
    gs = fig.add_gridspec(2, 3, width_ratios=[0.92, 1.16, 1.16], hspace=0.40, wspace=0.60)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1:])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d1 = fig.add_subplot(gs[1, 1])
    ax_d2 = fig.add_subplot(gs[1, 2])

    xlab = ["CHECK\nincident KL ≥2\n(n=400)", "OAI\nbaseline KL2\n(n=1,653)"]
    ax_a.bar(xlab, [93.5, 100.0], color=COL["blue"])
    ax_a.bar(xlab, [4.5, 0.0], bottom=[93.5, 100.0], color=COL["gold"])
    ax_a.bar(xlab, [2.0, 0.0], bottom=[98.0, 100.0], color="#B8B8B8")
    ax_a.set_ylim(0, 112); ax_a.set_ylabel("KL distribution (%)")
    ax_a.set_title("A. Radiographic state alignment")
    ax_a.tick_params(axis="x", labelsize=8)
    ax_a.text(0, 47, "KL2\n93.5%", ha="center", va="center", color="white", fontsize=8.2, weight="bold")
    ax_a.text(1, 50, "KL2\n100%", ha="center", va="center", color="white", fontsize=8.2, weight="bold")
    ax_a.text(0, 95.75, "KL3 4.5%", ha="center", va="center", fontsize=7.8, color="#222")
    ax_a.annotate("KL5/TKA 2.0%", xy=(0.0, 99.0), xytext=(0, 104.4), fontsize=7.8, ha="center",
                  arrowprops=dict(arrowstyle="-", color=COL["gray"], lw=0.8), color="#222")

    ss = smd[smd.Estimate.astype(str).str.startswith("SMD")].copy()
    ss["smd"] = ss.Estimate.str.replace("SMD ", "", regex=False).astype(float)
    ss["abs_smd"] = ss.smd.abs()
    label_map = {"Female": "Female sex"}
    ss["label"] = ss.Measure.replace(label_map)
    ss = ss.sort_values("abs_smd", ascending=True)
    ax_b.axvline(0, color="#222", lw=1)
    ax_b.axvline(-0.1, color=COL["gray"], ls="--"); ax_b.axvline(0.1, color=COL["gray"], ls="--")
    ax_b.scatter(ss.smd, ss.label, color=COL["blue"], s=62)
    ax_b.set_xlim(-0.90, 0.80)
    ax_b.set_xlabel("Standardized mean difference")
    ax_b.set_title("B. Clinical differences despite radiographic alignment")

    check24 = risk[risk.horizon_months == 24]
    groups = ["Low pain / KL0", "High pain / KL0", "Low pain / KL1", "High pain / KL1"]
    x = np.arange(4); w = 0.35
    check_vals, check_err, oai_vals, oai_err = [], [[], []], [], [[], []]
    for g in groups:
        c = check24[check24.pain_kl_group == g].iloc[0]
        o = oai_early[oai_early.group == g].iloc[0]
        for row, vals, errs in [(c, check_vals, check_err), (o, oai_vals, oai_err)]:
            lo, hi = wilson(int(row.events), int(row.knees))
            vals.append(row.risk * 100)
            errs[0].append(100 * (row.risk - lo))
            errs[1].append(100 * (hi - row.risk))
    ax_c.errorbar(x - w/2, check_vals, yerr=check_err, fmt="o", color=COL["blue"], capsize=3, label="CHECK")
    ax_c.errorbar(x + w/2, oai_vals, yerr=oai_err, fmt="o", color=COL["gold"], capsize=3, label="OAI")
    ax_c.set_xticks(x); ax_c.set_xticklabels(["Low pain\nKL0", "High pain\nKL0", "Low pain\nKL1", "High pain\nKL1"], fontsize=8)
    ax_c.set_ylabel("24-month incident KL ≥2 risk (%)")
    ax_c.set_title("C. Directional replication")
    ax_c.set_ylim(0, 42)
    ax_c.legend(loc="upper left", fontsize=8, frameon=False, handletextpad=0.4)

    x = np.arange(len(klrisk))
    ax_d1.errorbar(x, klrisk.risk_60m * 100, yerr=np.array([[100*(r.risk_60m-wilson(int(r.events_60m), int(r.knees))[0]) for _, r in klrisk.iterrows()], [100*(wilson(int(r.events_60m), int(r.knees))[1]-r.risk_60m) for _, r in klrisk.iterrows()]]), fmt="o", color=COL["blue"], capsize=4)
    ax_d1.set_xticks(x); ax_d1.set_xticklabels(["KL 0–1", "KL2", "KL3", "KL4"])
    ax_d1.set_ylim(0, 45)
    ax_d1.set_ylabel("Observed 60-month TKA/KR risk (%)")
    ax_d1.set_title("D1. Observed downstream risk")
    ax_d1.set_xlim(-0.25, len(klrisk) - 0.42)
    for i, r in klrisk.iterrows():
        ax_d1.text(i + 0.06, r.risk_60m * 100 + 1.8, f"{100*r.risk_60m:.1f}%", ha="left", fontsize=8)
    ax_d2.errorbar(ordf.or_vs_KL0_1, [0, 1, 2], xerr=[ordf.or_vs_KL0_1 - ordf.ci_lower_95, ordf.ci_upper_95 - ordf.or_vs_KL0_1], fmt="o", color="black", capsize=4)
    ax_d2.axvline(1, color=COL["gray"], ls="--")
    ax_d2.set_xscale("log")
    ax_d2.set_xlim(0.8, 90)
    ax_d2.set_xticks([1, 2, 5, 10, 20, 40])
    ax_d2.xaxis.set_major_formatter(mticker.FormatStrFormatter("%g"))
    ax_d2.set_yticks([0, 1, 2]); ax_d2.set_yticklabels(["KL2", "KL3", "KL4"])
    ax_d2.set_xlabel("Adjusted odds ratio vs KL 0–1")
    ax_d2.set_title("D2. Adjusted association with 60-month TKA/KR")
    for yi, r in enumerate(ordf.itertuples()):
        label_x = r.ci_upper_95 * 1.08
        ax_d2.text(label_x, yi, f"{r.or_vs_KL0_1:.2f} ({r.ci_lower_95:.2f}–{r.ci_upper_95:.2f})",
                   va="center", fontsize=7.4, ha="left",
                   bbox=dict(facecolor="white", edgecolor="none", pad=0.6, alpha=0.9))
    for ax in [ax_a, ax_b, ax_c, ax_d1, ax_d2]:
        ax.grid(alpha=0.15)
    fig.suptitle("Figure 3. CHECK-OAI bridge evidence", weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    save_main_figure(fig, "figure3_check_oai_bridge_evidence")
    plt.close(fig)


def make_figure4() -> None:
    comp = pd.read_csv(BASE / "reviewer_revised_manuscript/supplementary_tables/table_s8_oai_60m_tka_full_model_comparison.csv")
    pred = pd.read_csv(BASE / "tables/internal_validation_predictions.csv")
    oai = pred[(pred.cohort == "OAI") & (pred.model == "traditional_penalized_logistic")].copy()
    dca_src = pd.read_csv(BASE / "reviewer_revised_manuscript/supplementary_tables/table_s15_oai_60m_tka_decision_curve.csv")
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    comp = comp.sort_values("cv_auc")
    y = np.arange(len(comp))
    name_map = {
        "traditional_penalized_logistic": "Penalized LR",
        "traditional_logistic_longitudinal": "Longitudinal LR",
        "traditional_logistic_clinical_radiographic": "Clinical-radiographic LR",
        "machine_learning_random_forest": "Random forest",
        "machine_learning_gradient_boosting": "Gradient boosting",
        "traditional_logistic_discordance": "Pain-KL model",
        "traditional_logistic_base": "Base LR",
    }
    pred_all = pd.read_csv(BASE / "tables/internal_validation_predictions.csv")
    ci_rows = []
    for _, r in comp.iterrows():
        dd = pred_all[(pred_all.cohort == "OAI") & (pred_all.model == r.model)]
        if len(dd):
            auc, lo, hi = cluster_boot_auc(dd.y, dd.predicted_risk, dd.patient_id, n_boot=200)
        else:
            auc, lo, hi = float(r.cv_auc), np.nan, np.nan
        ci_rows.append((auc, lo, hi))
    aucs = np.array([r[0] for r in ci_rows]); los = np.array([r[1] for r in ci_rows]); his = np.array([r[2] for r in ci_rows])
    for i, row in enumerate(comp.itertuples()):
        selected = row.model == "traditional_penalized_logistic"
        color = COL["blue"] if selected else "white"
        edge = COL["blue"] if selected else COL["gray"]
        axes[0, 0].errorbar(aucs[i], y[i], xerr=[[aucs[i]-los[i]], [his[i]-aucs[i]]], fmt="o", mfc=color, mec=edge, mew=1.6, color=edge, ecolor=COL["gray"], capsize=3)
    axes[0, 0].set_yticks(y); axes[0, 0].set_yticklabels([name_map.get(m, m) for m in comp.model], fontsize=7.8)
    axes[0, 0].set_xlabel("AUC"); axes[0, 0].set_xlim(0.49, 0.86); axes[0, 0].set_title("A. Candidate-model AUC")
    cal = calibration_points(oai.y, oai.predicted_risk)
    axes[0, 1].plot([0, 1], [0, 1], ls="--", color=COL["gray"], alpha=0.62, lw=1)
    axes[0, 1].errorbar(cal.pred, cal.obs, yerr=[cal.obs - cal.lo, cal.hi - cal.obs], marker="o", markersize=4.4, color=COL["blue"], ecolor=COL["gray"], capsize=2)
    axes[0, 1].set_xlim(0, 0.45); axes[0, 1].set_ylim(0, 0.45)
    axes[0, 1].plot(cal.pred, cal.obs, color=COL["blue"], lw=0.7)
    axes[0, 1].set_xlabel("Predicted risk"); axes[0, 1].set_ylabel("Observed risk"); axes[0, 1].set_title("B. Out-of-fold calibration of the selected model")
    axes[0, 1].text(0.68, 0.12, "Intercept 0.14\nSlope 1.08\nBrier 0.089", transform=axes[0, 1].transAxes, fontsize=8.5, bbox=dict(boxstyle="round,pad=.25", fc="white", ec="none", alpha=0.85))
    oai["risk_group"] = pd.qcut(oai.predicted_risk, 3, labels=["Lowest tertile", "Middle tertile", "Highest tertile"])
    strata = oai.groupby("risk_group", observed=True).agg(n=("y", "size"), events=("y", "sum"), risk=("y", "mean")).reset_index()
    strata_ci = strata.apply(lambda r: wilson(int(r.events), int(r.n)), axis=1, result_type="expand")
    yerr = [100 * (strata.risk - strata_ci[0]), 100 * (strata_ci[1] - strata.risk)]
    axes[1, 0].bar(range(len(strata)), strata.risk * 100, color=[COL["green"], COL["gold"], COL["red"]], width=0.62)
    axes[1, 0].errorbar(range(len(strata)), strata.risk * 100, yerr=yerr, fmt="none", ecolor="#333", capsize=4)
    axes[1, 0].set_xticks(range(len(strata)))
    axes[1, 0].set_xticklabels(["Lowest\ntertile", "Middle\ntertile", "Highest\ntertile"], fontsize=9)
    for i, r in strata.iterrows():
        axes[1, 0].text(i, 100*strata_ci.iloc[i, 1] + 1.4, f"{100*r.risk:.1f}%\n{int(r.events)}/{int(r.n)}", ha="center", fontsize=8)
    axes[1, 0].set_ylim(0, 35)
    axes[1, 0].set_ylabel("Observed 60-month target-knee TKA/KR risk (%)"); axes[1, 0].set_title("C. Observed risk across predicted-risk tertiles")
    axes[1, 1].plot(dca_src.threshold_probability, dca_src.selected_model_net_benefit, color=COL["blue"], lw=2.2, label="Selected model")
    axes[1, 1].plot(dca_src.threshold_probability, dca_src.treat_all_net_benefit, color=COL["red"], ls="--", alpha=0.75, label="Treat all")
    axes[1, 1].axhline(0, color=COL["gray"], ls=":", alpha=0.85, label="Treat none")
    axes[1, 1].set_xlim(0.03, 0.30); axes[1, 1].set_xlabel("Threshold probability"); axes[1, 1].set_ylabel("Net benefit")
    axes[1, 1].set_title("D. Exploratory decision curve"); axes[1, 1].legend(fontsize=8)
    for ax in axes.ravel(): ax.grid(alpha=0.15)
    fig.suptitle("Figure 4. OAI 60-month TKA/KR prognostic-index model", weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    save_main_figure(fig, "figure4_oai_60m_tka_prognostic_index")
    plt.close(fig)


def make_figure5() -> None:
    rec = pd.read_csv(BASE / "tables/table_oai_to_mrkr_transport_recalibration.csv")
    pred = pd.read_csv(BASE / "tables/oai_to_mrkr_transport_predictions.csv")
    fig = plt.figure(figsize=(14, 8))
    gs = fig.add_gridspec(2, 3, hspace=0.38, wspace=0.34)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[0, 2])
    ax_d = fig.add_subplot(gs[1, 0])
    ax_e = fig.add_subplot(gs[1, 1:])
    aucs = rec[rec.recalibration_method == "none"].sort_values("target_horizon_months")
    auc_ci = {"24m": (0.700, 0.675, 0.722), "36m": (0.723, 0.700, 0.746)}
    x = np.arange(2)
    yv = [auc_ci["24m"][0], auc_ci["36m"][0]]
    yerr = [[auc_ci["24m"][0]-auc_ci["24m"][1], auc_ci["36m"][0]-auc_ci["36m"][1]], [auc_ci["24m"][2]-auc_ci["24m"][0], auc_ci["36m"][2]-auc_ci["36m"][0]]]
    ax_a.errorbar(x, yv, yerr=yerr, fmt="o", color=COL["blue"], capsize=4)
    ax_a.set_xticks(x); ax_a.set_xticklabels(["24 m", "36 m"])
    ax_a.set_xlim(-0.45, 1.45)
    ax_a.set_ylim(0.55, 0.86); ax_a.set_ylabel("AUC"); ax_a.set_title("A. Transport discrimination")
    for i, key in enumerate(["24m", "36m"]):
        est, lo, hi = auc_ci[key]
        ax_a.text(
            i,
            hi + 0.020,
            f"{est:.3f}\n95% CI {lo:.3f}–{hi:.3f}",
            ha="center",
            va="bottom",
            fontsize=8,
            clip_on=False,
            bbox=dict(boxstyle="square,pad=0.08", fc="white", ec="none", alpha=0.78),
        )
    legend_handles = None
    legend_labels = None
    for ax, h, title in [(ax_b, 24, "B. MRKR 24-month out-of-fold calibration"), (ax_c, 36, "C. MRKR 36-month out-of-fold calibration")]:
        ax.plot([0, 1], [0, 1], ls="--", color=COL["gray"], alpha=0.45, lw=1)
        for method, color, lab, ls in [
            ("none", COL["blue"], "Original OAI index", "-"),
            ("intercept_recalibration", COL["gold"], "Intercept-only recalibration", "--"),
            ("logistic_recalibration", COL["red"], "Logistic recalibration", "-"),
        ]:
            d = pred[(pred.target_horizon_months == h) & (pred.recalibration_method == method)]
            c = calibration_points(d.y, d.predicted_risk)
            ax.errorbar(c.pred, c.obs, yerr=[c.obs - c.lo, c.hi - c.obs], marker="o", markersize=3.6, color=color, ecolor=color, alpha=0.92, capsize=1.2, label=lab)
            ax.plot(c.pred, c.obs, color=color, lw=0.55, ls=ls)
        ax.set_xlim(0, 1.0); ax.set_ylim(0, 1.05)
        ax.set_xlabel("Predicted risk"); ax.set_ylabel("Observed risk"); ax.set_title(title)
        if h == 24:
            legend_handles, legend_labels = ax.get_legend_handles_labels()
        else:
            leg = ax.get_legend()
            if leg:
                leg.remove()
    if legend_handles and legend_labels:
        fig.legend(legend_handles, legend_labels, loc="upper center", bbox_to_anchor=(0.5, 0.94),
                   ncol=3, fontsize=7.0, frameon=False, handletextpad=0.4, columnspacing=1.1)
    brier_rows = []
    for h, ypos in [(24, 1), (36, 0)]:
        offsets = [-0.18, 0, 0.18]
        for off, method, lab, color in zip(offsets, ["none", "intercept_recalibration", "logistic_recalibration"], ["Original", "Intercept-only", "Logistic"], [COL["blue"], COL["gold"], COL["red"]]):
            r = rec[(rec.target_horizon_months == h) & (rec.recalibration_method == method)].iloc[0]
            d = pred[(pred.target_horizon_months == h) & (pred.recalibration_method == method)]
            bv, blo, bhi = cluster_boot_brier(d.y, d.predicted_risk, d.patient_id, n_boot=200, seed=20260717 + h)
            ax_d.errorbar(bv, ypos + off, xerr=[[bv - blo], [bhi - bv]], fmt="o", color=color, capsize=3, label=lab if h == 24 else None)
            ax_d.text(bhi + 0.004, ypos + off, f"{bv:.3f}", va="center", ha="left", fontsize=8)
    ax_d.set_yticks([1, 0]); ax_d.set_yticklabels(["24-month", "36-month"])
    ax_d.set_xlabel("Brier score"); ax_d.set_title("D. Cross-validated Brier score")
    ax_d.set_xlim(0.195, 0.33)

    params = []
    for h in [24, 36]:
        d = pred[(pred.target_horizon_months == h) & (pred.recalibration_method == "none")]
        pp = logistic_update_params(d.y, d.predicted_risk)
        pp["horizon"] = f"{h}-month"
        params.append(pp)
    params = pd.concat(params, ignore_index=True)
    params["label"] = params["horizon"] + " " + params["parameter"].map({"alpha": "α", "beta": "β"})
    params = params.iloc[[0, 1, 2, 3]].copy()
    yy = np.arange(len(params))[::-1]
    colors = [COL["blue"] if p == "alpha" else COL["red"] for p in params.parameter]
    ax_e.axvline(0, color=COL["gray"], ls=":" )
    ax_e.axvline(1, color=COL["gray"], ls="--", alpha=0.55)
    for i, r in enumerate(params.itertuples()):
        ax_e.errorbar(r.estimate, yy[i], xerr=[[r.estimate-r.lo], [r.hi-r.estimate]], fmt="o", color=colors[i], capsize=4)
        ax_e.text(r.hi + 0.065, yy[i], f"{r.estimate:.2f} ({r.lo:.2f}–{r.hi:.2f})", va="center", fontsize=8)
    ax_e.set_yticks(yy); ax_e.set_yticklabels(params.label)
    ax_e.set_xlim(-0.06, 1.45)
    ax_e.set_xlabel("Logistic recalibration parameter estimate")
    ax_e.set_title("E. Horizon-specific logistic recalibration parameters")
    for ax in [ax_a, ax_b, ax_c, ax_d, ax_e]: ax.grid(alpha=0.15)
    fig.suptitle("Figure 5. OAI prognostic-index transport to MRKR", weight="bold", y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.84])
    save_main_figure(fig, "figure5_oai_index_transport_mrkr_recalibration")
    plt.close(fig)


def make_supplementary_figure_s4() -> None:
    smd = pd.read_csv(BASE / "reviewer_revised_manuscript/supplementary_tables/table_s7_check_oai_state_alignment_smd.csv")
    ss = smd[smd.Estimate.astype(str).str.startswith("SMD")].copy()
    ss["smd"] = ss.Estimate.str.replace("SMD ", "", regex=False).astype(float)
    ss = ss.sort_values("smd")
    fig, ax = plt.subplots(figsize=(7.2, 4.1))
    colors = [COL["red"] if v > 0 else COL["blue"] for v in ss.smd]
    ax.axvline(0, color="#222", lw=1)
    ax.axvline(-0.1, color=COL["gray"], ls="--", lw=1)
    ax.axvline(0.1, color=COL["gray"], ls="--", lw=1)
    ax.scatter(ss.smd, ss.Measure, s=70, color=colors)
    ax.set_xlim(-0.9, 0.8)
    ax.set_xlabel("Standardized mean difference")
    ax.set_title("Clinical differences persist despite radiographic state alignment")
    ax.grid(alpha=0.15)
    ax.text(0.02, -0.16, "Positive values indicate higher values in CHECK; negative values indicate higher values in OAI. Dashed lines mark +/-0.10 reference thresholds.",
            transform=ax.transAxes, fontsize=8)
    fig.tight_layout()
    save_supp_figure(fig, "figure_s4_check_oai_standardized_differences")
    plt.close(fig)


def make_supplementary_figure_s1() -> None:
    fig, ax = plt.subplots(figsize=(12.8, 7.0))
    ax.set_axis_off()
    columns = [
        (
            "CHECK",
            COL["blue"],
            [
                "CHECK knee-level source file\nsymptomatic early OA cohort",
                "Eligible baseline knees\nKL0/1 and baseline predictors",
                "24-month analysis\n1,598 knees; 853 patients\n185 incident KL ≥2 events",
                "60-month analysis\n1,510 knees; 811 patients\n394 incident KL ≥2 events",
                "96-month analysis\n1,460 knees; 788 patients\n520 incident KL ≥2 events",
            ],
        ),
        (
            "OAI",
            "#D97A25",
            [
                "OAI 24-month landmark\ncore modelling file",
                "Bridge subgroup\nbaseline KL0/1 knees",
                "Directional replication\n775 knees; 484 participants\n49 incident KL ≥2 events",
                "60-month TKA/KR model cohort\n2,415 knees; 1,310 participants\n279 target-knee events",
            ],
        ),
        (
            "MRKR",
            COL["red"],
            [
                "MRKR real-world\nradiograph-linked cohort",
                "Transportable common-variable\nmodel set",
                "24-month transport analysis\n2,363 knees; 1,588 patients\n855 arthroplasty events",
                "36-month transport analysis\n1,944 knees; 1,359 patients\n935 arthroplasty events",
            ],
        ),
    ]
    xs = [0.18, 0.50, 0.82]
    for x, (cohort, color, boxes) in zip(xs, columns):
        ax.text(x, 0.92, cohort, ha="center", va="center", fontsize=14, weight="bold", color=color)
        ys = np.linspace(0.78, 0.18, len(boxes))
        for idx, (y, text) in enumerate(zip(ys, boxes)):
            ax.text(
                x,
                y,
                text,
                ha="center",
                va="center",
                fontsize=9.2,
                zorder=3,
                linespacing=1.25,
                bbox=dict(boxstyle="round,pad=0.38,rounding_size=0.10", fc="white", ec=color, lw=1.7),
            )
            if idx < len(boxes) - 1:
                ax.annotate(
                    "",
                    xy=(x, ys[idx + 1] + 0.045),
                    xytext=(x, y - 0.045),
                    arrowprops=dict(arrowstyle="->", color=COL["gray"], lw=1.4),
                    zorder=1,
                )
    ax.text(
        0.5,
        0.04,
        "Boxes show the analytic populations used in the current manuscript; denominators differ by endpoint and available follow-up.",
        ha="center",
        va="center",
        fontsize=8.7,
        color=COL["gray"],
    )
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.suptitle("Three-cohort patient inclusion flow and analytic populations", weight="bold", y=0.985)
    fig.tight_layout(rect=[0, 0, 1, 0.955])
    save_supp_figure(fig, "figure_s1_cohort_inclusion_flow_analytic_populations")
    plt.close(fig)


def make_supplementary_figure_s3() -> None:
    pred = pd.read_csv(BASE / "check_incident_oa_analysis/tables/check_incident_oa_internal_validation_predictions.csv")
    model = "traditional_penalized_logistic"
    fig, axes = plt.subplots(1, 3, figsize=(11.2, 3.7), sharex=True, sharey=True)
    for ax, h in zip(axes, [24, 60, 96]):
        d = pred[(pred.horizon_months == h) & (pred.model == model)].copy()
        cal = calibration_points(d.y, d.predicted_risk)
        ax.plot([0, 1], [0, 1], ls="--", color=COL["gray"], alpha=0.55, lw=1)
        ax.errorbar(
            cal.pred,
            cal.obs,
            yerr=[cal.obs - cal.lo, cal.hi - cal.obs],
            fmt="o",
            color=COL["blue"],
            ecolor=COL["gray"],
            markersize=4.2,
            capsize=2,
        )
        ax.plot(cal.pred, cal.obs, color=COL["blue"], lw=0.7)
        ax.set_title(f"{h}-month: Penalized logistic regression")
        ax.set_xlim(0, 0.62)
        ax.set_ylim(0, 0.62)
        ax.set_xlabel("Predicted risk")
        ax.grid(alpha=0.15)
    axes[0].set_ylabel("Observed risk")
    fig.suptitle("Patient-grouped out-of-fold calibration of the selected CHECK incident KL ≥2 model", weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    save_supp_figure(fig, "figure_s3_check_selected_model_calibration_curves")
    plt.close(fig)


def make_supplementary_figure_s5() -> None:
    comp = pd.read_csv(BASE / "reviewer_revised_manuscript/supplementary_tables/table_s3_check_complete_model_comparison.csv")
    pred = pd.read_csv(BASE / "check_incident_oa_analysis/tables/check_incident_oa_internal_validation_predictions.csv")
    horizons = [24, 60, 96]
    fig, axes = plt.subplots(3, 2, figsize=(10.8, 9.2), sharey="row")
    model_order = [
        "traditional_penalized_logistic",
        "traditional_logistic_enhanced",
        "traditional_logistic_clinical_radiographic",
        "traditional_logistic_pain_kl_group",
        "machine_learning_gradient_boosting",
        "machine_learning_random_forest",
        "traditional_logistic_base",
    ]
    for row_idx, h in enumerate(horizons):
        cc = comp[comp.horizon_months == h].copy()
        cc["order"] = cc.model.map({m: i for i, m in enumerate(model_order)})
        cc = cc.sort_values("order", ascending=False)
        labels = [model_display(m) for m in cc.model]
        y = np.arange(len(cc))
        auc_ci, brier_ci = [], []
        for m in cc.model:
            dd = pred[(pred.horizon_months == h) & (pred.model == m)]
            if len(dd):
                auc_ci.append(cluster_boot_auc(dd.y, dd.predicted_risk, dd.patient_id, n_boot=120, seed=20260717 + h))
                brier_ci.append(cluster_boot_brier(dd.y, dd.predicted_risk, dd.patient_id, n_boot=120, seed=20260718 + h))
            else:
                r = cc[cc.model == m].iloc[0]
                auc_ci.append((r.cv_auc, np.nan, np.nan))
                brier_ci.append((r.brier, np.nan, np.nan))
        for col_idx, (vals, title, xlabel, xlim) in enumerate([
            (auc_ci, f"{h}-month AUC", "AUC", (0.48, 0.86)),
            (brier_ci, f"{h}-month Brier score", "Brier score", (0.07, 0.25)),
        ]):
            ax = axes[row_idx, col_idx]
            est = np.array([v[0] for v in vals])
            lo = np.array([v[1] for v in vals])
            hi = np.array([v[2] for v in vals])
            xerr = np.vstack([est - lo, hi - est])
            selected = cc.model.eq("traditional_penalized_logistic").to_numpy()
            for i, is_sel in enumerate(selected):
                ax.errorbar(est[i], y[i], xerr=[[xerr[0, i]], [xerr[1, i]]], fmt="o",
                            color=COL["blue"] if is_sel else COL["gray"],
                            mfc=COL["blue"] if is_sel else "white",
                            mec=COL["blue"] if is_sel else COL["gray"],
                            mew=1.4, capsize=2.5)
            ax.set_yticks(y)
            ax.set_yticklabels(labels, fontsize=8)
            ax.set_xlim(*xlim)
            ax.set_xlabel(xlabel)
            ax.set_title(title + (" (higher is better)" if col_idx == 0 else " (lower is better)"))
            ax.grid(alpha=0.15)
    fig.suptitle("CHECK model-comparison performance across incident KL >=2 horizons", weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    save_supp_figure(fig, "figure_s5_check_model_comparison_point_plot")
    plt.close(fig)


def make_supplementary_figure_s6() -> None:
    oai = pd.read_csv(BASE / "check_oai_bridge_analysis/tables/bridge_oai_early_subgroup_incident_roa_risk.csv")
    groups = ["Low pain / KL0", "High pain / KL0", "Low pain / KL1", "High pain / KL1"]
    dat = oai[oai.group.isin(groups)].set_index("group").loc[groups].reset_index()
    errs = np.array([[100 * (r.risk - wilson(int(r.events), int(r.knees))[0]) for _, r in dat.iterrows()],
                     [100 * (wilson(int(r.events), int(r.knees))[1] - r.risk) for _, r in dat.iterrows()]])
    fig, ax = plt.subplots(figsize=(7.0, 4.3))
    x = np.arange(len(dat))
    ax.errorbar(x, dat.risk * 100, yerr=errs, fmt="o", color=COL["blue"], capsize=3)
    ax.set_xticks(x)
    ax.set_xticklabels(["Low pain\nKL 0", "High pain\nKL 0", "Low pain\nKL 1", "High pain\nKL 1"])
    ax.set_ylabel("24-month incident KL >=2 risk (%)")
    ax.set_title("Directional replication of pain-KL risk ordering in OAI KL 0-1 knees")
    ax.set_ylim(0, 25)
    for i, r in dat.iterrows():
        ax.text(i, r.risk * 100 + errs[1, i] + 0.9, f"{100*r.risk:.1f}%\n{int(r.events)}/{int(r.knees)}", ha="center", fontsize=8)
    ax.grid(alpha=0.15)
    fig.tight_layout()
    save_supp_figure(fig, "figure_s6_oai_directional_replication_pain_kl_gradient")
    plt.close(fig)


def make_supplementary_figure_s7() -> None:
    comp = pd.read_csv(BASE / "reviewer_revised_manuscript/supplementary_tables/table_s9_mrkr_internal_model_comparison.csv")
    comp = comp.sort_values("cv_auc")
    y = np.arange(len(comp))
    labels = [model_display(m) for m in comp.model]
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.5), sharey=True)
    for ax, col, xlabel, xlim in [
        (axes[0], "cv_auc", "AUC", (0.55, 0.76)),
        (axes[1], "brier", "Brier score", (0.19, 0.26)),
    ]:
        ax.scatter(comp[col], y, s=62, c="white", edgecolors=COL["gray"], linewidths=1.5)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlim(*xlim)
        ax.set_xlabel(xlabel)
        ax.grid(alpha=0.15)
    axes[0].set_title("A. Discrimination")
    axes[1].set_title("B. Probability accuracy")
    fig.suptitle("Internal MRKR benchmark for 24-month hardware-defined arthroplasty", weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    save_supp_figure(fig, "figure_s7_mrkr_internal_model_performance")
    plt.close(fig)


def make_supplementary_figure_s8() -> None:
    dca = pd.read_csv(BASE / "reviewer_revised_manuscript/supplementary_tables/table_s14_mrkr_corrected_decision_curve.csv")
    method_map = {
        "none": ("Original OAI index", COL["blue"], "-"),
        "intercept_recalibration": ("Intercept-only recalibration", COL["gold"], "--"),
        "logistic_recalibration": ("Logistic recalibration", COL["red"], "-"),
    }
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.2), sharey=True)
    handles = labels = None
    for ax, h in zip(axes, [24, 36]):
        sub = dca[dca.horizon_months == h]
        for method, (label, color, ls) in method_map.items():
            dd = sub[sub.method == method]
            ax.plot(dd.threshold_probability, dd.net_benefit, label=label, color=color, ls=ls, lw=2)
        base = sub[sub.method == "none"]
        if len(base):
            ax.plot(base.threshold_probability, base.treat_all, color=COL["gray"], ls=":", lw=1.5, label="Treat all")
            ax.axhline(0, color="#222", ls="--", lw=1, alpha=0.6, label="Treat none")
        ax.set_xlim(0.02, 0.45)
        ax.set_ylim(-0.20, 0.55)
        ax.set_xlabel("Threshold probability")
        ax.set_title(f"{h}-month horizon")
        ax.grid(alpha=0.15)
        if handles is None:
            handles, labels = ax.get_legend_handles_labels()
    axes[0].set_ylabel("Net benefit")
    fig.legend(handles, labels, loc="upper center", ncol=5, frameon=False, fontsize=9, bbox_to_anchor=(0.5, 0.94))
    fig.suptitle("Exploratory MRKR decision-curve analysis using out-of-fold recalibrated predictions", weight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.84])
    save_supp_figure(fig, "figure_s8_mrkr_transport_decision_curve")
    plt.close(fig)


def make_supplementary_figure_s9() -> None:
    risk = pd.read_csv(BASE / "reviewer_revised_manuscript/supplementary_tables/table_s6_oai_kl_state_adjusted_60m_tka_risk.csv")
    risk["risk"] = risk["60m risk"].str.replace("%", "", regex=False).astype(float) / 100
    errs = np.array([[100 * (r.risk - wilson(int(r.Events), int(r.Knees))[0]) for _, r in risk.iterrows()],
                     [100 * (wilson(int(r.Events), int(r.Knees))[1] - r.risk) for _, r in risk.iterrows()]])
    fig, ax = plt.subplots(figsize=(7.0, 4.3))
    x = np.arange(len(risk))
    labels = risk["Baseline KL"].replace({"KL0/1": "KL 0–1"}).tolist()
    ax.errorbar(x, risk.risk * 100, yerr=errs, fmt="o", color=COL["blue"], capsize=3)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Observed 60-month TKA/KR risk (%)")
    ax.set_title("Observed OAI TKA/KR risk by baseline KL state")
    ax.set_ylim(0, 45)
    ax.set_xlim(-0.15, len(risk) - 0.65)
    for i, r in risk.iterrows():
        if i == len(risk) - 1:
            ax.text(i - 0.06, r.risk * 100 + errs[1, i] + 1.0, f"{100*r.risk:.1f}%", ha="right", fontsize=8)
        else:
            ax.text(i + 0.05, r.risk * 100 + errs[1, i] + 1.0, f"{100*r.risk:.1f}%", ha="left", fontsize=8)
    ax.grid(alpha=0.15)
    fig.tight_layout()
    save_supp_figure(fig, "figure_s9_oai_tka_risk_by_baseline_kl_state")
    plt.close(fig)


def load_analysis_module(module_name: str, filename: str):
    path = BASE / "scripts" / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def fit_final_penalized_model(df: pd.DataFrame, outcome_col: str, patient_col: str, spec_tuple: tuple) -> tuple[object, dict]:
    features, _categorical, estimator, grid = spec_tuple
    y = df[outcome_col].astype(int).to_numpy()
    groups = df[patient_col].astype(str).to_numpy()
    model = clone(estimator)
    best = {}
    if grid:
        cv = GroupKFold(n_splits=min(5, len(np.unique(groups))))
        search = GridSearchCV(model, grid, scoring="roc_auc", cv=cv, n_jobs=-1)
        search.fit(df[features], y, groups=groups)
        model = search.best_estimator_
        best = search.best_params_
    else:
        model.fit(df[features], y)
    return model, best


def coefficient_rows(model, model_name: str, endpoint: str, term_labels: dict[str, str]) -> list[dict[str, object]]:
    pre = model.named_steps["pre"]
    lr = model.named_steps["model"]
    feature_names = [name.replace("num__", "") for name in pre.get_feature_names_out()]
    num_steps = pre.named_transformers_["num"].named_steps
    scaler = num_steps.get("scaler", num_steps.get("scale"))
    rows = [
        {
            "Model": model_name,
            "Endpoint": endpoint,
            "Term": "Intercept",
            "Coefficient": float(lr.intercept_[0]),
            "Center": "",
            "Scale": "",
            "Coding / unit": "Logit intercept after preprocessing",
        }
    ]
    for term, coef, center, scale in zip(feature_names, lr.coef_[0], scaler.mean_, scaler.scale_):
        rows.append(
            {
                "Model": model_name,
                "Endpoint": endpoint,
                "Term": term_labels.get(term, term),
                "Coefficient": float(coef),
                "Center": float(center),
                "Scale": float(scale),
                "Coding / unit": "Coefficient per 1 SD after within-model median imputation and z-standardization",
            }
        )
    return rows


def make_final_model_equation_assets() -> None:
    check_mod = load_analysis_module("check_incident_oa_model_specs", "40_check_incident_definite_oa_analysis.py")
    stage_mod = load_analysis_module("stage_specific_model_specs", "38_complete_stage_specific_prediction_analysis.py")

    check_df = pd.read_csv(BASE / "check_incident_oa_analysis/tables/check_incident_oa_24m_analysis_dataset.csv")
    check_spec = check_mod.model_specs()["traditional_penalized_logistic"]
    check_model, check_best = fit_final_penalized_model(check_df, "outcome", "patient_id", check_spec)

    datasets = {cohort: stage_mod.normalize_cohort(df, cohort) for cohort, df in stage_mod.read_data().items()}
    oai_task = stage_mod.AnalysisTask("OAI", "60-month target-knee TKA/KR", 60, "Aim 3 OAI 60-month arthroplasty model development")
    oai_df = stage_mod.cohort_task_data(datasets, oai_task)
    oai_spec = stage_mod.model_specs("OAI")["traditional_penalized_logistic"]
    oai_model, oai_best = fit_final_penalized_model(oai_df, "primary_outcome", "patient_id", oai_spec)

    term_labels = {
        "age": "Age",
        "female": "Female sex",
        "right_knee": "Right knee",
        "pain": "Pain score",
        "kl1": "Baseline KL1",
        "kl": "KL grade",
        "bmi": "BMI",
        "function": "WOMAC function",
        "baseline_knee_pain_flag": "Baseline knee pain flag",
        "pain_change": "Pain change, 0–24 months",
        "kl_change": "KL change, 0–24 months",
    }
    rows = []
    rows.extend(coefficient_rows(check_model, "CHECK final penalized logistic model", "24-month incident KL ≥2", term_labels))
    rows.extend(coefficient_rows(oai_model, "OAI final penalized logistic model", "60-month target-knee TKA/KR", term_labels))

    transport_pred = pd.read_csv(BASE / "tables/oai_to_mrkr_transport_predictions.csv")
    for h in [24, 36]:
        d = transport_pred[(transport_pred.target_horizon_months == h) & (transport_pred.recalibration_method == "none")]
        params = logistic_update_params(d.y, d.predicted_risk)
        for r in params.itertuples():
            rows.append(
                {
                    "Model": "MRKR logistic recalibration",
                    "Endpoint": f"{h}-month arthroplasty",
                    "Term": "alpha" if r.parameter == "alpha" else "beta",
                    "Coefficient": float(r.estimate),
                    "Center": "",
                    "Scale": "",
                    "Coding / unit": "logit(p_MRKR,h) = alpha_h + beta_h * LP_OAI",
                }
            )
    coeff = pd.DataFrame(rows)
    coeff["Coefficient"] = coeff["Coefficient"].map(lambda v: f"{float(v):.4f}" if v != "" else "")
    for c in ["Center", "Scale"]:
        coeff[c] = coeff[c].map(lambda v: f"{float(v):.4f}" if v != "" else "")
    coeff.to_csv(SUPP_TABLES / "table_s13_final_model_equations_and_coefficients.csv", index=False)

    complexity = pd.DataFrame(
        [
            ["CHECK", "24-month incident KL ≥2", len(check_df), check_df.patient_id.nunique(), int(check_df.outcome.sum()), 8, "Penalized logistic regression; C=0.03", "Patient-grouped nested CV for tuning; patient-grouped OOF validation"],
            ["OAI", "60-month target-knee TKA/KR", len(oai_df), oai_df.patient_id.nunique(), int(oai_df.primary_outcome.sum()), 7, "Penalized logistic regression; C=0.03", "Patient-grouped nested CV for tuning; patient-grouped OOF validation"],
            ["MRKR", "24/36-month arthroplasty", "2,363 / 1,944", "1,588 / 1,359", "855 / 935", "2 recalibration parameters per horizon", "Fixed OAI linear predictor plus alpha/beta recalibration", "Patient-grouped out-of-fold target-cohort recalibration"],
        ],
        columns=["Cohort", "Endpoint", "Knees", "Patients", "Events", "Model complexity", "Final model", "Validation approach"],
    )
    complexity.to_csv(SUPP_TABLES / "table_s14_sample_size_and_model_complexity.csv", index=False)

    def model_terms(model):
        pre = model.named_steps["pre"]
        lr = model.named_steps["model"]
        names = [term_labels.get(n.replace("num__", ""), n.replace("num__", "")) for n in pre.get_feature_names_out()]
        return float(lr.intercept_[0]), list(zip(names, lr.coef_[0]))

    check_intercept, check_terms = model_terms(check_model)
    oai_intercept, oai_terms = model_terms(oai_model)
    rec24 = logistic_update_params(
        transport_pred[(transport_pred.target_horizon_months == 24) & (transport_pred.recalibration_method == "none")].y,
        transport_pred[(transport_pred.target_horizon_months == 24) & (transport_pred.recalibration_method == "none")].predicted_risk,
    )
    rec36 = logistic_update_params(
        transport_pred[(transport_pred.target_horizon_months == 36) & (transport_pred.recalibration_method == "none")].y,
        transport_pred[(transport_pred.target_horizon_months == 36) & (transport_pred.recalibration_method == "none")].predicted_risk,
    )
    fig, axes = plt.subplots(3, 1, figsize=(12.5, 7.2), gridspec_kw={"height_ratios": [1.15, 1.05, 0.85]})
    panels = [
        (axes[0], "A. CHECK final 24-month incident KL ≥2 equation", check_intercept, check_terms, check_best),
        (axes[1], "B. OAI final 60-month TKA/KR prognostic-index equation", oai_intercept, oai_terms, oai_best),
    ]
    for ax, title, intercept, terms, best in panels:
        ax.axis("off")
        ax.text(0.01, 0.92, title, fontsize=12, weight="bold", color=COL["blue"], va="top")
        pieces = [f"{intercept:.3f}"] + [f"{coef:+.3f} x z({name})" for name, coef in terms]
        eq = "logit(p) = " + " ".join(pieces)
        ax.text(0.02, 0.56, eq, fontsize=10.0, va="center", ha="left", wrap=True)
        penalty = best.get("model__C", "")
        ax.text(0.02, 0.18, f"Preprocessing: median imputation and z-standardization; L2 penalty C={penalty}.", fontsize=8.5, color=COL["gray"])
    ax = axes[2]
    ax.axis("off")
    ax.text(0.01, 0.90, "C. MRKR target-setting recalibration equations", fontsize=12, weight="bold", color=COL["blue"], va="top")
    a24 = rec24.loc[rec24.parameter == "alpha", "estimate"].iloc[0]
    b24 = rec24.loc[rec24.parameter == "beta", "estimate"].iloc[0]
    a36 = rec36.loc[rec36.parameter == "alpha", "estimate"].iloc[0]
    b36 = rec36.loc[rec36.parameter == "beta", "estimate"].iloc[0]
    ax.text(0.02, 0.55, f"24 months: logit(p_MRKR,24) = {a24:.3f} + {b24:.3f} x LP_OAI", fontsize=10.5)
    ax.text(0.02, 0.28, f"36 months: logit(p_MRKR,36) = {a36:.3f} + {b36:.3f} x LP_OAI", fontsize=10.5)
    ax.text(0.02, 0.06, "LP_OAI is the transported OAI prognostic-index linear predictor; recalibration updates absolute risk for the MRKR target setting.", fontsize=8.5, color=COL["gray"])
    fig.suptitle("Figure 6. Final model equations and coefficients", weight="bold", y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    save_main_figure(fig, "figure6_final_model_equations_coefficients")
    plt.close(fig)


def make_supplementary_figures_publication() -> None:
    make_supplementary_figure_s1()
    make_supplementary_figure_s3()
    make_supplementary_figure_s4()
    make_supplementary_figure_s5()
    make_supplementary_figure_s6()
    make_supplementary_figure_s7()
    make_supplementary_figure_s8()
    make_supplementary_figure_s9()


def copy_supplementary() -> None:
    src_dir = BASE / "reviewer_revised_manuscript"
    for p in (src_dir / "supplementary_tables").glob("*.csv"):
        shutil.copy2(p, SUPP_TABLES / p.name)
    for p in (src_dir / "supplementary_figures").glob("*"):
        if p.suffix.lower() in [".png", ".pdf"]:
            shutil.copy2(p, SUPP_FIGS / p.name)


def build_manuscript() -> None:
    table4 = pd.read_csv(TABLES / "table4_model_performance_and_transport.csv")
    c24 = table4[table4.Analysis.eq("CHECK 24m")].iloc[0]
    oai = table4[table4.Analysis.eq("OAI 60m TKA/KR")].iloc[0]
    mrkr24 = table4[(table4.Analysis.eq("OAI index -> MRKR 24m")) & (table4.Model.eq("Original OAI prognostic index"))].iloc[0]
    mrkr24_log = table4[(table4.Analysis.eq("OAI index -> MRKR 24m")) & (table4.Model.eq("Logistic recalibration"))].iloc[0]
    text = f"""# Stage-Specific Prediction Across the Knee Osteoarthritis Continuum: Early Radiographic Transition, Arthroplasty Risk, and Real-World Recalibration

## Abstract

**Background:** Knee osteoarthritis (OA) prediction depends on disease stage. Early symptomatic KL0/1 knees require prediction of incident definite radiographic OA, whereas later-stage knees require prediction of arthroplasty risk and target-setting recalibration. We evaluated a three-stage framework with two bridge analyses and one real-world transport validation.

**Methods:** Aim 1 used CHECK baseline KL0/1 knees to model incident KL >=2, with 24 months prespecified as the primary horizon and 60/96 months as time-extension analyses. Aim 2 evaluated KL >=2 as a radiographic connection node using three bridge components: CHECK incident KL >=2 versus OAI baseline KL2 radiographic state alignment, OAI KL0/1 directional replication of the pain-KL risk gradient, and OAI KL-state-to-TKA/KR risk gradient. Aim 3 developed an OAI 60-month TKA/KR prognostic index in knees spanning early to advanced radiographic severity, predominantly KL >=2. Aim 4 transported the OAI-derived prognostic index to MRKR and applied horizon-specific recalibration for 24- and 36-month arthroplasty outcomes.

**Results:** In CHECK, incident KL >=2 occurred in 185/1,598 knees (11.6%) at 24 months, 394/1,510 (26.1%) at 60 months, and 520/1,460 (35.6%) at 96 months. Penalized logistic regression was selected as the CHECK 24-month primary model, with AUC {c24['AUC (95% CI)']} and Brier {c24['Brier (95% CI)']}. CHECK incident KL >=2 knees were radiographically aligned with OAI baseline KL2 knees, but SMDs showed clinical non-exchangeability. OAI KL0/1 knees directionally reproduced the pain-KL ordering, and OAI 60-month TKA/KR risk increased from 3.4% in KL0/1 to 35.1% in KL4. The OAI prognostic index achieved AUC {oai['AUC (95% CI)']} and Brier {oai['Brier (95% CI)']}. In MRKR, the unrecalibrated OAI index retained moderate ranking at 24 months (AUC {mrkr24['AUC (95% CI)']}) but underestimated absolute risk (O/E {mrkr24['O/E']}); logistic recalibration improved Brier to {mrkr24_log['Brier (95% CI)']}.

**Conclusions:** The findings support a stage-specific prediction framework rather than three parallel prediction exercises. KL >=2 acted as a radiographic connection node, not proof of cohort exchangeability. The OAI prognostic index partially transported to MRKR, but absolute-risk interpretation required horizon- and setting-specific recalibration.

## Introduction

Knee OA prediction is often weakened by treating different disease stages as a single modelling problem. In early symptomatic KL0/1 knees, the clinically coherent outcome is transition to definite radiographic OA. In knees spanning radiographic OA severity, the question shifts to arthroplasty risk. In real-world radiograph cohorts, the central question is whether a research-cohort prognostic index preserves ranking and how much local recalibration is needed.

We therefore organized CHECK, OAI, and MRKR into a three-stage, population-level framework. This framework does not assume that the same patients move from one cohort to another, nor that cohorts are exchangeable. Instead, it asks whether KL >=2 can serve as a radiographic connection node and whether an OAI arthroplasty-risk index can be transported to a target real-world setting after recalibration.

## Methods

### Study Design

The study had four aims. Aim 1 modelled early structural transition in CHECK. Aim 2 tested two bridge concepts and one downstream gradient: radiographic state alignment, directional replication, and KL-state-to-arthroplasty gradient. Aim 3 developed the OAI 60-month TKA/KR prognostic index. Aim 4 evaluated cross-horizon prognostic-index transport and recalibration in MRKR.

### Stage-Specific Endpoints

CHECK baseline KL0/1 knees were analysed for incident KL >=2 at 24, 60, and 96 months. The 24-month horizon was treated as the main prediction target; longer horizons were time-extension analyses because denominators differed and missing radiographs increased over time. OAI used a 24-month landmark and 60-month target-knee TKA/KR outcome. MRKR used index radiograph time zero and hardware-defined arthroplasty at 24 and 36 months.

### Bridge Analyses

Bridge 2A compared CHECK incident KL >=2 knees with OAI baseline KL2 knees. Bridge 2B evaluated directional replication of the pain-KL risk ordering in an OAI KL0/1 subgroup. Bridge 2C assessed whether OAI KL state marked a downstream TKA/KR risk gradient. These analyses were interpreted as population-level evidence, not external validation of one cohort by another.

### Model Development and Transport

Candidate models included demographic, pain-KL, clinical-radiographic, penalized logistic regression, and machine-learning comparators. All preprocessing steps, including imputation and standardization, were fitted within training folds. Internal validation used patient-grouped folds to prevent knees from the same participant appearing in both training and validation folds. Penalized logistic regression models used nested patient-grouped tuning for the L2 penalty. Model selection prioritized calibrated probability estimation and Brier score when AUC differences were small, and favoured simpler transparent models when performance was similar. Penalized logistic regression was selected for CHECK 24 months and OAI because it combined discrimination, calibration, probability accuracy, and interpretability. Complete final equations and coefficients are shown in Figure 6 and Supplementary Table S13; model complexity relative to sample size is summarized in Supplementary Table S14. For MRKR, the OAI model was transported as a fixed prognostic index, not as a directly applicable 24- or 36-month probability. Recalibration used logit[P(Y_h=1)] = alpha_h + beta_h LP_OAI.

## Results

### Aim 1: CHECK Early Structural Transition

Among knees with available radiographic assessment at each horizon, incident KL >=2 increased from 11.6% at 24 months to 35.6% at 96 months. The 24-month risk gradient ranged from 2.5% in low-pain/KL0 knees to 32.0% in high-pain/KL1 knees. Penalized logistic regression was selected as the main CHECK model because RF and penalized LR had nearly identical AUC, whereas penalized LR was more stable and interpretable.

### Aim 2: Two Bridge Evidence Streams and Downstream Gradient

CHECK incident KL >=2 knees were similar to OAI baseline KL2 knees radiographically, but age, sex, BMI, pain, and function differed substantially. Thus, the bridge supports radiographic state alignment rather than cohort exchangeability. In OAI KL0/1 knees, 24-month incident KL >=2 risk increased from 2.8% in low-pain/KL0 to 15.0% in high-pain/KL1, showing directional replication but lower absolute risk than CHECK. In OAI, 60-month TKA/KR risk increased monotonically with KL state, from 3.4% in KL0/1 to 35.1% in KL4.

### Aim 3: OAI Prognostic-Index Development

The OAI cohort included 2,415 knees and 279 60-month TKA/KR events. Although the cohort was predominantly KL >=2, it included a minority of KL0/1 knees and is therefore described as spanning early to advanced radiographic severity. Penalized logistic regression was selected as the OAI prognostic-index model. More complex machine-learning models did not provide a clinically meaningful advantage.

### Aim 4: MRKR Transport and Recalibration

The OAI prognostic index retained moderate discrimination in MRKR at 24 and 36 months but underestimated absolute risk. At 24 months, O/E was 1.69 before recalibration. Intercept-only recalibration corrected baseline-risk mismatch, while logistic recalibration additionally updated effect strength. Recalibration improved Brier score at both 24 and 36 months, supporting target-setting recalibration before absolute-risk interpretation.

## Discussion

The main contribution is not that a complex algorithm achieved superior AUC. The contribution is a stage-specific design: early radiographic transition in CHECK, radiographic bridge evidence through KL >=2, OAI arthroplasty-risk modelling, and real-world transport with recalibration in MRKR. This structure is more clinically coherent than treating all knees as one prediction population.

Several cautions are important. CHECK and OAI were radiographically linked but clinically non-exchangeable. OAI-to-MRKR transport evaluated a prognostic index, not direct external validation of 60-month probabilities at 24 or 36 months. MRKR calibration shifts may reflect case mix, time horizon, imaging indication, proximity to surgery, outcome ascertainment, and health-care pathways. Independent temporal or geographic validation remains necessary before clinical use.

## Conclusion

Different OA stages require different prediction targets. This three-stage framework supports KL >=2 as a radiographic connection node, shows a downstream OAI arthroplasty-risk gradient, and demonstrates partial MRKR transport of an OAI prognostic index with necessary recalibration.
"""
    (MANUSCRIPT / "three_stage_bridge_transport_manuscript_draft.md").write_text(text, encoding="utf-8")

    notes = """# Three-stage bridge-transport revision notes

This package implements the latest framework: three stages, two bridge evidence streams plus a downstream KL-to-TKA/KR gradient, and one real-world transport validation.

Completed from available outputs:
- CHECK 24/60/96 incident KL >=2 summaries.
- CHECK 24m primary model refocused on penalized logistic regression.
- CHECK-OAI radiographic state alignment and clinical non-exchangeability.
- OAI early KL0/1 directional replication.
- OAI KL-state to 60m TKA/KR observed and adjusted gradient.
- OAI prognostic-index model performance.
- MRKR original, intercept-only, and logistic recalibration.

Not newly generated because required row-level source variables were not available in the current result package:
- Restricted cubic spline for continuous pain.
- CHECK retained/lost follow-up SMD and IPW analysis.
- OAI KL>=2-only model refit.
- MRKR early surgery exclusion at <=3/6/12 months.
- Fold-level alpha/beta distribution from repeated recalibration CV.
"""
    (OUT / "three_stage_revision_notes.md").write_text(notes, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    build_tables()
    copy_supplementary()
    make_supplementary_figures_publication()
    make_figure1()
    make_figure2()
    make_figure3()
    make_figure4()
    make_figure5()
    make_final_model_equation_assets()
    build_manuscript()
    print(OUT)
    print(MANUSCRIPT / "three_stage_bridge_transport_manuscript_draft.md")


if __name__ == "__main__":
    main()
