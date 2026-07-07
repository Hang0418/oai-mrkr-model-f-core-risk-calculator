# 项目分析计划

## 研究目标

建立并验证一个膝骨关节炎进展预测模型，重点预测在既定 landmark 时间点之后发生膝关节置换或结构性进展的风险。当前最稳妥的主线是：

- 开发队列：OAI。
- 外部/补充验证队列：CHECK。
- 主预测时间点：OAI 24 个月 landmark。
- 主结局：landmark 后膝关节置换/TKA/KR。
- 补充结局：KL 进展、JSN 进展、WOMAC 疼痛/功能轨迹。

## 队列定位

### OAI

OAI 数据量大、TKA/KR 事件数较充足，适合作为模型开发队列。当前 24 个月 landmark 数据包含 9,592 膝；合格 landmark 样本 8,314 膝，后续事件 831 个。完整核心变量 dynamic Cox 模型样本为 7,830 膝，事件 800 个。

OAI 当前适合完成：

- Cox/随机生存森林/梯度提升生存模型开发。
- 内部验证和 bootstrap optimism correction。
- 预测性能评价：C-index、time-dependent AUC、校准、Brier score。
- 分层可视化：疼痛轨迹、KL 分层、BMI 分层、性别分层。

### CHECK

CHECK 已整理为 1,002 名受试者、2,004 膝。它有 T0-T8 临床随访、T0/T2/T5/T8/T10 影像评分，以及 T1-T8 侧别 TKA 记录。TKA 事件只有 33 个，因此不适合独立训练 TKA 模型，也不适合作为强结论的 TKA 外部验证。

CHECK 更适合：

- 验证 OAI 模型变量方向和风险分层的可迁移性。
- 验证结构性进展，如 KL 进展、内外侧 JSN 进展。
- 比较疼痛和功能轨迹。
- 作为敏感性分析或补充验证队列。

### MOST

MOST/AgingResearchBiobank 当前未取得可分析数据，且申请流程需要进一步授权/签字。该数据源暂不作为当前项目依赖，避免项目卡在权限流程上。

## 当前可用数据集

| 文件 | 用途 | 样本量 |
| --- | --- | --- |
| `derived/OAI/oai_24m_landmark_dataset.csv` | OAI 24 个月 landmark 建模 | 9,592 膝 |
| `derived/OAI/oai_knee_level_first_pass.csv` | OAI 基线膝关节层面数据 | 9,592 膝 |
| `derived/OAI/oai_pain_trajectory_long.csv` | OAI 疼痛轨迹 | 长表 |
| `derived/CHECK/check_knee_level_first_pass.csv` | CHECK 膝关节层面验证数据 | 2,004 膝 |
| `derived/CHECK/check_pain_trajectory_long.csv` | CHECK T0-T8 症状轨迹 | 18,036 行 |

## 建议建模路线

1. 定义主分析集：OAI 24 个月 landmark，排除 landmark 前已发生 KR/TKA 的膝。
2. 固定候选预测因子：年龄、性别、BMI、基线/landmark WOMAC 疼痛和功能、疼痛轨迹、KL、JSN、既往膝损伤/手术、用药。
3. 处理缺失值：先报告完整案例结果，再使用多重插补或模型内缺失处理做敏感性分析。
4. 建模：从 Cox 模型开始，随后比较 penalized Cox、random survival forest、gradient boosting survival。
5. 内部验证：bootstrap 或 repeated cross-validation，报告 optimism-corrected performance。
6. 外部/补充验证：在 CHECK 中验证可映射变量构成的简化模型，重点看校准、风险分层、KL/JSN 进展。
7. 报告规范：按 TRIPOD/TRIPOD+AI 描述数据来源、纳排标准、结局、预测因子、缺失值、验证设计和模型可用性。

## 需要谨慎说明的限制

- OAI 和 CHECK 的结局、随访间隔、变量定义并不完全一致，不能直接宣称完全外部验证等同。
- CHECK 的 TKA 事件数少，TKA 模型验证只能作为探索性结果。
- 当前 Cox dynamic 模型的比例风险假设检验有显著信号，后续需要考虑时间交互、分层 Cox 或机器学习生存模型。
- 不能把预测变量解释为因果效应，只能描述其预测贡献或关联。

