#!/usr/bin/env python3
from __future__ import annotations

import shutil
import importlib.util
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"
LATEST = TABLES / "latest_framework"
SOURCE = ROOT / "results" / "figures" / "methodology_aligned"
OUT = ROOT / "results" / "figures" / "latest_framework_supplement"
OUT.mkdir(parents=True, exist_ok=True)

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 7.2,
        "axes.titlesize": 8.2,
        "axes.labelsize": 7.2,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.8,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "savefig.dpi": 600,
    }
)

COL = {
    "navy": "#17324D",
    "blue": "#356AA0",
    "teal": "#248277",
    "orange": "#D76A3A",
    "red": "#B64040",
    "gray": "#667085",
    "light": "#E5E9EF",
}


def save(fig: plt.Figure, stem: str) -> None:
    fig.savefig(OUT / f"{stem}.png", dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / f"{stem}.tiff", dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / f"{stem}.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def preserve_approved_figures() -> None:
    stems = {1: "supplementary_figure_s1_model_e_nomogram"}
    for stem in stems.values():
        for ext in ("png", "pdf", "svg", "tiff"):
            src = SOURCE / f"{stem}.{ext}"
            if not src.exists():
                raise FileNotFoundError(src)
            shutil.copy2(src, OUT / src.name)


def box(ax, xy, wh, text, fc, ec="#CBD5E1", size=8.0, weight="normal"):
    x, y = xy; w, h = wh
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.012",
                           linewidth=0.8, edgecolor=ec, facecolor=fc)
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size,
            color=COL["navy"], fontweight=weight, linespacing=1.12)


def figure_s2() -> None:
    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.text(0.04, 0.94, "Model F-core research-use risk calculator", fontsize=14, fontweight="bold", color=COL["navy"])
    ax.text(0.04, 0.89, "OAI-derived common-variable model with optional imaging-setting recalibration",
            fontsize=8.5, color=COL["gray"])
    box(ax, (0.04, 0.15), (0.41, 0.66), "", "#F8FAFC")
    ax.text(0.075, 0.77, "Inputs", fontsize=10, fontweight="bold", color=COL["navy"])
    inputs = [("Age, years", "64"), ("Sex", "Female"), ("Knee side", "Right"),
              ("Pain score, 0–10", "6"), ("Baseline KL grade", "3"),
              ("24-month KL grade", "4"), ("KL worsening", "Auto: yes")]
    y = 0.70
    for label, value in inputs:
        ax.text(0.075, y, label, fontsize=8.0, va="center", color=COL["navy"])
        box(ax, (0.29, y - 0.023), (0.115, 0.046), value, "white", size=7.5)
        y -= 0.072
    box(ax, (0.53, 0.59), (0.42, 0.20),
        "Original OAI-derived estimate\n24-month knee-replacement risk: 21.0%\n60-month knee-replacement risk: 52.7%",
        "#EEF4FF", ec="#9CB8DE", size=9.0, weight="bold")
    box(ax, (0.53, 0.36), (0.42, 0.17),
        "MRKR imaging-setting recalibration\n24-month hardware-detection risk: 54.8%\nResearch interpretation: very high risk stratum",
        "#EAF7F4", ec="#8BC7B8", size=8.5, weight="bold")
    box(ax, (0.53, 0.16), (0.42, 0.14),
        "RESEARCH USE ONLY\nNot validated for individual clinical decisions.\nHardware-detection risk is not exact operation-date risk.\nLocal validation and recalibration are required.",
        "#FFF1F1", ec=COL["red"], size=7.0, weight="bold")
    ax.text(0.53, 0.105, "Model F-core v1.0 | Formula: OAI Cox model + target-setting recalibration",
            fontsize=6.5, color=COL["gray"])
    ax.text(0.53, 0.075, "GitHub: Hang0418/oai-mrkr-model-f-core-risk-calculator", fontsize=6.5, color=COL["gray"])
    save(fig, "supplementary_figure_s2_model_f_calculator_mockup")


def figure_s3() -> None:
    d = pd.read_csv(TABLES / "reviewer_round2_mrkr_oos_risk_strata.csv")
    order = ["Low (<10%)", "Intermediate (10-<25%)", "High (25-<50%)", "Very high (>=50%)"]
    d = d.set_index("stratum").loc[order].reset_index()
    y = np.arange(len(d))[::-1]
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.scatter(d.mean_predicted_24m, y + 0.10, marker="s", s=34, color=COL["blue"], label="Mean pooled OOS predicted")
    ax.errorbar(d.observed_24m, y - 0.10,
                xerr=[d.observed_24m-d.observed_lower_95, d.observed_upper_95-d.observed_24m],
                fmt="o", ms=4.5, capsize=3, color=COL["teal"], label="Observed 1−KM (95% CI)")
    for i, r in d.iterrows():
        ax.text(0.64, y[i], f"n={int(r.knees):,}; 24-mo events={int(r.events_24m)}",
                ha="left", va="center", fontsize=6.7, color=COL["gray"])
    ax.set_yticks(y, order); ax.set_xlim(0, 0.78); ax.set_xlabel("24-month probability")
    ax.set_title("Supplementary Figure S3 | MRKR recalibrated risk strata", loc="left", fontweight="bold", color=COL["navy"])
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.28), ncol=2, fontsize=6.6)
    ax.grid(axis="x", color=COL["light"], lw=0.7)
    fig.subplots_adjust(left=0.23, right=0.98, bottom=0.26, top=0.88)
    save(fig, "supplementary_figure_s3_mrkr_risk_strata")


def figure_s4() -> None:
    early = pd.read_csv(LATEST / "revised_figure5_mrkr_early_sensitivity.csv")
    timing = pd.read_csv(LATEST / "latest_mrkr_timing_sensitivity.csv").iloc[:3].copy()

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.35), gridspec_kw={"wspace": 0.85})

    ax = axes[0]
    y = np.arange(len(early))[::-1]
    ax.errorbar(early.auc_24m, y,
                xerr=[early.auc_24m-early.auc_lower_95, early.auc_upper_95-early.auc_24m],
                fmt="o", ms=4.5, capsize=3, color=COL["blue"])
    ax.set_yticks(y, ["Full cohort", "Exclude ≤3 months", "Exclude ≤6 months", "Exclude ≤12 months"])
    ax.set_xlim(0.62, 0.79); ax.set_xlabel("24-month AUC (95% CI)")
    ax.set_title("a  Early-detection exclusions", loc="left", fontweight="bold", color=COL["navy"])
    for yy, r in zip(y, early.itertuples()):
        ax.text(0.787, yy, f"n={int(r.knees):,}; events={int(r.events_by_24m)}", ha="right", va="center", fontsize=5.8, color=COL["gray"])
    ax.grid(axis="x", color=COL["light"], lw=0.7)

    ax = axes[1]
    y = np.arange(3)[::-1]
    short = ["First hardware-positive image", "CPT-timed within interval", "Interval midpoint"]
    lo = timing["auc_24m"] - timing["auc_lower_95"]
    hi = timing["auc_upper_95"] - timing["auc_24m"]
    ax.errorbar(timing["auc_24m"], y, xerr=np.vstack([lo, hi]), fmt="o", ms=5,
                capsize=3, color=COL["teal"], lw=1.2)
    for yy, row in zip(y, timing.itertuples()):
        ax.text(row.auc_upper_95 + 0.002, yy, f"{row.auc_24m:.3f}", va="center", fontsize=6.5)
    ax.set_yticks(y, short)
    ax.set_xlim(0.675, 0.745)
    ax.set_xlabel("24-month AUC (patient-clustered 95% CI)")
    ax.set_title("b  Exact/right-censored timing assumptions", loc="left", fontweight="bold", color=COL["navy"])
    ax.grid(axis="x", color=COL["light"], lw=0.7)

    fig.suptitle("Supplementary Figure S4 | Robustness of MRKR transport discrimination",
                 x=0.06, ha="left", fontsize=9.2, fontweight="bold", color=COL["navy"])
    fig.subplots_adjust(left=0.09, right=0.98, bottom=0.27, top=0.82)
    save(fig, "supplementary_figure_s4_mrkr_sensitivity")

    source = early[["definition", "knees", "patients", "events_by_24m", "auc_24m", "auc_lower_95", "auc_upper_95"]].copy()
    source["panel"] = "a"
    timing_source = timing[["definition", "n_knees", "events_by_24m", "auc_24m", "auc_lower_95", "auc_upper_95"]].copy()
    timing_source["panel"] = "b"
    source.to_csv(LATEST / "source_data_supplementary_figure_s4a.csv", index=False)
    timing_source.to_csv(LATEST / "source_data_supplementary_figure_s4b.csv", index=False)


def figure_s5() -> None:
    d = pd.read_csv(LATEST / "revised_supplementary_mrkr_subgroup_auc.csv")
    d = d[d.subgroup.ne("All MRKR core")].copy()
    overall = pd.read_csv(LATEST / "revised_supplementary_mrkr_subgroup_auc.csv").iloc[0].auc_24m
    domain_order = [
        ("Enrichment / ascertainment", ["OA enriched: baseline KL>=2", "OA enriched: knee OA ICD before landmark",
                                        "OA enriched: KL>=2 or OA ICD", "Pain-present at landmark", "High-quality landmark/pain window"]),
        ("Sex", ["Female", "Male"]),
        ("Age", ["Age <60 years", "Age 60-69 years", "Age >=70 years"]),
        ("Baseline KL", ["Baseline KL 0-1", "Baseline KL 2", "Baseline KL 3-4"]),
        ("Race", ["Race: Caucasian or White", "Race: African American or Black", "Race: Asian", "Race: Unknown"]),
    ]
    rows, domains = [], []
    for domain, names in domain_order:
        for name in names:
            z = d[d.subgroup.eq(name)]
            if len(z): rows.append(z.iloc[0]); domains.append(domain)
    p = pd.DataFrame(rows).reset_index(drop=True); p["domain"] = domains
    labels = p.subgroup.str.replace("OA enriched: ", "", regex=False).str.replace("Race: ", "", regex=False)
    y = np.arange(len(p))[::-1]
    fig, ax = plt.subplots(figsize=(7.3, 6.3))
    ax.axvline(overall, color=COL["orange"], ls="--", lw=1.1, label=f"Overall AUC = {overall:.3f}")
    ax.errorbar(p.auc_24m, y, xerr=[p.auc_24m-p.lower_95, p.upper_95-p.auc_24m],
                fmt="o", ms=4.2, capsize=2.7, color=COL["blue"], ecolor="#6F87A0")
    ax.set_yticks(y, labels); ax.set_xlim(0.48, 0.91); ax.set_xlabel("24-month AUC (patient-clustered 95% CI)")
    ax.set_title("Supplementary Figure S5 | MRKR subgroup discrimination", loc="left", fontweight="bold", color=COL["navy"])
    ax.grid(axis="x", color=COL["light"], lw=0.7); ax.legend(loc="lower right", fontsize=6.7)
    for yy, r in zip(y, p.itertuples()):
        ax.text(0.905, yy, f"n={int(r.n_knees):,}; events={int(r.events_by_24m)}", ha="right", va="center", fontsize=5.8, color=COL["gray"])
    starts = p.groupby("domain", sort=False).head(1).index
    for idx in starts[1:]:
        ax.axhline(len(p)-idx-0.5, color="#D8DEE6", lw=0.8)
    fig.text(0.12, 0.015, "Descriptive subgroup estimates; no formal interaction tests were performed.", fontsize=6.7, color=COL["gray"])
    fig.subplots_adjust(left=0.34, right=0.98, bottom=0.10, top=0.93)
    save(fig, "supplementary_figure_s5_mrkr_subgroups")


def km_risk_ci(time, event, horizon):
    order = np.argsort(time); time = np.asarray(time)[order]; event = np.asarray(event)[order]
    surv, varlog = 1.0, 0.0
    for t in np.unique(time[(event == 1) & (time <= horizon)]):
        n = np.sum(time >= t); d = np.sum((time == t) & (event == 1))
        surv *= (1 - d / n)
        if n > d: varlog += d / (n * (n - d))
    risk = 1 - surv
    se_s = surv * np.sqrt(varlog)
    return risk, max(0, risk - 1.96*se_s), min(1, risk + 1.96*se_s)


def figure_s6() -> None:
    tab = pd.read_csv(TABLES / "supplementary_table_9_check_exploratory_validation.csv").set_index("Item")
    check = pd.read_csv(LATEST / "revised_supplementary_check_calibration.csv").iloc[0]
    oai_data = pd.read_csv(ROOT / "derived" / "validation" / "oai_24m_common_change_model_dataset.csv")
    oai_obs, oai_lo, oai_hi = km_risk_ci(oai_data.time, oai_data.event, 60)
    pred = np.array([float(str(tab.loc["Mean predicted 60-month risk", "OAI common-change model"]).replace("%", ""))/100,
                     check.mean_predicted_60m])
    obs = np.array([oai_obs, check.observed_60m]); lo = np.array([oai_lo, check.observed_lower_95]); hi = np.array([oai_hi, check.observed_upper_95])
    fig, ax = plt.subplots(figsize=(5.4, 4.7))
    ax.plot([0, 0.13], [0, 0.13], "--", color=COL["gray"], lw=1, label="Identity")
    colors = [COL["blue"], COL["orange"]]
    for i, label in enumerate(["OAI common-change", "CHECK exploratory"]):
        ax.errorbar(pred[i], obs[i], yerr=[[obs[i]-lo[i]], [hi[i]-obs[i]]], fmt="o", ms=7, capsize=4, color=colors[i], label=label)
        note = f"events={274 if i==0 else 26}\nO/E={obs[i]/pred[i]:.2f}"
        ax.annotate(note, (pred[i], obs[i]), xytext=(7, 7 if i == 0 else -28), textcoords="offset points", fontsize=6.6, color=colors[i])
    ax.set_xlim(0, 0.13); ax.set_ylim(0, 0.13); ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Mean predicted 60-month risk"); ax.set_ylabel("Observed 60-month risk (95% CI)")
    ax.set_title("Supplementary Figure S6 | Exploratory CHECK calibration", loc="left", fontweight="bold", color=COL["navy"])
    ax.legend(loc="upper left", fontsize=6.7); ax.grid(color=COL["light"], lw=0.7)
    fig.text(0.11, 0.02, "CHECK: 1.52% observed (95% CI 1.04%–2.22%); event-limited exploratory analysis.", fontsize=6.6, color=COL["gray"])
    fig.subplots_adjust(left=0.18, right=0.96, bottom=0.16, top=0.91)
    save(fig, "supplementary_figure_s6_check_exploratory_validation")


def figure_s7() -> None:
    ph = pd.read_csv(TABLES / "oai_mrkr_reviewer_model_e_schoenfeld_ph.csv")
    ph = ph[ph.term.ne("GLOBAL")].copy(); ph["score"] = -np.log10(ph.p_value.clip(lower=1e-12)); ph = ph.sort_values("score")
    sens = pd.read_csv(TABLES / "reviewer_round2_model_e_ph_calibration_sensitivity.csv")
    fig, (ax, tb) = plt.subplots(1, 2, figsize=(8.4, 4.9), gridspec_kw={"width_ratios": [1.25, 1.0], "wspace": 0.42})
    colors = np.where(ph.p_value < 0.05, COL["red"], COL["gray"])
    ax.barh(ph.term, ph.score, color=colors); ax.axvline(-np.log10(.05), color=COL["orange"], ls="--", lw=1, label="P=0.05")
    ax.set_xlabel("−log10 Schoenfeld P value"); ax.set_title("a  Predictor-level PH diagnostics", loc="left", fontweight="bold", color=COL["navy"])
    ax.legend(loc="lower right", fontsize=6.6); ax.grid(axis="x", color=COL["light"], lw=0.7)
    tb.axis("off"); tb.set_xlim(0, 1); tb.set_ylim(0, 1)
    tb.set_title("b  Apparent fixed-horizon sensitivity", loc="left", fontweight="bold", color=COL["navy"])
    metrics = [("C-index", "c_index"), ("60-mo AUC", "auc_60m"), ("60-mo Brier", "brier_60m"),
               ("Calibration intercept", "calibration_intercept_60m"), ("Calibration slope", "calibration_slope_60m")]
    x = [0.02, 0.58, 0.87]; tb.text(x[0], .90, "Metric", fontweight="bold", fontsize=7.0)
    tb.text(x[1], .90, "Average-effect", ha="center", fontweight="bold", fontsize=7.0)
    tb.text(x[2], .90, "Time-varying", ha="center", fontweight="bold", fontsize=7.0)
    for i, (label, col) in enumerate(metrics):
        yy = .78 - i*.13; tb.text(x[0], yy, label, fontsize=7.0)
        tb.text(x[1], yy, f"{sens.iloc[0][col]:.3f}", ha="center", fontsize=7.0)
        tb.text(x[2], yy, f"{sens.iloc[1][col]:.3f}", ha="center", fontsize=7.0)
        tb.plot([.02,.98],[yy-.045,yy-.045],color="#E0E5EB",lw=.7)
    tb.text(.02, .06, "Time-varying terms: age, baseline pain, function change,\nbaseline KL, KL change, and baseline medial JSN.\nInteraction: x × log(max[t, 0.1]).", fontsize=6.2, color=COL["gray"])
    fig.suptitle("Supplementary Figure S7 | Model E proportional-hazards sensitivity", x=.06, ha="left", fontsize=9.3, fontweight="bold", color=COL["navy"])
    fig.subplots_adjust(left=.16, right=.98, bottom=.10, top=.87)
    save(fig, "supplementary_figure_s7_ph_tvc_sensitivity")


def figure_s8() -> None:
    d = pd.read_csv(LATEST / "revised_supplementary_mrkr_secondary_horizons.csv")
    h = d.drop_duplicates("horizon_months")
    fig, axs = plt.subplots(2, 2, figsize=(7.4, 5.4), gridspec_kw={"hspace": .42, "wspace": .34})
    for ax in axs.flat: ax.grid(color=COL["light"], lw=.7)
    axs[0,0].plot([0,*h.horizon_months], [3412,*h.at_risk], "o-", color=COL["blue"]); axs[0,0].set_title("a  Number at risk", loc="left", fontweight="bold", color=COL["navy"]); axs[0,0].set_ylabel("Knees")
    axs[0,1].plot([0,*h.horizon_months], [0,*h.censored_before_horizon], "s-", color=COL["orange"]); axs[0,1].set_title("b  Censored before horizon", loc="left", fontweight="bold", color=COL["navy"]); axs[0,1].set_ylabel("Knees")
    for name, color, style in [("Original transport", COL["orange"], "-"), ("Apparent slope+baseline recalibration", COL["teal"], "-")]:
        z=d[d.analysis.eq(name)]; axs[1,0].plot(z.horizon_months,z.mean_predicted_risk,"o"+style,color=color,label=name.replace("Apparent slope+baseline ","Apparent "))
        axs[1,1].plot(z.horizon_months,z.brier,"o"+style,color=color,label=name.replace("Apparent slope+baseline ","Apparent "))
    axs[1,0].plot(h.horizon_months,h.observed_risk,"D-",color=COL["blue"],label="Observed 1−KM")
    axs[1,0].set_title("c  Predicted and observed risk",loc="left",fontweight="bold",color=COL["navy"]); axs[1,0].set_ylabel("Risk"); axs[1,0].legend(fontsize=5.8)
    axs[1,1].set_title("d  Event-time-specific IPCW Brier",loc="left",fontweight="bold",color=COL["navy"]); axs[1,1].set_ylabel("Brier score"); axs[1,1].legend(fontsize=5.8)
    for ax in axs.flat:
        ax.set_xlim(0,63); ax.set_xticks([0,12,24,36,60]); ax.set_xlabel("Months after landmark")
        ax.axvspan(58,62,color="#E9EDF2",alpha=.75,zorder=-2)
    fig.text(.79,.025,"60-month estimates exploratory: 483 knees at risk.",fontsize=6.4,color=COL["gray"],ha="center")
    fig.suptitle("Supplementary Figure S8 | Exploratory long-horizon MRKR performance",x=.06,ha="left",fontsize=9.3,fontweight="bold",color=COL["navy"])
    fig.subplots_adjust(left=.10,right=.98,bottom=.10,top=.90)
    save(fig,"supplementary_figure_s8_mrkr_long_horizon")


def figure_s9() -> None:
    files=[("OAI","oai_model_f_included_vs_excluded_comparison.csv"),("MRKR","mrkr_model_f_included_vs_excluded_comparison.csv")]
    fig,axs=plt.subplots(1,2,figsize=(8.8,4.5),sharex=True,gridspec_kw={"wspace":.48})
    keep=["Age, years","Baseline pain score, 0-10","24-month pain score, 0-10","Baseline KL grade","24-month KL grade","Post-landmark follow-up, months","Female","Right knee","Post-landmark KR/TKA event","Post-landmark hardware-defined KR/TKA event","Race, overall SMD","Ethnicity, overall SMD"]
    for ax,(cohort,file) in zip(axs,files):
        d=pd.read_csv(TABLES/file); d=d[d.Characteristic.isin(keep)&d.SMD.notna()].copy(); d=d.sort_values("SMD")
        labels=d.Characteristic.str.replace("Post-landmark hardware-defined KR/TKA event","Post-landmark event",regex=False).str.replace("Post-landmark KR/TKA event","Post-landmark event",regex=False)
        y=np.arange(len(d)); process=d.Characteristic.str.contains("follow-up|event",case=False,regex=True)
        ax.hlines(y,0,d.SMD,color="#D4DAE2",lw=1)
        ax.scatter(d.loc[~process,"SMD"],y[~process],s=30,color=COL["blue"] if cohort=="OAI" else COL["orange"])
        ax.scatter(d.loc[process,"SMD"],y[process],s=34,facecolors="white",edgecolors=COL["blue"] if cohort=="OAI" else COL["orange"],linewidths=1.2,label="Follow-up/outcome process")
        ax.axvline(.10,color=COL["red"],ls="--",lw=1); ax.set_yticks(y,labels); ax.set_title(cohort,loc="left",fontweight="bold",color=COL["navy"]); ax.grid(axis="x",color=COL["light"],lw=.7)
        ax.set_xlabel("Absolute SMD"); ax.legend(loc="lower right",fontsize=5.8)
    fig.suptitle("Supplementary Figure S9 | Complete-case selection",x=.06,ha="left",fontsize=9.3,fontweight="bold",color=COL["navy"])
    fig.subplots_adjust(left=.22,right=.98,bottom=.13,top=.87)
    save(fig,"supplementary_figure_s9_selection_love_plot")


def figure_s10() -> None:
    intervals = pd.read_csv(LATEST / "latest_mrkr_hardware_detection_intervals.csv")
    timing = pd.read_csv(LATEST / "latest_mrkr_timing_sensitivity.csv")
    widths = (intervals["interval_right_months"] - intervals["interval_left_months"]) * 30.4375

    relation = pd.Series(
        np.select(
            [
                intervals["interval_right_months"].le(24),
                intervals["interval_left_months"].lt(24) & intervals["interval_right_months"].gt(24),
            ],
            ["Known by 24 months", "Interval crosses 24 months"],
            default="Known after 24 months",
        )
    ).value_counts().reindex(["Known by 24 months", "Interval crosses 24 months", "Known after 24 months"])
    cpt = pd.Series(
        np.where(intervals["cpt_within_interval_90"].fillna(False), "Eligible CPT anchor", "No eligible CPT anchor")
    ).value_counts().reindex(["Eligible CPT anchor", "No eligible CPT anchor"])

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 6.0), gridspec_kw={"hspace": 0.48, "wspace": 0.40})

    ax = axes[0, 0]
    bins = np.arange(0, 751, 30)
    ax.hist(widths.clip(upper=750), bins=bins, color=COL["blue"], alpha=0.85, edgecolor="white", linewidth=0.35)
    ax.axvline(widths.median(), color=COL["red"], lw=1.3, label=f"Median {widths.median():.0f} d")
    ax.axvspan(widths.quantile(.25), widths.quantile(.75), color=COL["orange"], alpha=0.16,
               label=f"IQR {widths.quantile(.25):.0f}-{widths.quantile(.75):.0f} d")
    ax.set_xlabel("Last-negative to first-positive interval, days\n(values >750 days shown in final bin)")
    ax.set_ylabel("Hardware detections")
    ax.set_title("a  Detection-interval width", loc="left", fontweight="bold", color=COL["navy"])
    ax.legend(fontsize=6.3)

    ax = axes[0, 1]
    colors = [COL["teal"], COL["orange"], COL["gray"]]
    bars = ax.bar(np.arange(3), relation.values, color=colors, width=0.68)
    for bar, value in zip(bars, relation.values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 18, f"{int(value):,}", ha="center", fontsize=6.8)
    ax.set_xticks(np.arange(3), ["By 24 mo", "Crosses 24 mo", "After 24 mo"], rotation=15)
    ax.set_ylabel("Hardware detections")
    ax.set_ylim(0, max(relation.values) * 1.16)
    ax.set_title("b  Identification at the 24-month horizon", loc="left", fontweight="bold", color=COL["navy"])
    ax.grid(axis="y", color=COL["light"], lw=0.7)

    ax = axes[1, 0]
    bars = ax.bar(np.arange(2), cpt.values, color=[COL["teal"], COL["gray"]], width=0.62)
    for bar, value in zip(bars, cpt.values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 18,
                f"{int(value):,}\n({value / len(intervals):.1%})", ha="center", fontsize=6.8)
    ax.set_xticks(np.arange(2), ["Temporally matched CPT\nwithin interval and ±90 d", "Other or unavailable"], rotation=0)
    ax.set_ylabel("Hardware detections")
    ax.set_ylim(0, max(cpt.values) * 1.18)
    ax.set_title("c  CPT support for timing (laterality not required)", loc="left", fontweight="bold", color=COL["navy"])
    ax.grid(axis="y", color=COL["light"], lw=0.7)

    ax = axes[1, 1]
    exact = timing.iloc[:3].copy()
    y = np.arange(3)[::-1]
    xerr = np.vstack([
        exact["observed_24m"] - exact["observed_lower_95"],
        exact["observed_upper_95"] - exact["observed_24m"],
    ])
    ax.errorbar(exact["observed_24m"], y, xerr=xerr, fmt="o", ms=5, capsize=3,
                color=COL["blue"], lw=1.2)
    labels = ["First-positive right endpoint", "CPT-timed hybrid", "Interval midpoint"]
    ax.set_yticks(y, labels)
    ax.set_xlim(0.25, 0.32)
    ax.set_xlabel("Observed 24-month risk (95% CI)")
    ax.set_title("d  Absolute-risk sensitivity", loc="left", fontweight="bold", color=COL["navy"])
    for yy, row in zip(y, exact.itertuples()):
        ax.text(row.observed_upper_95 + 0.001, yy, f"{row.observed_24m:.1%}", va="center", fontsize=6.3, color=COL["navy"])
    ax.grid(axis="x", color=COL["light"], lw=0.7)

    fig.suptitle("Supplementary Figure S10 | MRKR hardware outcome-timing audit",
                 x=0.06, ha="left", fontsize=9.2, fontweight="bold", color=COL["navy"])
    fig.subplots_adjust(left=0.10, right=0.98, bottom=0.10, top=0.91)
    save(fig, "supplementary_figure_s10_mrkr_hardware_timing_audit")

    pd.DataFrame({"interval_width_days": widths}).to_csv(
        LATEST / "source_data_supplementary_figure_s10a.csv", index=False
    )
    relation.rename_axis("horizon_relation").reset_index(name="n_events").to_csv(
        LATEST / "source_data_supplementary_figure_s10b.csv", index=False
    )
    cpt.rename_axis("cpt_timing_support").reset_index(name="n_events").to_csv(
        LATEST / "source_data_supplementary_figure_s10c.csv", index=False
    )
    exact.to_csv(LATEST / "source_data_supplementary_figure_s10d.csv", index=False)


def main() -> None:
    preserve_approved_figures()
    figure_s2()
    figure_s3()
    figure_s4()
    figure_s5()
    figure_s6()
    figure_s7()
    figure_s8()
    figure_s9()
    figure_s10()
    print(OUT)


if __name__ == "__main__":
    main()
