#!/usr/bin/env python3
"""Generate reviewer-style figures for the OAI landmark manuscript."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "results" / "tables"
FIGS = ROOT / "results" / "figures"
FIGS.mkdir(parents=True, exist_ok=True)


def clean_model(name: str) -> str:
    return {
        "A_basic": "A\nBasic",
        "B_baseline_symptoms": "B\nBaseline\nsymptoms",
        "C_baseline_symptoms_imaging": "C\nBaseline\nclinical-\nradiographic",
        "D_dynamic_clinical": "D\nDynamic\nclinical",
        "E_dynamic_clinical_imaging": "E\nDynamic\nclinical-\nradiographic",
    }.get(name, name)


def figure1():
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.8), gridspec_kw={"width_ratios": [1, 1.25]})
    ax = axes[0]
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    steps = [
        "OAI knee-level dataset\n9,592 knees",
        "Eligible at 24-month landmark\n8,314 knees",
        "Excluded for incomplete\nbaseline/24-month predictors\n5,248 knees",
        "Common complete-case set\n3,066 knees / 1,640 participants\n559 post-landmark KR/TKA events",
        "Model A-E development\ninternal validation, calibration,\nDCA, risk stratification",
    ]
    y = 0.92
    for i, text in enumerate(steps):
        box = FancyBboxPatch((0.08, y - 0.105), 0.84, 0.09, boxstyle="round,pad=0.015",
                             linewidth=1.1, edgecolor="#1F4D78", facecolor="#F2F6FA")
        ax.add_patch(box)
        ax.text(0.5, y - 0.06, text, ha="center", va="center", fontsize=9)
        if i < len(steps) - 1:
            ax.annotate("", xy=(0.5, y - 0.17), xytext=(0.5, y - 0.13),
                        arrowprops=dict(arrowstyle="-|>", color="#1F4D78", lw=1.2))
        y -= 0.18
    ax.text(0.02, 0.98, "A  Study flow", fontsize=12, weight="bold", color="#0B2545", va="top")

    ax = axes[1]
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.02, 0.98, "B  24-month landmark design", fontsize=12, weight="bold", color="#0B2545", va="top")
    y0 = 0.58
    xs = [0.08, 0.32, 0.54, 0.88]
    labels = ["Baseline", "12 months", "24-month\nlandmark", "Follow-up"]
    ax.plot([xs[0], xs[-1]], [y0, y0], color="#1F4D78", lw=2)
    for x, lab in zip(xs, labels):
        ax.plot([x, x], [y0 - 0.04, y0 + 0.04], color="#1F4D78", lw=2)
        ax.text(x, y0 + 0.08, lab, ha="center", va="bottom", fontsize=9, weight="bold")
    ax.text(0.08, y0 - 0.16, "Baseline symptoms\nKL/JSN\nage, sex, BMI", ha="center", va="top", fontsize=8)
    ax.text(0.32, y0 - 0.16, "Interim symptom\ntrajectory", ha="center", va="top", fontsize=8)
    ax.text(0.54, y0 - 0.16, "Build dynamic predictors\n0-24m symptom and\nstructure changes", ha="center", va="top", fontsize=8)
    ax.text(0.88, y0 - 0.16, "Predict target-knee\nKR/TKA at 24, 60,\nand 96 months", ha="center", va="top", fontsize=8)
    callout = FancyBboxPatch((0.21, 0.78), 0.50, 0.09, boxstyle="round,pad=0.015",
                             linewidth=1.0, edgecolor="#9B1C1C", facecolor="#FFF5F5")
    ax.add_patch(callout)
    ax.text(0.46, 0.825, "Knees with KR/TKA before or at\n24-month landmark were excluded",
            ha="center", va="center", fontsize=8, color="#6B0F0F")
    ax.annotate("", xy=(0.54, y0 + 0.045), xytext=(0.49, 0.78),
                arrowprops=dict(arrowstyle="-|>", color="#9B1C1C", lw=1.0))
    fig.tight_layout()
    fig.savefig(FIGS / "figure1_study_flow_landmark.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def figure2():
    df = pd.read_csv(TABLES / "oai_docx_plan_model_comparison.csv")
    labels = [clean_model(x) for x in df["model"]]
    x = range(len(df))
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    axes[0].plot(x, df["c_index"], marker="o", label="Apparent")
    axes[0].plot(x, df["optimism_corrected_c_index"], marker="o", label="Bootstrap-corrected")
    axes[0].set_ylabel("C-index")
    axes[0].set_ylim(0.48, 0.82)
    axes[0].legend(frameon=False, fontsize=8)
    axes[1].plot(x, df["auc_60m"], marker="o", color="#1F77B4")
    axes[1].set_ylabel("Time-dependent AUC at 60 months")
    axes[1].set_ylim(0.48, 0.84)
    axes[2].plot(x, df["brier_60m"], marker="o", color="#D62728")
    axes[2].invert_yaxis()
    axes[2].set_ylabel("Brier score at 60 months\n(lower is better)")
    for ax in axes:
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, fontsize=8)
        ax.grid(axis="y", alpha=0.25)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Incremental performance across sequential landmark models", fontsize=12, weight="bold")
    fig.tight_layout()
    fig.savefig(FIGS / "figure2_model_performance.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def figure3():
    cal = pd.read_csv(TABLES / "oai_docx_plan_calibration_60m.csv")
    dca = pd.read_csv(TABLES / "oai_docx_plan_decision_curve_60m.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    ax = axes[0]
    lim = max(cal["mean_predicted_risk"].max(), cal["observed_km_risk"].max()) * 1.12
    ax.plot([0, lim], [0, lim], "--", color="grey", lw=1)
    ax.plot(cal["mean_predicted_risk"], cal["observed_km_risk"], marker="o", color="#1F77B4")
    for _, r in cal.iterrows():
        ax.text(r["mean_predicted_risk"], r["observed_km_risk"] + 0.012, str(int(r["n"])),
                fontsize=7, ha="center")
    ax.set_xlabel("Mean predicted 5-year KR/TKA risk")
    ax.set_ylabel("Observed 5-year KR/TKA risk")
    ax.set_title("A  Calibration by risk decile")
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
    ax.spines[["top", "right"]].set_visible(False)

    ax = axes[1]
    ax.plot(dca["threshold"], dca["net_benefit_model"], label="Model E", color="#1F77B4", lw=2)
    ax.plot(dca["threshold"], dca["net_benefit_treat_all"], label="Treat all", color="#D62728", lw=1.8)
    ax.plot(dca["threshold"], dca["net_benefit_treat_none"], label="Treat none", color="grey", lw=1.8)
    for pt in [0.05, 0.10, 0.20]:
        ax.axvline(pt, color="grey", lw=0.7, alpha=0.35)
    ax.set_xlabel("Risk threshold")
    ax.set_ylabel("Net benefit")
    ax.set_title("B  Decision curve")
    ax.set_ylim(-0.02, 0.105)
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGS / "figure3_calibration_dca.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def figure5():
    summ = pd.read_csv(TABLES / "oai_docx_plan_symptom_structure_group_summary.csv")
    hr = pd.read_csv(TABLES / "oai_docx_plan_symptom_structure_group_hr.csv")
    order = ["Low pain / low structure", "High pain / low structure", "Low pain / high structure", "High pain / high structure"]
    summ["symptom_structure_group"] = pd.Categorical(summ["symptom_structure_group"], order, ordered=True)
    summ = summ.sort_values("symptom_structure_group")
    hr = hr[hr["term"].str.contains("symptom_structure_group", regex=False)].copy()
    hr["group"] = hr["term"].str.replace("symptom_structure_group", "", regex=False)
    hr["group"] = pd.Categorical(hr["group"], order[1:], ordered=True)
    hr = hr.sort_values("group")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), gridspec_kw={"width_ratios": [1.15, 1]})
    ax = axes[0]
    colors = ["#8EC0E4", "#F9C74F", "#F9844A", "#C1121F"]
    ax.bar(range(len(summ)), summ["event.mean"] * 100, color=colors)
    ax.set_xticks(range(len(summ)))
    ax.set_xticklabels(["Low pain\nlow structure", "High pain\nlow structure", "Low pain\nhigh structure", "High pain\nhigh structure"], fontsize=8)
    ax.set_ylabel("Observed KR/TKA event rate (%)")
    ax.set_title("A  Event gradient")
    ax.spines[["top", "right"]].set_visible(False)
    for i, r in enumerate(summ.itertuples()):
        ax.text(i, r._3 * 100 + 1, f"n={int(r._2)}", ha="center", fontsize=7)

    ax = axes[1]
    y = range(len(hr))
    ax.errorbar(hr["hazard_ratio"], list(y),
                xerr=[hr["hazard_ratio"] - hr["ci_lower_95"], hr["ci_upper_95"] - hr["hazard_ratio"]],
                fmt="o", color="#1F4D78", ecolor="#1F4D78", capsize=3)
    ax.axvline(1, color="grey", ls="--")
    ax.set_yticks(list(y))
    ax.set_yticklabels(["High pain\nlow structure", "Low pain\nhigh structure", "High pain\nhigh structure"], fontsize=8)
    ax.set_xlabel("Hazard ratio vs low pain/low structure")
    ax.set_title("B  Adjusted KR/TKA risk")
    ax.set_xscale("log")
    ax.set_xlim(1, 12)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGS / "figure5_symptom_structure_discordance.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    figure1()
    figure2()
    figure3()
    figure5()
    print("Generated reviewer figures")


if __name__ == "__main__":
    main()
