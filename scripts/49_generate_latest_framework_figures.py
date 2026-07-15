#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"
LATEST = TABLES / "latest_framework"
OUT = ROOT / "results" / "figures" / "latest_framework"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        "font.family": "Arial",
        "font.size": 7.5,
        "axes.titlesize": 8.5,
        "axes.labelsize": 7.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.8,
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
    "green": "#4E8B57",
    "gray": "#667085",
    "light": "#F4F6F8",
    "pale_blue": "#EAF1F8",
    "pale_orange": "#FCF0E8",
}


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(OUT / f"{name}.png", dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / f"{name}.tiff", dpi=600, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / f"{name}.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def panel_title(ax: plt.Axes, letter: str, title: str) -> None:
    ax.set_title(f"{letter}. {title}", loc="left", fontweight="bold", color=COL["navy"], pad=8)


def rounded(ax, x, y, w, h, title, subtitle, fc, ec, title_frac=.63, subtitle_frac=.28,
            subtitle_size=6.8):
    patch = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.018",
        facecolor=fc, edgecolor=ec, linewidth=1.0,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h * title_frac, title, ha="center", va="center", fontsize=8.2,
            fontweight="bold", color=COL["navy"])
    ax.text(x + w / 2, y + h * subtitle_frac, subtitle, ha="center", va="center", fontsize=subtitle_size,
            color=COL["gray"], linespacing=1.25)


def arrow(ax, start, end, color="#8C99A8"):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=10,
                                linewidth=1.1, color=color))


def figure1() -> None:
    fig = plt.figure(figsize=(7.2, 6.8), facecolor="white")
    gs = fig.add_gridspec(3, 1, height_ratios=[1.1, 0.72, 0.9], hspace=0.30)

    ax = fig.add_subplot(gs[0]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.text(0.0, 1.02, "A. Cohort formation", fontweight="bold", fontsize=10, color=COL["navy"])
    ax.add_patch(FancyBboxPatch((0.015, 0.05), 0.465, 0.88, boxstyle="round,pad=0.012",
                                facecolor="#F7FAFD", edgecolor="#C5D6E6"))
    ax.add_patch(FancyBboxPatch((0.52, 0.05), 0.465, 0.88, boxstyle="round,pad=0.012",
                                facecolor="#FFF9F4", edgecolor="#E8CCB7"))
    ax.text(0.04, 0.86, "OAI development", color=COL["blue"], fontweight="bold", fontsize=9.2)
    ax.text(0.545, 0.86, "MRKR transport evaluation", color=COL["orange"], fontweight="bold", fontsize=9.2)
    rounded(ax, 0.055, 0.66, 0.385, 0.13, "9,592 knee rows / 4,796 participants",
            "Scheduled longitudinal symptoms and radiographs", COL["pale_blue"], "#91AFCC")
    rounded(ax, 0.56, 0.66, 0.385, 0.13, "9,115 baseline-landmark pairs / 5,162 patients",
            "Real-world imaging, pain and procedure records", COL["pale_orange"], "#DDA77E")
    arrow(ax, (0.247, 0.65), (0.247, 0.58)); arrow(ax, (0.752, 0.65), (0.752, 0.58))
    rounded(ax, 0.065, 0.35, 0.365, 0.21, "Sequential exclusions",
            "Prior/baseline or pre-landmark KR: 143\nNo post-landmark follow-up: 692\nMissing landmark pain: 443\nMissing F-core predictors: 5,210",
            "white", "#B8C6D5", title_frac=.90, subtitle_frac=.25, subtitle_size=5.8)
    rounded(ax, 0.57, 0.35, 0.365, 0.21, "Sequential exclusions",
            "No valid post-landmark ascertainment interval: 4,506\nMissing landmark pain: 1,197\nMissing laterality, KL, age or sex: 0",
            "white", "#D7C1AF", title_frac=.88, subtitle_frac=.25, subtitle_size=5.9)
    arrow(ax, (0.247, 0.34), (0.247, 0.29)); arrow(ax, (0.752, 0.34), (0.752, 0.29))
    rounded(ax, 0.035, 0.09, 0.205, 0.17, "Model F-core",
            "3,104 knees / 1,656 participants\n566 recorded KR events", COL["pale_blue"], "#7D9FC2")
    rounded(ax, 0.255, 0.09, 0.205, 0.17, "Model E",
            "3,066 knees / 1,640 participants\n559 recorded KR events", "#E9F5F2", "#75AD9F")
    rounded(ax, 0.59, 0.09, 0.325, 0.17, "Model F-core transport cohort",
            "3,412 knees / 2,179 patients\n1,140 hardware detections; 855 by 24 months",
            COL["pale_orange"], "#D79B6E")

    ax = fig.add_subplot(gs[1]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.text(0.0, 1.02, "B. Twenty-four-month landmark design", fontweight="bold", fontsize=10, color=COL["navy"])
    ax.plot([0.07, 0.93], [0.55, 0.55], color="#A7B2BF", lw=2)
    arrow(ax, (0.90, 0.55), (0.96, 0.55))
    for x, label, c in [(0.10, "Baseline", COL["blue"]), (0.48, "24-month landmark", COL["teal"]),
                        (0.88, "Post-landmark", COL["orange"])]:
        ax.add_patch(Circle((x, 0.55), 0.025, facecolor=c, edgecolor="white", linewidth=1.3, zorder=3))
        ax.text(x, 0.73, label, ha="center", fontweight="bold", color=COL["navy"])
    rounded(ax, 0.035, 0.10, 0.20, 0.25, "Baseline state", "Symptoms, KL grade and JSN", COL["pale_blue"], "#A9C0D7")
    rounded(ax, 0.35, 0.10, 0.26, 0.25, "Updated state", "0-24 month symptom and\nstructural information", "#E9F5F2", "#99C7BC")
    rounded(ax, 0.73, 0.10, 0.25, 0.25, "Future outcome", "OAI: recorded knee replacement\nMRKR: hardware-positive image",
            COL["pale_orange"], "#E1B693")
    ax.text(0.30, 0.88, "Replacement before or at landmark excluded", ha="center",
            fontsize=7.2, color=COL["red"], fontweight="bold")

    ax = fig.add_subplot(gs[2]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.text(0.0, 1.02, "C. Distinct model roles and outcome meaning", fontweight="bold", fontsize=10, color=COL["navy"])
    rounded(ax, 0.025, 0.48, 0.25, 0.34, "Model E: full OAI dynamic model",
            "Baseline symptoms, KL/JSN plus\n0-24 month symptom and structural changes", "#E9F5F2", "#72AB9E")
    rounded(ax, 0.035, 0.13, 0.23, 0.19, "Internal validation", "Incremental value, calibration and utility", "#F5FAF8", "#B5D6CE")
    arrow(ax, (0.15, 0.47), (0.15, 0.33), COL["teal"])
    rounded(ax, 0.32, 0.48, 0.20, 0.34, "Model F-core",
            "Age, sex, knee side, landmark pain,\nbaseline KL and KL worsening", COL["pale_blue"], "#7D9FC2")
    rounded(ax, 0.57, 0.51, 0.16, 0.28, "Direct transport", "Original OAI-derived score", COL["pale_orange"], "#DDA77E")
    rounded(ax, 0.78, 0.51, 0.19, 0.28, "Local recalibration", "Slope plus baseline updating", "#EEF6F0", "#91B69A")
    arrow(ax, (0.52, 0.65), (0.57, 0.65)); arrow(ax, (0.73, 0.65), (0.78, 0.65))
    rounded(ax, 0.56, 0.13, 0.41, 0.20, "MRKR endpoint",
            "First side-matched hardware-positive postoperative radiograph\nImaging ascertainment date, not the exact operation date",
            "#F7F8FA", "#B5BEC9")
    arrow(ax, (0.87, 0.50), (0.78, 0.34), COL["green"])
    fig.subplots_adjust(left=0.035, right=0.985, top=0.97, bottom=0.035)
    save(fig, "figure1_study_design_cohort_flow_landmark")


def figure2() -> None:
    p = pd.read_csv(LATEST / "latest_oai_staged_nested_performance.csv")
    inc = pd.read_csv(LATEST / "latest_oai_incremental_comparisons.csv")
    x = np.arange(len(p))
    labels = ["A\nDemographics", "B\n+ baseline\nsymptoms", "C\n+ baseline\nKL/JSN",
              "D\n+ symptom\nchanges", "E\n+ structural\nchanges"]
    fig, axs = plt.subplots(2, 2, figsize=(7.2, 5.5))
    ax = axs[0, 0]
    ax.errorbar(x, p.c_index, yerr=[p.c_index-p.c_index_lower_95, p.c_index_upper_95-p.c_index],
                fmt="o-", color=COL["blue"], capsize=3, label="Apparent")
    ax.plot(x, p.optimism_corrected_c, "s--", color=COL["teal"], label="Optimism-corrected")
    ax.set_xticks(x, labels); ax.set_ylim(0.49, 0.82); ax.set_ylabel("Harrell C-index")
    panel_title(ax, "A", "Discrimination across strictly nested models")
    ax.legend(frameon=False, loc="upper left"); ax.grid(axis="y", alpha=.22)

    ax = axs[0, 1]
    ax.errorbar(x, p.auc_60m, yerr=[p.auc_60m-p.auc_60m_lower_95, p.auc_60m_upper_95-p.auc_60m],
                fmt="o-", color=COL["teal"], capsize=3)
    ax.set_xticks(x, labels); ax.set_ylim(0.48, 0.85); ax.set_ylabel("60-month time-dependent AUC")
    panel_title(ax, "B", "Fixed-horizon discrimination")
    ax.grid(axis="y", alpha=.22)

    ax = axs[1, 0]
    ax.plot(x, p.brier_60m, "o-", color=COL["orange"], lw=1.6)
    for xi, v in zip(x, p.brier_60m):
        ax.text(xi, v + .0015, f"{v:.3f}", ha="center", va="bottom", fontsize=7.3)
    ax.set_xticks(x, labels); ax.set_ylim(0.10, 0.135); ax.set_ylabel("60-month IPCW Brier score")
    panel_title(ax, "C", "Overall prediction error")
    ax.text(.02, .08, "Lower is better", transform=ax.transAxes, color=COL["gray"], fontsize=7.5)
    ax.grid(axis="y", alpha=.22)

    ax = axs[1, 1]
    y = np.arange(len(inc))[::-1]
    ax.axvline(0, color="#9AA4AF", lw=.8)
    ax.errorbar(inc.delta_c_index, y + .10,
                xerr=[inc.delta_c_index-inc.delta_c_lower_95, inc.delta_c_upper_95-inc.delta_c_index],
                fmt="o", color=COL["blue"], capsize=3, label="Delta C-index")
    ax.errorbar(inc.delta_auc_60m, y - .10,
                xerr=[inc.delta_auc_60m-inc.delta_auc_lower_95, inc.delta_auc_upper_95-inc.delta_auc_60m],
                fmt="s", color=COL["teal"], capsize=3, label="Delta 60-month AUC")
    ax.set_yticks(y, inc.comparison); ax.set_xlabel("Increment in predictive performance")
    panel_title(ax, "D", "Incremental comparisons")
    ax.legend(frameon=False, fontsize=7.3, loc="upper center", bbox_to_anchor=(.5, -.20), ncol=2)
    ax.grid(axis="x", alpha=.22)
    for yi, (_, r) in zip(y, inc.iterrows()):
        ax.text(.145, yi, f"LR chi-square {r.lr_chisq:.1f}; P<0.001", va="center", fontsize=6.8, color=COL["gray"])
    ax.set_xlim(-.005, .23)
    fig.suptitle("Incremental prognostic value of baseline and longitudinal clinical-radiographic information in OAI",
                 fontsize=10.5, fontweight="bold", color=COL["navy"], y=.995)
    fig.subplots_adjust(left=.10, right=.985, bottom=.10, top=.93, hspace=.40, wspace=.32)
    save(fig, "figure2_oai_incremental_value_strictly_nested")


def km_curve(time: np.ndarray, event: np.ndarray):
    order = np.argsort(time); time = np.asarray(time)[order]; event = np.asarray(event)[order]
    unique_events = np.unique(time[event == 1])
    xs = [0.0]; surv = [1.0]; lower = [1.0]; upper = [1.0]
    s = 1.0; greenwood = 0.0
    for t in unique_events:
        n = np.sum(time >= t); d = np.sum((time == t) & (event == 1))
        if n <= 0: continue
        s *= 1 - d / n
        if n > d: greenwood += d / (n * (n - d))
        se = s * np.sqrt(greenwood)
        xs.append(float(t)); surv.append(s); lower.append(max(0, s - 1.96 * se)); upper.append(min(1, s + 1.96 * se))
    return np.asarray(xs), 1-np.asarray(surv), 1-np.asarray(upper), 1-np.asarray(lower)


def figure3() -> None:
    h = pd.read_csv(LATEST / "latest_oai_model_e_horizon_auc.csv")
    cal = pd.read_csv(TABLES / "reviewer_round2_oai_cv_calibration_curve.csv")
    cm = pd.read_csv(TABLES / "reviewer_round2_oai_cv_calibration_metrics.csv").iloc[0]
    dca = pd.read_csv(TABLES / "reviewer_round2_oai_cv_decision_curve.csv")
    risk = pd.read_csv(LATEST / "latest_oai_model_e_risk_predictions.csv")
    fig, axs = plt.subplots(2, 2, figsize=(7.2, 5.8))

    ax = axs[0, 0]
    ax.errorbar(h.horizon_months, h.auc, yerr=[h.auc-h.lower_95, h.upper_95-h.auc],
                fmt="o-", color=COL["blue"], capsize=4)
    ax.set_xticks(h.horizon_months); ax.set_ylim(.70, .90); ax.set_xlabel("Months after landmark"); ax.set_ylabel("AUC")
    panel_title(ax, "A", "Model E time-dependent discrimination")
    ax.grid(axis="y", alpha=.22)

    ax = axs[0, 1]
    ax.plot([0, .55], [0, .55], "--", color="#9099A4", lw=1, label="Ideal")
    ax.fill_between(cal.predicted_risk, cal.lower_95, cal.upper_95, color=COL["blue"], alpha=.15, linewidth=0)
    ax.plot(cal.predicted_risk, cal.observed_smooth, color=COL["blue"], lw=1.8, label="10-fold out-of-sample")
    ax.set_xlim(0, .55); ax.set_ylim(0, .55); ax.set_xlabel("Predicted 60-month risk"); ax.set_ylabel("Observed 60-month risk")
    panel_title(ax, "B", "Cross-validated calibration")
    ax.text(.03, .95, f"Intercept {cm.calibration_intercept:.3f}\nSlope {cm.calibration_slope:.3f}\nBrier {cm.brier_60m:.3f}",
            transform=ax.transAxes, va="top", fontsize=7.5, color=COL["navy"])
    ax.legend(frameon=False, loc="lower right", fontsize=7.5)

    ax = axs[1, 0]
    for label, c in [("Model E updated clinical-radiographic", COL["blue"]),
                     ("Model C baseline clinical-radiographic", COL["teal"])]:
        z = dca[dca.model == label]
        ax.plot(z.threshold, z.net_benefit, lw=1.8, color=c,
                label="Model E" if label.startswith("Model E") else "Model C")
    one = dca.iloc[: len(dca)//2]
    ax.plot(one.threshold, one.treat_all, color=COL["gray"], ls="--", label="Intervene in all")
    ax.axhline(0, color="#222222", lw=.9, label="Intervene in none")
    ax.set_xlim(.02, .30); ax.set_xlabel("Risk threshold"); ax.set_ylabel("Net benefit")
    panel_title(ax, "C", "Decision-curve analysis at 60 months")
    ax.legend(frameon=False, fontsize=7.1, loc="upper right")

    ax = axs[1, 1]
    colors = ["#9DB9D3", "#5F8FB8", "#D69A72", "#B64040"]
    for (q, z), c in zip(risk.groupby("risk_quartile", observed=True), colors):
        x, y, _, _ = km_curve(z.time.to_numpy(), z.event.to_numpy())
        ax.step(x, y, where="post", lw=1.7, color=c, label=q)
    ax.set_xlim(0, 120); ax.set_ylim(0, .55); ax.set_xlabel("Months after landmark"); ax.set_ylabel("Cumulative knee-replacement probability")
    panel_title(ax, "D", "Observed risk by Model E predicted-risk quartile")
    ax.legend(frameon=False, title="Risk quartile", fontsize=7.4)
    fig.suptitle("Internal validation and clinical performance of OAI Model E",
                 fontsize=10.5, fontweight="bold", color=COL["navy"], y=.995)
    fig.subplots_adjust(left=.09, right=.985, bottom=.09, top=.93, hspace=.38, wspace=.30)
    save(fig, "figure3_oai_model_e_internal_validation")


def add_at_risk(ax, time, horizons):
    values = [int(np.sum(np.asarray(time) >= h)) for h in horizons]
    ax.text(-.24, -.24, "At risk", transform=ax.transAxes, fontsize=7.2, fontweight="bold", clip_on=False)
    xmin, xmax = ax.get_xlim()
    for h, n in zip(horizons, values):
        ax.text((h-xmin)/(xmax-xmin), -.24, f"{n:,}", transform=ax.transAxes, ha="center", fontsize=7, clip_on=False)


def figure4() -> None:
    oai = pd.read_csv(ROOT / "derived" / "transport" / "oai_train_model_f_core.csv")
    mr = pd.read_csv(ROOT / "derived" / "transport" / "mrkr_validation_model_f_core.csv")
    intervals = pd.read_csv(LATEST / "latest_mrkr_hardware_detection_intervals.csv")
    fig, axs = plt.subplots(2, 2, figsize=(7.2, 6.2))
    horizons = [0, 12, 24, 36, 60]
    for ax, d, color, title, ylabel in [
        (axs[0, 0], oai, COL["blue"], "OAI recorded knee replacement", "Cumulative knee-replacement probability"),
        (axs[0, 1], mr, COL["orange"], "MRKR postoperative hardware detection", "Cumulative hardware-detection probability"),
    ]:
        x, y, lo, hi = km_curve(d.time_months.to_numpy(), d.event_primary.to_numpy())
        ax.step(x, y, where="post", color=color, lw=1.9)
        ax.fill_between(x, lo, hi, step="post", color=color, alpha=.14, linewidth=0)
        ax.set_xlim(0, 60); ax.set_xticks(horizons); ax.set_xlabel("Months after landmark"); ax.set_ylabel(ylabel)
        panel_title(ax, "A" if ax is axs[0, 0] else "B", title)
        ax.grid(axis="y", alpha=.2); add_at_risk(ax, d.time_months, horizons)

    ax = axs[1, 0]
    bins = np.arange(0, 61, 3)
    oe = oai.loc[oai.event_primary.eq(1) & oai.time_months.le(60), "time_months"]
    me = mr.loc[mr.event_primary.eq(1) & mr.time_months.le(60), "time_months"]
    ax.hist(oe, bins=bins, density=True, histtype="step", lw=1.8, color=COL["blue"], label="OAI recorded KR")
    ax.hist(me, bins=bins, density=True, histtype="step", lw=1.8, color=COL["orange"], label="MRKR hardware detection")
    ax.set_xlabel("Observed event/detection time after landmark, months"); ax.set_ylabel("Density")
    panel_title(ax, "C", "Different observed timing distributions")
    ax.legend(frameon=False, fontsize=7.4)

    ax = axs[1, 1]; ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    panel_title(ax, "D", "MRKR event-time interval")
    ax.plot([.10, .90], [.48, .48], color="#AAB3BE", lw=2)
    for x, c in [(.18, COL["blue"]), (.82, COL["orange"])]:
        ax.add_patch(Circle((x, .48), .025, facecolor=c, edgecolor="white", linewidth=1.2, zorder=3))
    ax.text(.18, .64, "Last hardware-negative\nradiograph", ha="center", fontweight="bold", fontsize=8)
    ax.text(.82, .64, "First hardware-positive\nradiograph", ha="center", fontweight="bold", fontsize=8)
    ax.add_patch(FancyArrowPatch((.23, .35), (.77, .35), arrowstyle="<->", mutation_scale=11,
                                color=COL["gray"], lw=1.2))
    ax.text(.50, .27, "True surgery occurred within this interval", ha="center", color=COL["gray"], fontsize=8)
    ax.text(.50, .08, "Median 83 days (IQR 43-157); 96 intervals >365 days;\n62 intervals crossed the 24-month horizon",
            ha="center", fontsize=8, color=COL["navy"],
            bbox=dict(boxstyle="round,pad=.35", fc=COL["light"], ec="#C8CED6"))
    fig.suptitle("Differences in follow-up and outcome ascertainment between OAI and MRKR",
                 fontsize=10.5, fontweight="bold", color=COL["navy"], y=.995)
    fig.subplots_adjust(left=.09, right=.985, bottom=.10, top=.93, hspace=.50, wspace=.34)
    save(fig, "figure4_oai_mrkr_outcome_ascertainment")


def figure5() -> None:
    h = pd.read_csv(LATEST / "latest_mrkr_horizon_auc.csv")
    cal_o = pd.read_csv(TABLES / "reviewer_round2_mrkr_original_calibration_curve.csv")
    cal_u = pd.read_csv(TABLES / "reviewer_round2_mrkr_oos_calibration_curve.csv")
    oos = pd.read_csv(TABLES / "reviewer_round2_mrkr_oos_performance.csv").iloc[0]
    strict = pd.read_csv(TABLES / "oai_mrkr_plan_mrkr_strict_sensitivity_24m.csv")
    timing = pd.read_csv(LATEST / "latest_mrkr_timing_sensitivity.csv")
    fig, axs = plt.subplots(3, 2, figsize=(7.2, 8.4))

    ax = axs[0, 0]
    ax.errorbar(h.horizon_months, h.auc, yerr=[h.auc-h.lower_95, h.upper_95-h.auc],
                fmt="o-", color=COL["blue"], capsize=4)
    ax.set_xticks(h.horizon_months); ax.set_ylim(.64, .82); ax.set_xlabel("Months after landmark"); ax.set_ylabel("Time-dependent AUC")
    panel_title(ax, "A", "Direct-transport discrimination")
    ax.grid(axis="y", alpha=.22)

    ax = axs[0, 1]
    lim = .32
    ax.plot([0, lim], [0, lim], "--", color="#9099A4", lw=1)
    ax.fill_between(cal_o.predicted_risk, cal_o.lower_95, cal_o.upper_95, color=COL["orange"], alpha=.15, linewidth=0)
    ax.plot(cal_o.predicted_risk, cal_o.observed_smooth, color=COL["orange"], lw=1.8)
    ax.set_xlim(0, lim); ax.set_ylim(0, .60); ax.set_xlabel("Original predicted 24-month risk"); ax.set_ylabel("Observed hardware-detection probability")
    panel_title(ax, "B", "Original OAI-derived calibration")
    ax.text(.04, .96, "Mean predicted 4.4%\nObserved 28.0%", transform=ax.transAxes, va="top", fontsize=7.8, color=COL["navy"])

    ax = axs[1, 0]
    lim = .80
    ax.plot([0, lim], [0, lim], "--", color="#9099A4", lw=1)
    ax.fill_between(cal_u.predicted_risk, cal_u.lower_95, cal_u.upper_95, color=COL["teal"], alpha=.15, linewidth=0)
    ax.plot(cal_u.predicted_risk, cal_u.observed_smooth, color=COL["teal"], lw=1.8)
    ax.set_xlim(0, lim); ax.set_ylim(0, lim); ax.set_xlabel("Held-out recalibrated 24-month risk"); ax.set_ylabel("Observed hardware-detection probability")
    panel_title(ax, "C", "Held-out recalibration performance")
    ax.text(.04, .96, f"Slope {oos.validation_calibration_slope:.3f}\nIntercept {oos.calibration_intercept:.3f}\nICI {oos.ici:.3f}",
            transform=ax.transAxes, va="top", fontsize=7.6, color=COL["navy"])

    ax = axs[1, 1]
    labels = ["Direct transport", "Apparent update", "Held-out update", "Null model"]
    values = [.3588469, .262, float(oos.brier_24m), float(oos.null_brier_24m)]
    colors = [COL["orange"], "#9CC7BD", COL["teal"], "#A8AFB8"]
    bars = ax.bar(np.arange(4), values, color=colors, width=.65)
    for b, v in zip(bars, values): ax.text(b.get_x()+b.get_width()/2, v+.006, f"{v:.3f}", ha="center", fontsize=7.5)
    ax.set_xticks(np.arange(4), labels, rotation=15, ha="right"); ax.set_ylim(0, .41); ax.set_ylabel("24-month IPCW Brier score")
    panel_title(ax, "D", "Overall prediction error")

    ax = axs[2, 0]
    y = np.arange(len(strict))[::-1]
    names = ["All detections", "Exclude <=3 months", "Exclude <=6 months", "Exclude <=12 months"]
    ax.plot(strict.auc_24m, y, "o-", color=COL["blue"], label="AUC")
    ax.plot(strict.observed_km_24m_risk, y, "s--", color=COL["orange"], label="Observed risk")
    ax.set_yticks(y, names); ax.set_xlim(.05, .76); ax.set_xlabel("Estimate")
    panel_title(ax, "E", "Early-detection exclusion sensitivity")
    ax.legend(frameon=False, fontsize=7.4); ax.grid(axis="x", alpha=.22)
    for yi, a, r in zip(y, strict.auc_24m, strict.observed_km_24m_risk):
        ax.text(a+.012, yi+.08, f"AUC {a:.3f}", fontsize=6.8, color=COL["blue"])
        ax.text(r+.012, yi-.15, f"Risk {100*r:.1f}%", fontsize=6.8, color=COL["orange"])

    ax = axs[2, 1]
    labels = ["Image right endpoint", "CPT-timed within interval", "Interval midpoint", "Interval-censored model"]
    y = np.arange(4)[::-1]
    ax.errorbar(timing.auc_24m.iloc[:3], y[:3],
                xerr=[timing.auc_24m.iloc[:3]-timing.auc_lower_95.iloc[:3], timing.auc_upper_95.iloc[:3]-timing.auc_24m.iloc[:3]],
                fmt="o", color=COL["teal"], capsize=3)
    ax.scatter(timing.auc_24m.iloc[3], y[3], marker="D", color=COL["red"], s=34)
    ax.set_yticks(y, labels); ax.set_xlim(.67, .77); ax.set_xlabel("24-month AUC")
    panel_title(ax, "F", "Outcome-time definition sensitivity")
    ax.grid(axis="x", alpha=.22)
    for yi, (_, r) in zip(y, timing.iterrows()):
        ax.text(.742, yi, f"{r.auc_24m:.3f}; {int(r.events_by_24m)} events", va="center", fontsize=6.6)
    fig.suptitle("MRKR transport performance, recalibration and robustness analyses",
                 fontsize=10.5, fontweight="bold", color=COL["navy"], y=.998)
    fig.subplots_adjust(left=.15, right=.985, bottom=.07, top=.95, hspace=.48, wspace=.34)
    save(fig, "figure5_mrkr_transport_recalibration_robustness")


def main() -> None:
    figure1(); figure2(); figure3(); figure4(); figure5()
    print(f"Wrote latest-framework figures to {OUT}")


if __name__ == "__main__":
    main()
