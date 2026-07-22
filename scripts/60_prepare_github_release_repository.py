from __future__ import annotations

import csv
import shutil
from pathlib import Path

from docx import Document


ROOT = Path(
    "/Users/hehang/Downloads/时间序列预测模型/膝关节炎/"
    "stage_specific_progression_framework/complete_project_analysis"
)
MANUSCRIPT_ROOT = ROOT / "three_stage_bridge_transport_manuscript"
RELEASE_ROOT = ROOT / "github_release"
REPO_DIR = ROOT.parent / "public_release/oai-mrkr-model-f-core-risk-calculator"

MAIN_DOCX = (
    MANUSCRIPT_ROOT
    / "JOSR_supplement_figures_then_tables_S1_S14_T1_T25_20260722/manuscript/"
    "three_stage_bridge_transport_manuscript_JOSR_clinical_translation_preserve_images_unchanged.docx"
)
SUPP_DOCX = (
    MANUSCRIPT_ROOT
    / "JOSR_supplement_figures_then_tables_S1_S14_T1_T25_20260722/manuscript/"
    "three_stage_bridge_transport_supplementary_materials_FiguresS1-S14_then_TablesS1-S24_S14_screenshot.docx"
)
CALC_DIR = MANUSCRIPT_ROOT / "enhanced_research_calculator_20260722"
CALC_HTML = CALC_DIR / "knee_oa_stage_specific_risk_calculator.html"
CALC_SCREENSHOTS = CALC_DIR / "screenshots"

MAIN_FIG_SRC = (
    MANUSCRIPT_ROOT
    / "main_supplement_5fig3table_revision_from_bridge_sample_fixed_base_20260722_v2/main_figures"
)
SUPP_FIG_SRC = (
    MANUSCRIPT_ROOT
    / "main_supplement_5fig3table_revision_from_bridge_sample_fixed_base_20260722_v2/supplementary_figures"
)
ADDED_FIG_SRC = MANUSCRIPT_ROOT / "preserve_existing_images_latest_framework_additions_20260722/added_figures"
SCRIPT_SRC = ROOT / "scripts"


MAIN_FIGURES = {
    "figure1_stage_specific_framework.png": MAIN_FIG_SRC / "figure1_from_latest_initial_draft_unchanged.png",
    "figure2_check_early_structural_transition.pdf": MAIN_FIG_SRC / "figure2_check_early_structural_transition_primary_model.pdf",
    "figure2_check_early_structural_transition.png": MAIN_FIG_SRC / "figure2_check_early_structural_transition_primary_model.png",
    "figure3_radiographic_bridge_arthroplasty_gradient.pdf": MAIN_FIG_SRC / "figure3_check_oai_radiographic_bridge_evidence.pdf",
    "figure3_radiographic_bridge_arthroplasty_gradient.png": MAIN_FIG_SRC / "figure3_check_oai_radiographic_bridge_evidence.png",
    "figure4_oai_arthroplasty_model_stratification.pdf": MAIN_FIG_SRC / "figure4_oai_incremental_value_clinical_stratification.pdf",
    "figure4_oai_arthroplasty_model_stratification.png": MAIN_FIG_SRC / "figure4_oai_incremental_value_clinical_stratification.png",
    "figure5_mrkr_transport_recalibration_sensitivity.pdf": MAIN_FIG_SRC / "figure5_mrkr_transport_recalibration_sensitivity.pdf",
    "figure5_mrkr_transport_recalibration_sensitivity.png": MAIN_FIG_SRC / "figure5_mrkr_transport_recalibration_sensitivity.png",
}

SUPPLEMENTARY_FIGURES = {
    "figure_s1_three_cohort_inclusion_flow.png": SUPP_FIG_SRC / "figure_s1_three_cohort_inclusion_flow_latest.png",
    "figure_s2_check_kl_transition_matrices.png": SUPP_FIG_SRC / "figure_s2_check_kl_transition_matrices.png",
    "figure_s3_check_calibration.png": SUPP_FIG_SRC / "figure_s3_check_calibration.png",
    "figure_s4_check_candidate_model_performance.png": SUPP_FIG_SRC / "figure_s4_check_candidate_model_comparison.png",
    "figure_s5_check_96m_radiograph_availability_bias.png": ADDED_FIG_SRC / "figure_s16_check_96m_radiograph_missingness_smd.png",
    "figure_s5_check_96m_radiograph_availability_bias.pdf": ADDED_FIG_SRC / "figure_s16_check_96m_radiograph_missingness_smd.pdf",
    "figure_s6_oai_kl_timepoint_sensitivity.png": ADDED_FIG_SRC / "figure_s18_oai_kl_timepoint_gradient_sensitivity.png",
    "figure_s6_oai_kl_timepoint_sensitivity.pdf": ADDED_FIG_SRC / "figure_s18_oai_kl_timepoint_gradient_sensitivity.pdf",
    "figure_s7_oai_predictor_domain_incremental_value.png": ADDED_FIG_SRC / "figure_s15_oai_predictor_domain_incremental_value.png",
    "figure_s7_oai_predictor_domain_incremental_value.pdf": ADDED_FIG_SRC / "figure_s15_oai_predictor_domain_incremental_value.pdf",
    "figure_s8_oai_coefficient_stability.png": ADDED_FIG_SRC / "figure_s19_oai_final_model_coefficient_stability.png",
    "figure_s8_oai_coefficient_stability.pdf": ADDED_FIG_SRC / "figure_s19_oai_final_model_coefficient_stability.pdf",
    "figure_s9_secondary_rf_shap_interpretation.png": ADDED_FIG_SRC / "figure_s22_secondary_rf_shap_interpretability.png",
    "figure_s9_secondary_rf_shap_interpretation.pdf": ADDED_FIG_SRC / "figure_s22_secondary_rf_shap_interpretability.pdf",
    "figure_s10_mrkr_internal_benchmark.png": SUPP_FIG_SRC / "figure_s8_mrkr_internal_target_benchmark.png",
    "figure_s11_mrkr_oof_recalibration_workflow.png": ADDED_FIG_SRC / "figure_s21_mrkr_oof_recalibration_workflow.png",
    "figure_s11_mrkr_oof_recalibration_workflow.pdf": ADDED_FIG_SRC / "figure_s21_mrkr_oof_recalibration_workflow.pdf",
    "figure_s12_mrkr_early_event_exclusion_sensitivity.png": ADDED_FIG_SRC / "figure_s17_mrkr_early_event_exclusion_sensitivity.png",
    "figure_s12_mrkr_early_event_exclusion_sensitivity.pdf": ADDED_FIG_SRC / "figure_s17_mrkr_early_event_exclusion_sensitivity.pdf",
    "figure_s13_mrkr_decision_curve.png": SUPP_FIG_SRC / "figure_s10_mrkr_decision_curve.png",
    "figure_s14_web_calculator_composite.png": CALC_SCREENSHOTS / "figure_s14_enhanced_web_calculator_composite.png",
}

SCRIPTS = [
    "51_generate_three_stage_bridge_transport_assets.py",
    "53_clinical_translation_upgrade_analyses.py",
    "54_generate_5fig3table_revision.py",
    "58_reorder_supplement_interleaved_s1_s14_t1_t25.py",
    "59_supplement_figures_then_tables_s14_screenshot.py",
    "60_prepare_github_release_repository.py",
]


def ensure_empty_repo_dir() -> None:
    if REPO_DIR.exists():
        for child in REPO_DIR.iterdir():
            if child.name == ".git":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    REPO_DIR.mkdir(parents=True, exist_ok=True)


def copy_files(mapping: dict[str, Path], target_dir: Path) -> list[str]:
    target_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for name, src in mapping.items():
        if not src.exists():
            raise FileNotFoundError(src)
        dst = target_dir / name
        shutil.copy2(src, dst)
        copied.append(str(dst.relative_to(REPO_DIR)))
    return copied


def table_to_rows(table) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.rows:
        rows.append([cell.text.replace("\n", " ").strip() for cell in row.cells])
    return rows


def write_csv(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerows(rows)


def extract_tables(docx_path: Path, target_dir: Path, prefix: str) -> list[str]:
    doc = Document(docx_path)
    out: list[str] = []
    for idx, table in enumerate(doc.tables, start=1):
        rows = table_to_rows(table)
        path = target_dir / f"{prefix}{idx:02d}.csv"
        write_csv(path, rows)
        out.append(str(path.relative_to(REPO_DIR)))
    return out


def write_text_files() -> None:
    (REPO_DIR / ".gitignore").write_text(
        "\n".join(
            [
                ".DS_Store",
                "__pycache__/",
                "*.pyc",
                "*.docx",
                "*.doc",
                "*.wps",
                "*.RData",
                "*.rds",
                "*.h5ad",
                "raw_data/",
                "data/raw/",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (REPO_DIR / ".nojekyll").write_text("", encoding="utf-8")
    (REPO_DIR / "README.md").write_text(
        """# Knee OA Stage-Specific Risk Calculator

This repository accompanies the manuscript:

**Stage-specific prediction of knee osteoarthritis progression and arthroplasty risk with real-world recalibration**

It contains only manuscript figure/table assets, summary CSV tables, reproducibility scripts, and a static research-use web calculator. Raw CHECK, OAI, or MRKR source data are not included.

## Online calculator

The static calculator is served from `index.html` and implements two stage-matched modules:

- **Early Radiographic Progression**: 24-month risk of incident KL >=2 in symptomatic baseline KL0/1 knees.
- **Knee Arthroplasty Risk**: 60-month target-knee TKA/KR risk after the OAI 24-month landmark.

MRKR is represented as a model-transport and target-cohort recalibration page rather than as a patient-facing model-entry point.

## Repository structure

```text
index.html                  Static web calculator for GitHub Pages
figures/main/               Main manuscript figures
figures/supplementary/      Supplementary Figures S1-S14
tables/main/                Main manuscript tables extracted as CSV
tables/supplementary/       Supplementary Tables S1-S24 extracted as CSV after final consistency revision
scripts/                    Figure/table/calculator preparation scripts
screenshots/                Web-calculator screenshots used for Figure S14
```

## Use and limitations

The calculator is for research communication and reproducibility. It is not validated for treatment decisions or surgical eligibility. The threshold displays are exploratory and intended for risk enrichment, follow-up planning, and research use.

## Data availability

Only aggregate figure/table outputs are provided. Original cohort-level source data must be obtained through the relevant cohort data-access mechanisms.
""",
        encoding="utf-8",
    )


def main() -> None:
    ensure_empty_repo_dir()
    write_text_files()
    shutil.copy2(CALC_HTML, REPO_DIR / "index.html")
    shutil.copytree(CALC_SCREENSHOTS, REPO_DIR / "screenshots", dirs_exist_ok=True)
    main_figs = copy_files(MAIN_FIGURES, REPO_DIR / "figures/main")
    supp_figs = copy_files(SUPPLEMENTARY_FIGURES, REPO_DIR / "figures/supplementary")
    main_tables = extract_tables(MAIN_DOCX, REPO_DIR / "tables/main", "table")
    supp_tables = extract_tables(SUPP_DOCX, REPO_DIR / "tables/supplementary", "table_s")
    script_files = copy_files({s: SCRIPT_SRC / s for s in SCRIPTS}, REPO_DIR / "scripts")
    (REPO_DIR / "MANIFEST.md").write_text(
        "\n".join(
            [
                "# Release manifest",
                "",
                "Included assets are restricted to manuscript figure/table outputs and calculator code.",
                "",
                f"- Main figures: {len(main_figs)} files",
                f"- Supplementary figures: {len(supp_figs)} files",
                f"- Main tables: {len(main_tables)} CSV files",
                f"- Supplementary tables: {len(supp_tables)} CSV files",
                f"- Scripts: {len(script_files)} files",
                "",
                "No raw cohort data, DOCX manuscript files, WPS backups, or intermediate patient-level source files are included.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(REPO_DIR)
    print(f"main_figures={len(main_figs)} supplementary_figures={len(supp_figs)}")
    print(f"main_tables={len(main_tables)} supplementary_tables={len(supp_tables)} scripts={len(script_files)}")


if __name__ == "__main__":
    main()
