"""Generate CHECK supplementary validation tables from existing OAI-CHECK outputs."""

from pathlib import Path
import pandas as pd


ROOT = Path("/Users/hehang/Downloads/时间序列预测模型/膝关节炎")
TABLES = ROOT / "results" / "tables"


def pct(x):
    return f"{100 * float(x):.1f}%"


metrics = pd.read_csv(TABLES / "oai_24m_landmark_validation_metrics.csv")
oai = metrics[(metrics["model"] == "common_change") & (metrics["validation"] == "OAI apparent/internal")].iloc[0]
check = metrics[(metrics["model"] == "common_change") & (metrics["validation"] == "CHECK external exploratory TKA")].iloc[0]

table9 = pd.DataFrame(
    [
        ["Knees, n", int(oai["n"]), int(check["n"])],
        ["Participants, n", int(oai["participants"]), int(check["participants"])],
        ["Post-landmark TKA/KR events, n", int(oai["events_total"]), int(check["events_total"])],
        ["60-month TKA/KR events, n", int(oai["events_by_horizon"]), int(check["events_by_horizon"])],
        ["C-index", f"{float(oai['c_index']):.3f}", f"{float(check['c_index']):.3f}"],
        ["Mean predicted 60-month risk", pct(oai["mean_predicted_risk"]), pct(check["mean_predicted_risk"])],
        ["Observed 60-month risk", pct(oai["observed_km_risk"]), pct(check["observed_km_risk"])],
        ["Interpretation", "Development/internal estimate", "Exploratory validation; event-limited"],
    ],
    columns=["Item", "OAI common-change model", "CHECK exploratory validation"],
)
table9.to_csv(TABLES / "supplementary_table_9_check_exploratory_validation.csv", index=False)

table10 = pd.DataFrame(
    [
        ["Age", "Baseline age", "Baseline age", "Directly mapped"],
        ["Sex", "Participant sex", "Participant sex", "Directly mapped"],
        ["BMI", "Baseline BMI", "Baseline BMI", "Directly mapped"],
        ["Knee side", "Left/right knee", "Left/right knee", "Directly mapped"],
        ["WOMAC pain", "WOMAC pain at 24-month landmark and 0-24 month change", "WOMAC pain at CHECK T2 and T0-T2 change", "Approximately mapped"],
        ["WOMAC function", "WOMAC function at 24-month landmark and 0-24 month change", "WOMAC function at CHECK T2 and T0-T2 change", "Approximately mapped"],
        ["KL grade", "OAI radiographic KL grade at 24-month landmark", "CHECK radiographic KL grade at T2", "Approximately mapped"],
        ["KL change", "24-month KL minus baseline KL", "T2 KL minus T0 KL", "Approximately mapped"],
        ["Medial JSN", "OAI semiquantitative medial JSN at 24-month landmark", "CHECK medial JSN at T2", "Approximately mapped"],
        ["Medial JSN change", "24-month medial JSN minus baseline medial JSN", "T2 medial JSN minus T0 medial JSN", "Approximately mapped"],
        ["TKA/KR outcome", "Post-landmark side-specific KR/TKA", "Post-landmark side-specific TKA through CHECK follow-up", "Approximately mapped"],
        ["Follow-up time", "Months after 24-month landmark", "Months after CHECK T2 landmark", "Approximately mapped"],
    ],
    columns=["Predictor", "OAI definition", "CHECK definition", "Harmonization decision"],
)
table10.to_csv(TABLES / "supplementary_table_10_oai_check_predictor_harmonization.csv", index=False)

print(TABLES / "supplementary_table_9_check_exploratory_validation.csv")
print(TABLES / "supplementary_table_10_oai_check_predictor_harmonization.csv")
