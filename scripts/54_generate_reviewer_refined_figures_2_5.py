#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"
LATEST = TABLES / "latest_framework"


def load_base():
    path = ROOT / "scripts" / "49_generate_latest_framework_figures.py"
    spec = importlib.util.spec_from_file_location("latest_figures", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


base = load_base()
COL = base.COL
save = base.save
panel_title = base.panel_title
km_curve = base.km_curve

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 8.0,
        "axes.titlesize": 9.0,
        "axes.labelsize": 8.2,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "legend.fontsize": 7.5,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
    }
)


MODEL_LABELS = [
    "A",
    "B",
    "C",
    "D",
    "E",
]


def figure2() -> None:
    p = pd.read_csv(LATEST / "latest_oai_staged_nested_performance.csv")
    inc = pd.read_csv(LATEST / "latest_oai_incremental_comparisons.csv")
    x = np.arange(len(p))
    fig, axs = plt.subplots(2, 2, figsize=(7.2, 5.65))

    ax = axs[0, 0]
    ax.plot(x, p.c_index, "o-", color="#A9BED2", lw=1.0, ms=4, label="Apparent")
    corrected_low = p.c_index_lower_95 - p.optimism_c
    corrected_high = p.c_index_upper_95 - p.optimism_c
    ax.errorbar(
        x,
        p.optimism_corrected_c,
        yerr=[p.optimism_corrected_c - corrected_low, corrected_high - p.optimism_corrected_c],
        fmt="s-",
        color=COL["blue"],
        lw=2.0,
        ms=4.5,
        capsize=3,
        label="Bootstrap optimism-corrected (95% CI)",
    )
    ax.set_xticks(x, MODEL_LABELS)
    ax.set_ylim(0.48, 0.82)
    ax.set_ylabel("Harrell C-index")
    panel_title(ax, "A", "Discrimination across strictly nested models")
    ax.grid(axis="y", alpha=0.22)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.20),
        ncol=2,
        fontsize=6.2,
        frameon=False,
        handletextpad=0.45,
        columnspacing=0.9,
    )

    ax = axs[0, 1]
    ax.errorbar(
        x,
        p.optimism_corrected_auc_60m,
        yerr=[
            p.optimism_corrected_auc_60m - p.corrected_auc_60m_lower_95,
            p.corrected_auc_60m_upper_95 - p.optimism_corrected_auc_60m,
        ],
        fmt="o-",
        color=COL["blue"],
        lw=1.9,
        capsize=3,
    )
    ax.set_xticks(x, MODEL_LABELS)
    ax.set_ylim(0.48, 0.85)
    ax.set_ylabel("60-month time-dependent AUC")
    panel_title(ax, "B", "Bootstrap optimism-corrected 60-month AUC")
    ax.grid(axis="y", alpha=0.22)

    ax = axs[1, 0]
    ax.errorbar(
        x,
        p.optimism_corrected_brier_60m,
        yerr=[
            p.optimism_corrected_brier_60m - p.corrected_brier_60m_lower_95,
            p.corrected_brier_60m_upper_95 - p.optimism_corrected_brier_60m,
        ],
        fmt="o-",
        color=COL["orange"],
        lw=1.9,
        capsize=3,
    )
    for xi, value in zip(x, p.optimism_corrected_brier_60m):
        ax.text(xi, value + 0.0017, f"{value:.3f}", ha="center", fontsize=7.2)
    ax.set_xticks(x, MODEL_LABELS)
    ax.set_ylim(0.09, 0.15)
    ax.set_ylabel("60-month IPCW Brier score")
    panel_title(ax, "C", "Bootstrap optimism-corrected prediction error")
    ax.text(0.02, 0.045, "Lower is better", transform=ax.transAxes, color="#8B949E", fontsize=6.6)
    ax.grid(axis="y", alpha=0.22)

    ax = axs[1, 1]
    y = np.arange(len(inc))[::-1]
    ax.axvline(0, color="#59636E", lw=1.0)
    ax.errorbar(
        inc.delta_c_index,
        y + 0.11,
        xerr=[inc.delta_c_index - inc.delta_c_lower_95, inc.delta_c_upper_95 - inc.delta_c_index],
        fmt="o",
        color=COL["blue"],
        capsize=3,
        label="Delta C-index",
    )
    ax.errorbar(
        inc.delta_auc_60m,
        y - 0.11,
        xerr=[inc.delta_auc_60m - inc.delta_auc_lower_95, inc.delta_auc_upper_95 - inc.delta_auc_60m],
        fmt="s",
        color=COL["teal"],
        capsize=3,
        label="Delta 60-month AUC",
    )
    labels = inc.comparison.tolist()
    labels[-1] = "Model E vs C*"
    ax.set_yticks(y, labels)
    ax.get_yticklabels()[-1].set_fontweight("bold")
    ax.set_xlim(-0.008, 0.270)
    ax.set_ylim(-0.45, 5.0)
    ax.set_xlabel("Absolute change in discrimination")
    panel_title(ax, "D", "Incremental comparisons")
    ax.grid(axis="x", alpha=0.22)
    for yi, row in zip(y, inc.itertuples()):
        weight = "bold" if row.comparison == inc.comparison.iloc[-1] else "normal"
        ax.text(
            0.205,
            yi,
            f"LR χ² = {row.lr_chisq:.1f}\nP < 0.001",
            va="center",
            fontsize=6.45,
            linespacing=1.35,
            color=COL["gray"],
            fontweight=weight,
        )
    ax.legend(loc="upper left", ncol=2, fontsize=6.2, frameon=False, handletextpad=0.45, columnspacing=0.9)
    fig.suptitle(
        "Incremental prognostic value of baseline and longitudinal clinical-radiographic information in OAI",
        fontsize=11,
        fontweight="bold",
        color=COL["navy"],
        y=0.995,
    )
    fig.text(
        0.5,
        0.018,
        "Models were strictly nested. All intervals were derived from participant-level bootstrap resampling.",
        ha="center",
        fontsize=6.6,
        color=COL["gray"],
    )
    fig.subplots_adjust(left=0.105, right=0.985, bottom=0.105, top=0.92, hspace=0.58, wspace=0.34)
    save(fig, "figure2_oai_incremental_value_strictly_nested")


def add_rug(ax, values: pd.Series, y: float, color: str, max_marks: int = 420) -> None:
    values = values.dropna().sort_values().to_numpy()
    if len(values) > max_marks:
        values = values[np.linspace(0, len(values) - 1, max_marks).astype(int)]
    ax.plot(values, np.full(len(values), y), "|", color=color, alpha=0.22, ms=3.0, mew=0.45, clip_on=True)


def figure3() -> None:
    horizon = pd.read_csv(LATEST / "revised_figure3_oai_cv_horizon_auc.csv")
    cal = pd.read_csv(TABLES / "reviewer_round2_oai_cv_calibration_curve.csv")
    dec = pd.read_csv(LATEST / "revised_figure3_oai_cv_calibration_deciles.csv")
    metrics = pd.read_csv(TABLES / "reviewer_round2_oai_cv_calibration_metrics.csv").iloc[0]
    predictions = pd.read_csv(LATEST / "revised_figure3_oai_cv_risk_predictions.csv")
    quartiles = pd.read_csv(LATEST / "revised_figure3_oai_cv_quartile_summary.csv").set_index("risk_quartile")
    dca = pd.read_csv(TABLES / "reviewer_round2_oai_cv_decision_curve.csv")

    fig = plt.figure(figsize=(7.2, 6.15))
    gs = fig.add_gridspec(2, 2, hspace=0.42, wspace=0.32)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    dgs = gs[1, 1].subgridspec(2, 1, height_ratios=[3.15, 1.55], hspace=0.10)
    ax_d = fig.add_subplot(dgs[0])
    ax_rt = fig.add_subplot(dgs[1])

    ax = ax_a
    ax.errorbar(
        horizon.horizon_months,
        horizon.auc,
        yerr=[horizon.auc - horizon.lower_95, horizon.upper_95 - horizon.auc],
        fmt="o-",
        color=COL["blue"],
        capsize=4,
        lw=1.8,
    )
    ax.set_xticks(horizon.horizon_months)
    ax.set_ylim(0.60, 0.90)
    ax.set_xlabel("Months after landmark")
    ax.set_ylabel("Time-dependent AUC")
    panel_title(ax, "A", "Participant-level cross-validated AUC")
    ax.grid(axis="y", alpha=0.22)

    ax = ax_b
    ax.plot([0, 0.55], [0, 0.55], "--", color="#9099A4", lw=1, label="Ideal")
    ax.fill_between(cal.predicted_risk, cal.lower_95, cal.upper_95, color=COL["blue"], alpha=0.12, linewidth=0)
    ax.plot(cal.predicted_risk, cal.observed_smooth, color=COL["blue"], lw=1.7, label="Pooled out-of-sample smooth")
    ax.errorbar(
        dec.mean_predicted_risk,
        dec.observed_risk,
        yerr=[dec.observed_risk - dec.observed_lower_95, dec.observed_upper_95 - dec.observed_risk],
        fmt="o",
        ms=3.6,
        color=COL["navy"],
        ecolor="#6F8295",
        capsize=2,
        label="Risk deciles (95% CI)",
    )
    ax.set_xlim(0, 0.55)
    ax.set_ylim(0, 0.55)
    ax.set_xlabel("Predicted 60-month risk")
    ax.set_ylabel("Observed 60-month risk")
    panel_title(ax, "B", "Participant-level 10-fold calibration")
    ax.text(
        0.025,
        0.975,
        f"Calibration intercept = {metrics.calibration_intercept:.3f}\nCalibration slope = {metrics.calibration_slope:.3f}\n60-month IPCW Brier = {metrics.brier_60m:.3f}",
        transform=ax.transAxes,
        va="top",
        fontsize=6.9,
        linespacing=1.25,
        color=COL["navy"],
    )
    ax.legend(loc="lower right", bbox_to_anchor=(0.995, 0.015), fontsize=6.0)

    ax = ax_c
    for label, color in [
        ("Model E updated clinical-radiographic", COL["blue"]),
        ("Model C baseline clinical-radiographic", COL["teal"]),
    ]:
        z = dca[dca.model == label]
        ax.plot(z.threshold, z.net_benefit, lw=1.8, color=color, label="Model E" if label.startswith("Model E") else "Model C")
    one = dca.iloc[: len(dca) // 2]
    ax.plot(one.threshold, one.treat_all, color=COL["gray"], ls="--", label="Follow-up for all")
    ax.axhline(0, color="#222222", lw=0.9, label="No follow-up")
    ax.set_xlim(0.02, 0.30)
    ax.set_xlabel("Risk threshold")
    ax.set_ylabel("Net benefit")
    panel_title(ax, "C", "Decision-curve analysis at 60 months")
    ax.legend(loc="lower left", ncol=2, fontsize=6.0, handletextpad=0.45, columnspacing=0.8)

    colors = ["#8FB2D1", "#4F85B5", "#D69A72", COL["red"]]
    styles = [":", "--", "-.", "-"]
    for (q, z), color, style in zip(predictions.groupby("risk_quartile", observed=True), colors, styles):
        xx, yy, _, _ = km_curve(z.time.to_numpy(), z.event.to_numpy())
        width = 2.1 if q == "Q4" else 1.5
        row = quartiles.loc[q]
        ax_d.step(xx, yy, where="post", color=color, ls=style, lw=width,
                  label=f"{q}: {row.risk_min:.1%}–{row.risk_max:.1%}")
    ax_d.set_xlim(0, 120)
    ax_d.set_ylim(0, 0.55)
    ax_d.set_xticks([0, 24, 60, 120])
    ax_d.tick_params(axis="x", labelbottom=False)
    ax_d.set_ylabel("Cumulative knee-replacement probability")
    panel_title(ax_d, "D", "Risk by out-of-sample predicted-risk quartile")
    ax_d.legend(loc="upper left", fontsize=5.8)

    ax_rt.axis("off")
    xcols = {"quartile": 0.01, "n": 0.30, "events": 0.43, "24": 0.62, "60": 0.78, "120": 0.94}
    for key, label in [("quartile", "Quartile"), ("n", "n"), ("events", "Events*"),
                       ("24", "24 mo"), ("60", "60 mo"), ("120", "120 mo")]:
        ax_rt.text(xcols[key], 0.94, label, transform=ax_rt.transAxes,
                   ha="left" if key == "quartile" else "center", va="top", fontsize=6.35, fontweight="bold")
    for yrow, q in zip([0.72, 0.52, 0.32, 0.12], ["Q1", "Q2", "Q3", "Q4"]):
        row = quartiles.loc[q]
        ax_rt.text(xcols["quartile"], yrow, q, transform=ax_rt.transAxes, ha="left", va="center", fontsize=6.3)
        ax_rt.text(xcols["n"], yrow, f"{int(row.knees):,}", transform=ax_rt.transAxes, ha="center", va="center", fontsize=6.3)
        ax_rt.text(xcols["events"], yrow, f"{int(row.events_by_60m):,}", transform=ax_rt.transAxes, ha="center", va="center", fontsize=6.3)
        for month, xpos in [(24, xcols["24"]), (60, xcols["60"]), (120, xcols["120"])]:
            ax_rt.text(xpos, yrow, f"{int(row[f'at_risk_{month}m']):,}", transform=ax_rt.transAxes,
                       ha="center", va="center", fontsize=6.3)

    fig.suptitle("Internal validation and clinical performance of OAI Model E", fontsize=11, fontweight="bold", color=COL["navy"], y=0.995)
    fig.text(0.105, 0.015, "Panels A, B, and D use the same pooled participant-level 10-fold out-of-sample predictions.", fontsize=6.7, color=COL["gray"])
    fig.subplots_adjust(left=0.105, right=0.985, bottom=0.10, top=0.93)
    save(fig, "figure3_oai_model_e_internal_validation")


def draw_km_with_risk_table(container, data, color, letter, title, ylabel):
    sub = container.subgridspec(2, 1, height_ratios=[4.0, 0.72], hspace=0.02)
    ax = plt.gcf().add_subplot(sub[0])
    rt = plt.gcf().add_subplot(sub[1], sharex=ax)
    horizons = [0, 12, 24, 36, 60]
    xx, yy, low, high = km_curve(data.time_months.to_numpy(), data.event_primary.to_numpy())
    ax.step(xx, yy, where="post", color=color, lw=1.9)
    ax.fill_between(xx, low, high, step="post", color=color, alpha=0.16, linewidth=0)
    ax.set_xlim(0, 60)
    ax.set_ylim(0, 0.50)
    ax.set_xticks(horizons)
    ax.tick_params(axis="x", labelbottom=False)
    ax.set_ylabel(ylabel)
    panel_title(ax, letter, title)
    ax.grid(axis="y", alpha=0.2)
    rt.set_xlim(0, 60)
    rt.set_ylim(0, 1)
    rt.set_xticks(horizons)
    rt.set_xlabel("Months after landmark")
    rt.set_yticks([])
    rt.text(-0.105, 0.66, "At risk", transform=rt.transAxes, ha="right", va="center", fontsize=6.8, fontweight="bold", clip_on=False)
    for h in horizons:
        rt.text(h, 0.66, f"{int((data.time_months >= h).sum()):,}", ha="center", va="center", fontsize=6.5)
    rt.spines[["top", "right", "left"]].set_visible(False)
    rt.tick_params(axis="y", length=0)
    return ax


def figure4() -> None:
    oai = pd.read_csv(ROOT / "derived" / "transport" / "oai_train_model_f_core.csv")
    mrkr = pd.read_csv(ROOT / "derived" / "transport" / "mrkr_validation_model_f_core.csv")
    intervals = pd.read_csv(LATEST / "latest_mrkr_hardware_detection_intervals.csv")
    fig = plt.figure(figsize=(7.2, 6.35))
    gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.34)
    draw_km_with_risk_table(gs[0, 0], oai, COL["blue"], "A", "OAI recorded post-landmark knee replacement", "Cumulative knee-replacement probability")
    draw_km_with_risk_table(gs[0, 1], mrkr, COL["orange"], "B", "MRKR first side-specific hardware detection", "Cumulative hardware-detection probability")

    ax = fig.add_subplot(gs[1, 0])
    for data, color, label in [
        (oai, COL["blue"], "OAI recorded knee replacement"),
        (mrkr, COL["orange"], "MRKR hardware detection"),
    ]:
        times = np.sort(data.loc[data.event_primary.eq(1) & data.time_months.le(60), "time_months"].to_numpy())
        ecdf = np.arange(1, len(times) + 1) / len(times)
        ax.step(times, ecdf, where="post", color=color, lw=1.8, label=f"{label} (n={len(times)})")
    ax.set_xlim(0, 60)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Observed event-ascertainment time, months")
    ax.set_ylabel("Cumulative proportion of events")
    panel_title(ax, "C", "Event-ascertainment times among event knees")
    ax.text(0.02, 0.96, "Events observed by 60 months only", transform=ax.transAxes, va="top", color="#8B949E", fontsize=6.4)
    ax.legend(loc="lower right", fontsize=6.1)
    ax.grid(axis="y", alpha=0.2)

    ax = fig.add_subplot(gs[1, 1])
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    panel_title(ax, "D", "MRKR interval-censored event time")
    ax.plot([0.12, 0.88], [0.55, 0.55], color="#AAB3BE", lw=2)
    ax.scatter([0.18], [0.55], s=45, color=COL["blue"], edgecolor="white", zorder=3)
    ax.scatter([0.82], [0.55], s=45, color=COL["orange"], edgecolor="white", zorder=3)
    ax.text(0.18, 0.72, "$L_i$\nLast side-specific\nhardware-negative image", ha="center", fontsize=7.9, fontweight="bold")
    ax.text(0.82, 0.72, "$R_i$\nFirst side-specific\nhardware-positive image", ha="center", fontsize=7.9, fontweight="bold")
    ax.annotate("", xy=(0.77, 0.46), xytext=(0.23, 0.46), arrowprops=dict(arrowstyle="<->", color=COL["gray"], lw=1.2))
    ax.text(0.50, 0.31, "The underlying arthroplasty was assumed\nto have occurred within $(L_i, R_i]$", ha="center", color=COL["navy"], fontsize=8.0, fontweight="bold", linespacing=1.25)
    ax.text(
        0.50,
        0.065,
        "Median interval: 83 days\nIQR: 43–157 days\n96 intervals >365 days; 62 crossed the 24-month horizon",
        ha="center",
        va="center",
        fontsize=7.2,
        linespacing=1.35,
        color=COL["navy"],
        bbox=dict(boxstyle="round,pad=.50", fc=COL["light"], ec="#C8CED6"),
    )
    assert len(intervals) == 1140
    fig.suptitle("Differences in follow-up and outcome-ascertainment structure between OAI and MRKR", fontsize=11, fontweight="bold", color=COL["navy"], y=0.995)
    fig.subplots_adjust(left=0.105, right=0.985, bottom=0.08, top=0.93)
    save(fig, "figure4_oai_mrkr_outcome_ascertainment")


def figure5() -> None:
    horizon = pd.read_csv(LATEST / "latest_mrkr_horizon_auc.csv")
    cal_original = pd.read_csv(TABLES / "reviewer_round2_mrkr_original_calibration_curve.csv")
    cal_updated = pd.read_csv(TABLES / "reviewer_round2_mrkr_oos_calibration_curve.csv")
    deciles = pd.read_csv(LATEST / "revised_figure5_mrkr_calibration_deciles.csv")
    predictions = pd.read_csv(TABLES / "reviewer_round2_mrkr_oos_predictions.csv")
    oos = pd.read_csv(TABLES / "reviewer_round2_mrkr_oos_performance.csv").iloc[0]
    split = pd.read_csv(TABLES / "reviewer_round2_mrkr_split_validation_summary.csv").set_index("metric")
    formal_brier = pd.read_csv(ROOT / "data" / "source_data" / "formal_mrkr_brier_comparison.csv").set_index("analysis")
    early = pd.read_csv(LATEST / "revised_figure5_mrkr_early_sensitivity.csv")

    fig = plt.figure(figsize=(7.2, 8.2))
    gs = fig.add_gridspec(3, 2, height_ratios=[1, 1, 1.05], hspace=0.50, wspace=0.36)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])
    egs = gs[2, :].subgridspec(1, 2, wspace=0.78)
    ax_e1 = fig.add_subplot(egs[0, 0])
    ax_e2 = fig.add_subplot(egs[0, 1])

    ax = ax_a
    ax.errorbar(horizon.horizon_months, horizon.auc,
                yerr=[horizon.auc - horizon.lower_95, horizon.upper_95 - horizon.auc],
                fmt="o-", color=COL["orange"], capsize=4, lw=1.8)
    ax.set_xticks(horizon.horizon_months)
    ax.set_ylim(0.60, 0.90)
    ax.set_xlabel("Months after landmark")
    ax.set_ylabel("Time-dependent AUC")
    panel_title(ax, "A", "Original OAI-derived Model F-core in MRKR")
    ax.grid(axis="y", alpha=0.22)

    ax = ax_b
    original_dec = deciles[deciles.analysis.eq("Original OAI-derived Model F-core")]
    xmax = 0.17
    ax.plot([0, xmax], [0, xmax], "--", color=COL["gray"], lw=1, label="Ideal")
    ax.fill_between(cal_original.predicted_risk, cal_original.lower_95, cal_original.upper_95, color=COL["orange"], alpha=0.13, linewidth=0)
    ax.plot(cal_original.predicted_risk, cal_original.observed_smooth, color=COL["orange"], lw=1.7, label="Calibration smooth")
    ax.errorbar(original_dec.mean_predicted_risk, original_dec.observed_risk,
                yerr=[original_dec.observed_risk-original_dec.observed_lower_95, original_dec.observed_upper_95-original_dec.observed_risk],
                fmt="o", ms=3.5, color="#9B4B2B", capsize=2, label="Risk deciles (95% CI)")
    ax.set_xlim(0, xmax)
    ax.set_ylim(0, 0.62)
    ax.set_xlabel("Original predicted 24-month risk")
    ax.set_ylabel("Observed hardware-detection probability")
    panel_title(ax, "B", "Original OAI-derived calibration")
    ax.text(0.04, 0.96, "Mean predicted 24-month risk = 4.4%\nObserved 24-month hardware-detection\nprobability = 28.0%", transform=ax.transAxes, va="top", fontsize=6.8, color=COL["navy"])
    ax.legend(loc="lower right", fontsize=6.4)

    ax = ax_c
    updated_dec = deciles[deciles.analysis.eq("Pooled out-of-sample recalibrated predictions")]
    lim = 0.65
    ax.plot([0, lim], [0, lim], "--", color=COL["gray"], lw=1, label="Ideal")
    ax.fill_between(cal_updated.predicted_risk, cal_updated.lower_95, cal_updated.upper_95, color=COL["teal"], alpha=0.13, linewidth=0)
    ax.plot(cal_updated.predicted_risk, cal_updated.observed_smooth, color=COL["teal"], lw=1.7, label="Pooled OOS smooth")
    ax.errorbar(updated_dec.mean_predicted_risk, updated_dec.observed_risk,
                yerr=[updated_dec.observed_risk-updated_dec.observed_lower_95, updated_dec.observed_upper_95-updated_dec.observed_risk],
                fmt="o", ms=3.5, color="#155D55", capsize=2, label="Risk deciles (95% CI)")
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
    ax.set_xlabel("Held-out recalibrated 24-month risk")
    ax.set_ylabel("Observed hardware-detection probability")
    panel_title(ax, "C", "Repeated patient-level held-out recalibration")
    slope = split.loc["validation_calibration_slope_test"]
    intercept = split.loc["validation_calibration_intercept_test"]
    ici = split.loc["ici_test"]
    ax.text(
        0.04,
        0.96,
        f"Pooled OOS intercept = {oos.calibration_intercept:.3f}\n"
        f"Pooled OOS slope = {oos.validation_calibration_slope:.3f}\n"
        f"ICI = {oos.ici:.3f}; Brier = {oos.brier_24m:.3f}",
        transform=ax.transAxes,
        va="top",
        fontsize=6.05,
        linespacing=1.22,
        color=COL["navy"],
    )
    ax.text(
        0.04,
        0.72,
        "Across 100 splits, median (2.5th–97.5th percentile):\n"
        f"Slope {slope['median']:.3f} ({slope.q025:.3f}–{slope.q975:.3f}); "
        f"intercept {intercept['median']:.3f} ({intercept.q025:.3f}–{intercept.q975:.3f})\n"
        f"ICI {ici['median']:.3f} ({ici.q025:.3f}–{ici.q975:.3f})",
        transform=ax.transAxes,
        va="top",
        fontsize=5.35,
        linespacing=1.20,
        color=COL["gray"],
    )
    ax.legend(loc="lower right", fontsize=6.2)

    ax = ax_d
    values = [
        formal_brier.loc["Direct transport", "brier_24m"],
        formal_brier.loc["Apparent recalibration", "brier_24m"],
        formal_brier.loc["Held-out recalibration", "brier_24m"],
        formal_brier.loc["Null model", "brier_24m"],
    ]
    labels = ["Direct\ntransport", "Apparent\nrecalibration", "Held-out\nrecalibration", "Null\nmodel"]
    colors = [COL["orange"], "#9CC7BD", COL["teal"], "#A8AFB8"]
    bars = ax.bar(np.arange(4), values, color=colors, width=0.65)
    held = split.loc["brier_24m"]
    null = split.loc["null_brier_24m"]
    ax.errorbar([2, 3], [values[2], values[3]],
                yerr=[[values[2]-held.q025, values[3]-null.q025], [held.q975-values[2], null.q975-values[3]]],
                fmt="none", ecolor=COL["navy"], capsize=3, lw=1)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, value + 0.007, f"{value:.3f}", ha="center", fontsize=7.3)
    ax.set_xticks(np.arange(4), labels)
    ax.set_ylim(0, 0.43)
    ax.set_ylabel("24-month IPCW Brier score")
    panel_title(ax, "D", "Overall prediction error")
    ax.text(0.03, 0.965, "Lower is better", transform=ax.transAxes, va="top", color=COL["gray"], fontsize=6.4)
    ax.text(0.98, 0.965, "Error bars: empirical 2.5th–97.5th percentiles", transform=ax.transAxes,
            ha="right", va="top", color=COL["gray"], fontsize=5.35)
    ax.grid(axis="y", alpha=0.2)

    y = np.arange(len(early))[::-1]
    ax = ax_e1
    ax.errorbar(early.observed_24m, y,
                xerr=[early.observed_24m-early.observed_lower_95, early.observed_upper_95-early.observed_24m],
                fmt="o", color=COL["orange"], capsize=3)
    ax.set_yticks(y, early.definition)
    ax.set_xlim(0.07, 0.32)
    ax.set_xlabel("Kaplan–Meier 24-month hardware-detection\nprobability (95% CI)")
    panel_title(ax, "E", "24-month risk after early-detection exclusions")
    ax.grid(axis="x", alpha=0.2)

    ax = ax_e2
    ax.errorbar(early.auc_24m, y,
                xerr=[early.auc_24m-early.auc_lower_95, early.auc_upper_95-early.auc_24m],
                fmt="o", color=COL["blue"], capsize=3)
    ax.set_yticks(y, early.definition)
    ax.tick_params(axis="y", labelsize=6.2, pad=3)
    ax.set_xlim(0.62, 0.80)
    for yi, row in zip(y, early.itertuples()):
        ax.text(
            0.797,
            yi,
            f"n={int(row.knees):,}; events={int(row.events_by_24m)}",
            ha="right",
            va="center",
            fontsize=5.75,
            color=COL["gray"],
        )
    ax.set_xlabel("24-month AUC (patient-clustered 95% CI)")
    panel_title(ax, "F", "Early-detection exclusion AUC")
    ax.grid(axis="x", alpha=0.2)

    fig.suptitle("MRKR transport performance, recalibration and robustness analyses", fontsize=11, fontweight="bold", color=COL["navy"], y=0.995)
    fig.text(0.5, 0.012, "Recalibration used 100 repeated 70/30 patient-level splits.", ha="center", fontsize=6.55, color=COL["gray"])
    fig.subplots_adjust(left=0.13, right=0.985, bottom=0.105, top=0.94)
    save(fig, "figure5_mrkr_transport_recalibration_robustness")


def main() -> None:
    figure2()
    figure3()
    figure4()
    figure5()
    print(base.OUT)


if __name__ == "__main__":
    main()
