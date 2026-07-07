# 数据清单

## 目录结构

```text
raw/        原始下载数据，按队列保存
metadata/   文件索引、变量索引、数据字典
derived/    可直接分析的派生 CSV
results/    表格、图、模型对象
scripts/    可复现处理脚本
docs/       项目说明、申请文字和原始方案
```

## OAI

状态：已下载、已索引、已处理。

保留的原始包：

- `raw/OAI/General_ASCII`
- `raw/OAI/AllClinical_ASCII`
- `raw/OAI/MIF_ASCII`
- `raw/OAI/X-Ray Image Assessments_ASCII`
- `raw/OAI/X-Ray MetaAnalysis_ASCII`
- `raw/OAI/Outcomes_ASCII`

主要派生文件：

- `derived/OAI/oai_knee_level_first_pass.csv`
- `derived/OAI/oai_pain_trajectory_long.csv`
- `derived/OAI/oai_24m_landmark_dataset.csv`
- `derived/baseline/oai_patient_baseline.csv`

主要结果文件：

- `results/tables/oai_24m_landmark_summary.csv`
- `results/tables/cox_oai_24m_model_metrics.csv`
- `results/tables/cox_oai_24m_coefficients.csv`
- `results/figures/oai_24m_tka_km_by_pain_trajectory.png`
- `results/models/cox_oai_24m_baseline.rds`
- `results/models/cox_oai_24m_dynamic.rds`

## CHECK

状态：已下载、已索引、已处理。

来源：

- CHECK T0-T5: DOI `10.17026/DANS-XEX-HZWW`
- CHECK T0/T6/T7/T8: DOI `10.17026/DANS-ZC8-G4CW`

保留的原始数据：

- `raw/CHECK/CHECK_T0_DANS_ENG_20161128.tab`
- `raw/CHECK/CHECK_T1_DANS_ENG_20151207.DTA` 至 `CHECK_T8_DANS_ENG_20151207.DTA`
- 对应 `.sav` 文件，用于变量标签和源数据追溯
- `raw/CHECK/Rontgen_opT10_20191118.dta`
- CHECK 文档 PDF 和 radiographic scoring `.tab`

已删除：

- CHECK 的 `.POR/.por` portable 文件。它们与 `.DTA/.sav/.tab` 内容重复，不再作为项目依赖。

主要派生文件：

- `derived/CHECK/check_knee_level_first_pass.csv`
- `derived/CHECK/check_pain_trajectory_long.csv`
- `derived/baseline/check_patient_baseline.csv`

## 患者层面基线表

状态：已生成。

文件：

- `derived/baseline/oai_patient_baseline.csv`：OAI 患者一行，保留左右膝基线字段。
- `derived/baseline/check_patient_baseline.csv`：CHECK 患者一行，保留左右膝基线字段。
- `derived/baseline/combined_patient_baseline.csv`：完整合并表，保留所有队列特异字段。
- `derived/baseline/combined_patient_baseline_common.csv`：统一变量名合并表，更适合后续建模/描述统计。
- `results/tables/patient_baseline_table1.csv`：论文 Table 1 初稿。
- `metadata/patient_baseline_dictionary.csv`：患者基线字段说明。

当前患者层面样本量：

- OAI：4,796 人。
- CHECK：1,002 人。
- 合并：5,798 人。

主要结果文件：

- `results/tables/check_dataset_summary.csv`
- `results/tables/check_knee_dataset_by_side.csv`
- `results/tables/check_pain_trajectory_summary.csv`

CHECK 当前摘要：

- 1,002 名受试者。
- 2,004 膝。
- 基线 KL 可用 1,923 膝。
- TKA through T8 事件 33 个。
- KL T0-T5 进展 958 膝。
- KL T0-T8 进展 1,135 膝。

## MOST/AgingResearchBiobank

状态：暂停。

原因：当前未取得可分析数据，申请流程需要进一步授权/签字，短期内会拖慢项目进展。

已处理方式：

- 删除 MOST 大体积说明 PDF 和空 `raw/MOST`、`derived/MOST`、`metadata/MOST` 目录。
- 保留 `docs/agingresearchbiobank_request_text.md` 作为申请文字记录。
- 原始项目方案保留在 `docs/original_plan/OAI_MOST_膝OA纵向预测项目方案.docx`。

## 是否还需要下载数据

当前不需要继续下载才能推进项目。OAI + CHECK 已经足够完成一个训练队列加外部/补充验证队列的预测模型项目。

跨队列验证优先使用 `metadata/oai_check_variable_mapping.csv` 中列出的共有变量。映射状态标记为 `approximate` 的变量需要先核对量表方向、编码和评分定义，不能直接当作完全相同变量解释。

后续只有在改变研究方向时才建议追加数据：

- 如果做影像深度学习，需要下载膝关节 X-ray 图像数据，但文件会很大，且需要重新设计模型。
- 如果坚持 TKA 外部验证，需要寻找事件数更多且权限更容易的数据源。
- 如果只做临床表格预测，当前 OAI + CHECK 已够进入建模和论文方法设计。
