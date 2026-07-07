#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(survival)
})

args_file <- sub("--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])
if (is.na(args_file)) {
  script_dir <- getwd()
} else {
  script_dir <- dirname(normalizePath(args_file))
}
root <- normalizePath(file.path(script_dir, ".."))
derived_dir <- file.path(root, "derived", "OAI")
results_tables <- file.path(root, "results", "tables")
results_figures <- file.path(root, "results", "figures")
results_models <- file.path(root, "results", "models")

dir.create(results_tables, recursive = TRUE, showWarnings = FALSE)
dir.create(results_figures, recursive = TRUE, showWarnings = FALSE)
dir.create(results_models, recursive = TRUE, showWarnings = FALSE)

infile <- file.path(derived_dir, "oai_24m_landmark_dataset.csv")
df <- read.csv(infile, stringsAsFactors = FALSE, check.names = TRUE)

analysis <- subset(df, landmark_complete_core_24m == 1)
analysis$sex <- factor(analysis$enrollee_p02sex_num, levels = c(1, 2), labels = c("Male", "Female"))
analysis$side <- factor(analysis$side)
analysis$pain_trajectory_rule_0_24m <- factor(
  analysis$pain_trajectory_rule_0_24m,
  levels = c("low_stable", "moderate_stable", "worsening", "high_persistent", "improving", "missing")
)

baseline_vars <- c(
  "time_from_landmark_months",
  "event_after_landmark",
  "id",
  "side",
  "sex",
  "subject_v00age_num",
  "clinical00_p01bmi_num",
  "baseline_prior_knee_injury_num",
  "baseline_prior_knee_surgery_num",
  "womac_pain_0m",
  "womac_function_0m",
  "xray_sq_v00xrkl_num"
)

dynamic_vars <- c(
  "time_from_landmark_months",
  "event_after_landmark",
  "id",
  "side",
  "sex",
  "subject_v00age_num",
  "clinical00_p01bmi_num",
  "baseline_prior_knee_injury_num",
  "baseline_prior_knee_surgery_num",
  "womac_pain_24m",
  "womac_pain_delta_0_24m",
  "womac_function_24m",
  "womac_function_delta_0_24m",
  "xray_kl_current_24m",
  "xray_jsn_medial_current_24m",
  "pain_trajectory_rule_0_24m"
)

baseline_complete <- analysis[complete.cases(analysis[, baseline_vars]), baseline_vars]
dynamic_complete <- analysis[complete.cases(analysis[, dynamic_vars]), dynamic_vars]

baseline_formula <- Surv(time_from_landmark_months, event_after_landmark) ~
  subject_v00age_num +
  sex +
  clinical00_p01bmi_num +
  side +
  baseline_prior_knee_injury_num +
  baseline_prior_knee_surgery_num +
  womac_pain_0m +
  womac_function_0m +
  xray_sq_v00xrkl_num +
  cluster(id)

dynamic_formula <- Surv(time_from_landmark_months, event_after_landmark) ~
  subject_v00age_num +
  sex +
  clinical00_p01bmi_num +
  side +
  baseline_prior_knee_injury_num +
  baseline_prior_knee_surgery_num +
  womac_pain_24m +
  womac_pain_delta_0_24m +
  womac_function_24m +
  womac_function_delta_0_24m +
  xray_kl_current_24m +
  xray_jsn_medial_current_24m +
  pain_trajectory_rule_0_24m +
  cluster(id)

cox_baseline <- coxph(baseline_formula, data = baseline_complete, x = TRUE)
cox_dynamic <- coxph(dynamic_formula, data = dynamic_complete, x = TRUE)

saveRDS(cox_baseline, file.path(results_models, "cox_oai_24m_baseline.rds"))
saveRDS(cox_dynamic, file.path(results_models, "cox_oai_24m_dynamic.rds"))

tidy_cox <- function(model, model_name) {
  s <- summary(model)
  coef_df <- as.data.frame(s$coefficients)
  ci_df <- as.data.frame(s$conf.int)
  coef_df$term <- rownames(coef_df)
  ci_df$term <- rownames(ci_df)
  out <- merge(coef_df, ci_df, by = "term", all.x = TRUE)
  data.frame(
    model = model_name,
    term = out$term,
    beta = out[["coef"]],
    hazard_ratio = out[["exp(coef).x"]],
    ci_lower_95 = out[["lower .95"]],
    ci_upper_95 = out[["upper .95"]],
    robust_se = out[["robust se"]],
    z = out[["z"]],
    p_value = out[["Pr(>|z|)"]],
    row.names = NULL
  )
}

coef_out <- rbind(
  tidy_cox(cox_baseline, "baseline"),
  tidy_cox(cox_dynamic, "dynamic")
)
write.csv(coef_out, file.path(results_tables, "cox_oai_24m_coefficients.csv"), row.names = FALSE)

model_metrics <- function(model, model_name) {
  s <- summary(model)
  data.frame(
    model = model_name,
    n = model$n,
    events = model$nevent,
    concordance = unname(s$concordance[1]),
    concordance_se = unname(s$concordance[2]),
    loglik_null = model$loglik[1],
    loglik_model = model$loglik[2],
    aic = extractAIC(model)[2],
    row.names = NULL
  )
}

metrics <- rbind(
  model_metrics(cox_baseline, "baseline"),
  model_metrics(cox_dynamic, "dynamic")
)
write.csv(metrics, file.path(results_tables, "cox_oai_24m_model_metrics.csv"), row.names = FALSE)

zph_dynamic <- cox.zph(cox_dynamic)
zph_table <- as.data.frame(zph_dynamic$table)
zph_table$term <- rownames(zph_table)
write.csv(zph_table, file.path(results_tables, "cox_oai_24m_dynamic_ph_test.csv"), row.names = FALSE)

capture.output(
  {
    cat("OAI 24-month landmark Cox models\n")
    cat("Input file:", infile, "\n\n")
    cat("Baseline model complete-case knees:", nrow(baseline_complete), "\n")
    cat("Baseline model events after 24 months:", sum(baseline_complete$event_after_landmark), "\n")
    cat("Baseline model participants:", length(unique(baseline_complete$id)), "\n\n")
    cat("Dynamic model complete-case knees:", nrow(dynamic_complete), "\n")
    cat("Dynamic model events after 24 months:", sum(dynamic_complete$event_after_landmark), "\n")
    cat("Dynamic model participants:", length(unique(dynamic_complete$id)), "\n\n")
    cat("Baseline model\n")
    print(summary(cox_baseline))
    cat("\n\nDynamic model\n")
    print(summary(cox_dynamic))
    cat("\n\nDynamic model proportional hazards test\n")
    print(zph_dynamic)
  },
  file = file.path(results_tables, "cox_oai_24m_model_summary.txt")
)

km_data <- subset(
  dynamic_complete,
  pain_trajectory_rule_0_24m %in% c("low_stable", "moderate_stable", "worsening", "high_persistent", "improving")
)
km_fit <- survfit(
  Surv(time_from_landmark_months, event_after_landmark) ~ pain_trajectory_rule_0_24m,
  data = km_data
)

png(file.path(results_figures, "oai_24m_tka_km_by_pain_trajectory.png"), width = 1200, height = 850, res = 140)
plot(
  km_fit,
  col = c("#2C7BB6", "#00A6A6", "#Fdae61", "#D7191C", "#7B3294"),
  lwd = 2,
  xlab = "Months after 24-month landmark",
  ylab = "TKA/KR-free survival",
  xlim = c(0, 120),
  mark.time = FALSE
)
legend(
  "bottomleft",
  legend = levels(droplevels(km_data$pain_trajectory_rule_0_24m)),
  col = c("#2C7BB6", "#00A6A6", "#Fdae61", "#D7191C", "#7B3294"),
  lwd = 2,
  bty = "n"
)
dev.off()

cat("Wrote Cox outputs to", results_tables, "\n")
cat("Baseline complete-case knees:", nrow(baseline_complete), "\n")
cat("Baseline events:", sum(baseline_complete$event_after_landmark), "\n")
cat("Dynamic complete-case knees:", nrow(dynamic_complete), "\n")
cat("Dynamic events:", sum(dynamic_complete$event_after_landmark), "\n")
cat("Dynamic model C-index:", metrics$concordance[metrics$model == "dynamic"], "\n")
