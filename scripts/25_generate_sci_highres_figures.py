#!/usr/bin/env python3
"""Generate SCI-style high-resolution figures for the OAI/MRKR manuscript."""

from __future__ import annotations

from pathlib import Path
import textwrap

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"
FIGS = ROOT / "results" / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

BLUE = "#1F5D99"
NAVY = "#0B2545"
TEAL = "#1F7A5C"
ORANGE = "#B45F06"
RED = "#9B1C1C"
GRAY = "#52616B"
LIGHT_BLUE = "#EAF3FB"
LIGHT_ORANGE = "#FFF4E6"
LIGHT_GREEN = "#EAF7F0"
LIGHT_RED = "#FFF1F1"

mpl.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9.5,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
    "figure.titlesize": 13,
    "figure.titleweight": "bold",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
})


def save_all(fig: plt.Figure, stem: str, wspace: bool = True) -> None:
    if wspace:
        fig.tight_layout()
    for ext in ["png", "pdf", "svg"]:
        path = FIGS / f"{stem}.{ext}"
        if ext == "png":
            fig.savefig(path, dpi=600, bbox_inches="tight", facecolor="white")
        else:
            fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def box(ax, xy, wh, text, fc, ec=NAVY, fontsize=9, weight="normal", radius=0.025):
    x, y = xy
    w, h = wh
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.015,rounding_size={radius}",
        linewidth=1.0,
        edgecolor=ec,
        facecolor=fc,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, color=NAVY, fontweight=weight, linespacing=1.15)
    return patch


def arrow(ax, start, end, color=GRAY, rad=0):
    arr = FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=12,
                          linewidth=1.0, color=color,
                          connectionstyle=f"arc3,rad={rad}")
    ax.add_patch(arr)


def pct(x):
    return f"{100*x:.1f}%"


def fig1_cohort_flow():
    oai = pd.read_csv(TABLES / "oai_reviewer_inclusion_exclusion_flow.csv")
    mrkr = pd.read_csv(TABLES / "mrkr_reviewer_inclusion_exclusion_flow.csv")
    fig, ax = plt.subplots(figsize=(12.5, 7.2))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.02, 0.965, "OAI model development", color=NAVY, fontweight="bold", fontsize=13)
    ax.text(0.52, 0.965, "MRKR transport validation", color=NAVY, fontweight="bold", fontsize=13)

    oai_steps = [
        ("OAI knee rows assembled\n9,592 knees / 4,796 participants", LIGHT_BLUE),
        ("Exclude baseline/prior KR/TKA\n69 knees", LIGHT_ORANGE),
        ("Exclude KR/TKA <=24-month landmark\n74 knees", LIGHT_ORANGE),
        ("Exclude no post-landmark follow-up\n692 knees", LIGHT_ORANGE),
        ("Exclude missing 24-month pain\n443 knees", LIGHT_ORANGE),
        ("Exclude missing Model F-core predictors\n5,210 knees", LIGHT_ORANGE),
        ("OAI Model F-core training set\n3,104 knees / 1,656 participants\n566 KR/TKA events", LIGHT_GREEN),
        ("OAI Model E common-complete set\n3,066 knees / 1,640 participants\n559 KR/TKA events", LIGHT_GREEN),
    ]
    y = 0.86
    prev = None
    for i, (txt, fc) in enumerate(oai_steps):
        h = 0.075 if i < 6 else 0.09
        b = box(ax, (0.04, y - h), (0.39, h), txt, fc, fontsize=8.4, weight="bold" if i in [0, 6, 7] else "normal")
        if prev is not None:
            arrow(ax, (0.235, prev[1] - 0.003), (0.235, y + 0.004))
        prev = (b, y - h)
        y -= h + 0.028

    mrkr_steps = [
        ("MRKR baseline-landmark knee pairs\n9,115 knees / 5,162 patients", LIGHT_BLUE),
        ("Exclude no positive hardware follow-up\n4,506 knees", LIGHT_ORANGE),
        ("Exclude missing/ambiguous laterality\n0 knees", LIGHT_ORANGE),
        ("Exclude missing landmark pain\n1,197 knees", LIGHT_ORANGE),
        ("Exclude missing KL information\n0 knees", LIGHT_ORANGE),
        ("Exclude missing age/sex\n0 knees", LIGHT_ORANGE),
        ("MRKR Model F-core validation set\n3,412 knees / 2,179 patients\n1,140 hardware events", LIGHT_GREEN),
    ]
    y = 0.86
    prev = None
    for i, (txt, fc) in enumerate(mrkr_steps):
        h = 0.078 if i < 6 else 0.095
        b = box(ax, (0.56, y - h), (0.39, h), txt, fc, fontsize=8.4, weight="bold" if i in [0, 6] else "normal")
        if prev is not None:
            arrow(ax, (0.755, prev[1] - 0.003), (0.755, y + 0.004))
        prev = (b, y - h)
        y -= h + 0.033

    ax.text(
        0.5, 0.035,
        "KR/TKA, knee replacement or total knee arthroplasty; KL, Kellgren-Lawrence grade. "
        "OAI produced both the full Model E set and the common-variable Model F-core training set.",
        ha="center", va="center", fontsize=8.2, color=GRAY,
    )
    save_all(fig, "figure_oai_mrkr_sci_1_cohort_flow", wspace=False)


def fig2_framework():
    fig, ax = plt.subplots(figsize=(11.2, 5.6))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.04, 0.92, "Scientific OAI dynamic model", color=NAVY, fontweight="bold", fontsize=12.5)
    ax.text(0.44, 0.92, "Common-variable transport model", color=NAVY, fontweight="bold", fontsize=12.5)

    box(ax, (0.05, 0.70), (0.25, 0.12), "OAI 24-month\nlandmark cohort", LIGHT_BLUE, weight="bold")
    box(ax, (0.05, 0.48), (0.25, 0.12), "Sequential models\nA to E", LIGHT_BLUE)
    box(ax, (0.05, 0.26), (0.25, 0.14), "Primary Model E\nbaseline symptoms + baseline KL/JSN\n+ 0-24m symptom/structure change", LIGHT_GREEN, fontsize=8.2, weight="bold")
    arrow(ax, (0.175, 0.70), (0.175, 0.60))
    arrow(ax, (0.175, 0.48), (0.175, 0.40))

    box(ax, (0.43, 0.68), (0.22, 0.14), "OAI Model F-core\nage, sex, side,\nstandardized pain,\nbaseline KL, KL worsening", LIGHT_BLUE, fontsize=8.2, weight="bold")
    box(ax, (0.72, 0.68), (0.22, 0.14), "MRKR validation\nside-specific hardware outcome", LIGHT_BLUE, fontsize=8.4, weight="bold")
    box(ax, (0.43, 0.40), (0.22, 0.12), "Transport validation\nC-index, AUC,\ncalibration, DCA", LIGHT_GREEN, fontsize=8.4)
    box(ax, (0.72, 0.40), (0.22, 0.12), "Slope + baseline\nrecalibration", LIGHT_GREEN, fontsize=8.4)
    box(ax, (0.57, 0.17), (0.25, 0.12), "Risk strata and\nsensitivity analyses", LIGHT_ORANGE, fontsize=8.6, weight="bold")
    arrow(ax, (0.30, 0.74), (0.43, 0.74))
    arrow(ax, (0.65, 0.75), (0.72, 0.75))
    arrow(ax, (0.54, 0.68), (0.54, 0.52))
    arrow(ax, (0.83, 0.68), (0.83, 0.52))
    arrow(ax, (0.54, 0.40), (0.62, 0.29))
    arrow(ax, (0.83, 0.40), (0.76, 0.29))
    save_all(fig, "figure_oai_mrkr_sci_2_modeling_framework", wspace=False)


def fig3_staged_oai():
    df = pd.read_csv(TABLES / "oai_docx_plan_model_comparison.csv")
    labels = ["A\nBasic", "B\nSymptoms", "C\nSymptoms+\nImaging", "D\nDynamic\nClinical", "E\nDynamic\nClinical-\nImaging"]
    x = np.arange(len(labels))
    fig, axes = plt.subplots(1, 3, figsize=(12.2, 4.2))
    axes[0].plot(x, df["c_index"], marker="o", color=BLUE, label="Apparent")
    axes[0].plot(x, df["optimism_corrected_c_index"], marker="o", color=ORANGE, label="Bootstrap-corrected")
    axes[0].set_ylabel("C-index")
    axes[0].legend(frameon=False, fontsize=8)
    axes[1].plot(x, df["auc_60m"], marker="o", color=BLUE)
    axes[1].set_ylabel("Time-dependent AUC at 60 months")
    axes[2].plot(x, df["brier_60m"], marker="o", color=RED)
    axes[2].invert_yaxis()
    axes[2].set_ylabel("Brier score at 60 months\n(lower is better)")
    titles = ["A  Overall discrimination", "B  Fixed-horizon discrimination", "C  Prediction error"]
    for ax, title in zip(axes, titles):
        ax.set_title(title, loc="left")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=7.8)
        ax.grid(axis="y", alpha=0.22)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Staged OAI model performance in the 24-month landmark analysis", color=NAVY)
    save_all(fig, "figure_oai_mrkr_sci_3_oai_staged_performance")


def fig4_oai_calibration_dca():
    cal = pd.read_csv(TABLES / "oai_docx_plan_calibration_60m.csv")
    dca = pd.read_csv(TABLES / "oai_docx_plan_decision_curve_60m.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8))
    lim = max(cal["mean_predicted_risk"].max(), cal["observed_km_risk"].max()) * 1.1
    axes[0].plot([0, lim], [0, lim], "--", color=GRAY, lw=1)
    axes[0].plot(cal["mean_predicted_risk"], cal["observed_km_risk"], marker="o", color=BLUE, lw=1.8)
    axes[0].set_xlim(0, lim)
    axes[0].set_ylim(0, lim)
    axes[0].set_xlabel("Mean predicted 60-month risk")
    axes[0].set_ylabel("Observed KM 60-month risk")
    axes[0].set_title("A  Calibration", loc="left")
    axes[1].plot(dca["threshold"], dca["net_benefit_model"], color=BLUE, lw=2.2, label="Model E")
    axes[1].plot(dca["threshold"], dca["net_benefit_treat_all"], color=RED, lw=1.6, label="Treat all")
    axes[1].plot(dca["threshold"], dca["net_benefit_treat_none"], color=GRAY, lw=1.6, label="Treat none")
    axes[1].set_xlabel("Threshold probability")
    axes[1].set_ylabel("Net benefit")
    axes[1].set_title("B  Decision curve", loc="left")
    axes[1].legend(frameon=False)
    for ax in axes:
        ax.grid(alpha=0.22)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("OAI Model E calibration and clinical utility at 60 months", color=NAVY)
    save_all(fig, "figure_oai_mrkr_sci_4_oai_model_e_calibration_dca")


def fig5_time_event():
    time = pd.read_csv(TABLES / "oai_mrkr_plan_time_structure_table.csv")
    rows = []
    for h in [12, 24, 36, 60]:
        for _, r in time.iterrows():
            rows.append({"cohort": r["cohort"], "horizon": h, "events": r[f"events_{h}m"], "at_risk": r[f"at_risk_{h}m"]})
    d = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(8.8, 5.0))
    x = np.arange(4)
    width = 0.34
    for i, cohort in enumerate(["OAI", "MRKR"]):
        sub = d[d["cohort"] == cohort]
        off = (i - 0.5) * width
        ax.bar(x + off, sub["events"], width=width, label=cohort, color=BLUE if cohort == "OAI" else ORANGE)
        for xx, ev, ar in zip(x + off, sub["events"], sub["at_risk"]):
            ax.text(xx, ev + 25, f"risk {int(ar)}", ha="center", va="bottom", fontsize=7.6, rotation=0)
    ax.set_xticks(x)
    ax.set_xticklabels(["12", "24", "36", "60"])
    ax.set_xlabel("Months after landmark")
    ax.set_ylabel("Events by horizon")
    ax.set_title("OAI and MRKR time-event structure", color=NAVY)
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.22)
    save_all(fig, "figure_oai_mrkr_sci_5_time_event_structure")


def fig6_mrkr_calibration():
    cal = pd.read_csv(TABLES / "oai_mrkr_plan_calibration_24m.csv")
    cal = cal[cal["model"].isin(["MRKR original OAI baseline", "MRKR slope+baseline recalibrated"])]
    fig, ax = plt.subplots(figsize=(6.3, 5.6))
    ax.plot([0, 0.7], [0, 0.7], "--", color=GRAY, lw=1)
    for model, color, label in [
        ("MRKR original OAI baseline", RED, "Original OAI-derived"),
        ("MRKR slope+baseline recalibrated", TEAL, "Slope+baseline recalibrated"),
    ]:
        s = cal[cal["model"] == model]
        ax.plot(s["mean_predicted_risk"], s["observed_km_risk"], marker="o", lw=1.8, color=color, label=label)
    ax.set_xlabel("Mean predicted 24-month risk")
    ax.set_ylabel("Observed KM 24-month risk")
    ax.set_title("MRKR calibration before and after recalibration", color=NAVY)
    ax.legend(frameon=False)
    ax.grid(alpha=0.22)
    ax.spines[["top", "right"]].set_visible(False)
    save_all(fig, "figure_oai_mrkr_sci_6_mrkr_calibration_recalibration")


def fig7_risk_strata():
    strata = pd.read_csv(TABLES / "oai_mrkr_plan_mrkr_risk_strata_24m.csv")
    groups = ["<10%", "10-25%", "25-50%", ">50%"]
    strata["risk_group_recalibrated_24m"] = pd.Categorical(strata["risk_group_recalibrated_24m"], groups, ordered=True)
    strata = strata.sort_values("risk_group_recalibrated_24m")
    x = np.arange(len(strata))
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ax.bar(x - 0.18, strata["mean_recalibrated_predicted_24m_risk"], width=0.36, color=TEAL, label="Predicted")
    ax.bar(x + 0.18, strata["observed_km_24m_risk"], width=0.36, color=BLUE, label="Observed")
    for i, r in enumerate(strata.itertuples()):
        y = max(r.mean_recalibrated_predicted_24m_risk, r.observed_km_24m_risk) + 0.04
        ax.text(i, y, f"n={r.n_knees}\ne={r.events_by_24m}", ha="center", va="bottom", fontsize=7.6)
    ax.set_ylim(0, 0.65)
    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    ax.set_ylabel("24-month risk")
    ax.set_xlabel("MRKR recalibrated 24-month risk stratum")
    ax.set_title("MRKR recalibrated risk strata", color=NAVY)
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.22)
    ax.spines[["top", "right"]].set_visible(False)
    save_all(fig, "figure_oai_mrkr_sci_7_mrkr_risk_strata")


def fig8_sensitivity():
    strict = pd.read_csv(TABLES / "oai_mrkr_plan_mrkr_strict_sensitivity_24m.csv")
    outcome = pd.read_csv(TABLES / "oai_mrkr_plan_mrkr_outcome_sensitivity_24m.csv")
    strict_labels = ["All", ">3m", ">6m", ">12m"]
    outcome_labels = ["Hardware", "CPT", "Combined"]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.8))
    axes[0].plot(strict_labels, strict["auc_24m"], marker="o", color=BLUE, lw=1.8)
    for x, y, n, e in zip(strict_labels, strict["auc_24m"], strict["n_knees"], strict["events_by_24m"]):
        axes[0].text(x, y + 0.01, f"n={int(n)}\ne={int(e)}", ha="center", fontsize=7.2)
    axes[0].set_title("A  Early-event exclusions", loc="left")
    axes[0].set_ylabel("24-month AUC")
    axes[0].set_ylim(0.58, 0.75)
    axes[1].plot(outcome_labels, outcome["auc_24m"], marker="o", color=ORANGE, lw=1.8)
    for x, y, n, e in zip(outcome_labels, outcome["auc_24m"], outcome["n_knees"], outcome["events_by_24m"]):
        axes[1].text(x, y + 0.01, f"n={int(n)}\ne={int(e)}", ha="center", fontsize=7.2)
    axes[1].set_title("B  Outcome definitions", loc="left")
    axes[1].set_ylim(0.58, 0.75)
    for ax in axes:
        ax.axhline(0.5, color=GRAY, ls="--", lw=1)
        ax.grid(axis="y", alpha=0.22)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("MRKR sensitivity analyses", color=NAVY)
    save_all(fig, "figure_oai_mrkr_sci_8_mrkr_sensitivity")


def supp1_nomogram():
    coef = pd.read_csv(TABLES / "oai_docx_plan_cox_coefficients.csv")
    coef = coef[coef["model"] == "E_dynamic_clinical_imaging"].copy()
    keep = [
        ("kl_0", "Baseline KL grade"),
        ("jsn_medial_change", "Medial JSN change"),
        ("jsn_lateral_change", "Lateral JSN change"),
        ("pain_change", "WOMAC pain change"),
        ("stiffness_0", "Baseline stiffness"),
        ("pain_0", "Baseline pain"),
        ("bmi", "BMI"),
        ("female", "Female sex"),
    ]
    coef = coef.set_index("term").loc[[k for k, _ in keep]].reset_index()
    coef["label"] = [lbl for _, lbl in keep]
    coef["beta"] = np.log(coef["hazard_ratio"])
    coef["points"] = 100 * np.abs(coef["beta"]) / np.abs(coef["beta"]).max()
    fig, ax = plt.subplots(figsize=(10, 5.8))
    y = np.arange(len(coef))[::-1]
    ax.hlines(y, 0, coef["points"], color="#B6C2CF", lw=5)
    colors = [TEAL if b > 0 else ORANGE for b in coef["beta"]]
    ax.scatter(coef["points"], y, s=90, color=colors, zorder=3)
    for yy, p, hr in zip(y, coef["points"], coef["hazard_ratio"]):
        ax.text(p + 2.5, yy, f"{p:.0f} pts | HR {hr:.2f}", va="center", fontsize=8.5)
    ax.set_yticks(y)
    ax.set_yticklabels(coef["label"])
    ax.set_xlim(0, 118)
    ax.set_xlabel("Relative nomogram points scaled to strongest Model E effect")
    ax.set_title("Supplementary Figure S1. Research nomogram-style visualization of OAI Model E", color=NAVY)
    ax.grid(axis="x", alpha=0.22)
    ax.spines[["top", "right", "left"]].set_visible(False)
    save_all(fig, "supplementary_figure_s1_model_e_nomogram")


def supp2_calculator():
    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.04, 0.94, "Model F-core research-use calculator", fontsize=15, fontweight="bold", color=NAVY)
    ax.text(0.04, 0.89, "Common-variable OAI-derived transport model with MRKR recalibration", fontsize=10, color=GRAY)
    box(ax, (0.04, 0.16), (0.43, 0.68), "", "#F7F9FB", ec="#D8E2EC")
    inputs = [
        ("Age", "64 years"),
        ("Sex", "Female"),
        ("Knee side", "Right"),
        ("Landmark pain", "6 / 10"),
        ("Baseline KL grade", "3"),
        ("KL worsening", "Yes"),
    ]
    y = 0.76
    for lab, val in inputs:
        ax.text(0.08, y, lab, fontsize=9.5, color=NAVY, fontweight="bold")
        box(ax, (0.26, y - 0.025), (0.16, 0.045), val, "white", ec="#CBD5E1", fontsize=8.5)
        y -= 0.09
    box(ax, (0.54, 0.58), (0.38, 0.20), "Original OAI-derived risk\n24 months: 5.1%\n60 months: 14.3%", LIGHT_BLUE, fontsize=12, weight="bold")
    box(ax, (0.54, 0.31), (0.38, 0.20), "MRKR recalibrated risk\n24 months: 31.6%\nRisk stratum: 25-50%", LIGHT_GREEN, fontsize=12, weight="bold")
    box(ax, (0.54, 0.13), (0.38, 0.10), "Research-use only. Requires local validation and recalibration before clinical use.", LIGHT_RED, ec=RED, fontsize=9.2, weight="bold")
    arrow(ax, (0.47, 0.50), (0.54, 0.68))
    arrow(ax, (0.47, 0.42), (0.54, 0.40))
    save_all(fig, "supplementary_figure_s2_model_f_calculator_mockup", wspace=False)


def supp3_subgroups():
    df = pd.read_csv(TABLES / "oai_mrkr_highimpact_mrkr_subgroup_performance_24m.csv")
    df = df[df["subgroup"] != "All MRKR core"].copy()
    df = df.sort_values("auc_24m")
    fig, ax = plt.subplots(figsize=(8.5, 6.8))
    y = np.arange(len(df))
    ax.scatter(df["auc_24m"], y, s=np.sqrt(df["n_knees"]) * 3.0, color=BLUE, alpha=0.78)
    for yy, auc, n, e in zip(y, df["auc_24m"], df["n_knees"], df["events_by_24m"]):
        ax.text(auc + 0.006, yy, f"n={int(n)}, e={int(e)}", va="center", fontsize=7)
    ax.axvline(0.5, color=GRAY, ls="--", lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels(df["subgroup"], fontsize=8)
    ax.set_xlim(0.52, 0.78)
    ax.set_xlabel("24-month AUC")
    ax.set_title("Supplementary Figure S3. MRKR subgroup performance at 24 months", color=NAVY)
    ax.grid(axis="x", alpha=0.22)
    ax.spines[["top", "right", "left"]].set_visible(False)
    save_all(fig, "supplementary_figure_s3_mrkr_subgroups")


def main():
    fig1_cohort_flow()
    fig2_framework()
    fig3_staged_oai()
    fig4_oai_calibration_dca()
    fig5_time_event()
    fig6_mrkr_calibration()
    fig7_risk_strata()
    fig8_sensitivity()
    supp1_nomogram()
    supp2_calculator()
    supp3_subgroups()
    print("Generated SCI high-resolution PNG/PDF/SVG figures.")


if __name__ == "__main__":
    main()
