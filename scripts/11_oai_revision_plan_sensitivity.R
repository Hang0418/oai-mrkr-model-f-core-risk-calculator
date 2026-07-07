#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(survival)
})

args_file <- sub("--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])
script_dir <- if (is.na(args_file)) getwd() else dirname(normalizePath(args_file))
root <- normalizePath(file.path(script_dir, ".."))

derived_oai <- file.path(root, "derived", "OAI")
derived_validation <- file.path(root, "derived", "validation")
results_tables <- file.path(root, "results", "tables")
results_models <- file.path(root, "results", "models")
dir.create(results_tables, recursive = TRUE, showWarnings = FALSE)
dir.create(results_models, recursive = TRUE, showWarnings = FALSE)

read_csv <- function(path) read.csv(path, stringsAsFactors = FALSE, check.names = TRUE)

binary_auc <- function(y, score) {
  ok <- !is.na(y) & is.finite(score)
  y <- as.integer(y[ok] == 1)
  score <- score[ok]
  n1 <- sum(y == 1)
  n0 <- sum(y == 0)
  if (n1 == 0 || n0 == 0) return(NA_real_)
  ranks <- rank(score, ties.method = "average")
  (sum(ranks[y == 1]) - n1 * (n1 + 1) / 2) / (n1 * n0)
}

cindex_lp <- function(data, lp) {
  ok <- complete.cases(data[, c("time", "event")]) & is.finite(lp)
  as.numeric(concordance(Surv(time, event) ~ I(-lp), data = data[ok, ])$concordance)
}

predict_risk <- function(model, newdata, horizon) {
  bh <- basehaz(model, centered = FALSE)
  h0 <- approx(bh$time, bh$hazard, xout = horizon, method = "constant", rule = 2, f = 0)$y
  lp <- predict(model, newdata = newdata, type = "lp", reference = "zero")
  pmin(pmax(1 - exp(-h0 * exp(lp)), 0), 1)
}

prepare_oai <- function() {
  df <- read_csv(file.path(derived_oai, "oai_24m_landmark_dataset.csv"))
  df <- subset(df, landmark_eligible_24m == 1 & time_from_landmark_months > 0)
  data.frame(
    id = as.character(df$id),
    knee_id = paste("OAI", df$id, df$side, sep = "_"),
    side = factor(df$side),
    time = df$time_from_landmark_months,
    event = df$event_after_landmark,
    age = df$subject_v00age_num,
    female = ifelse(df$enrollee_p02sex_num == 2, 1, 0),
    bmi = df$clinical00_p01bmi_num,
    pain_0 = df$womac_pain_0m,
    function_0 = df$womac_function_0m,
    stiffness_0 = df$baseline_womac_stiffness_num,
    pain_change = df$womac_pain_delta_0_24m,
    function_change = df$womac_function_delta_0_24m,
    kl_0 = df$xray_sq_v00xrkl_num,
    kl_change = df$xray_kl_delta_0_24m,
    jsn_medial_0 = df$xray_sq_v00xrjsm_num,
    jsn_medial_change = df$xray_jsn_medial_delta_0_24m,
    jsn_lateral_0 = df$xray_sq_v00xrjsl_num,
    jsn_lateral_change = df$xray_jsn_lateral_current_24m - df$xray_sq_v00xrjsl_num,
    baseline_kr_or_excluded = df$event_before_or_at_landmark,
    landmark_complete_core_24m = df$landmark_complete_core_24m
  )
}

fit_cox <- function(vars, data) {
  coxph(as.formula(paste("Surv(time, event) ~", paste(vars, collapse = " + "), "+ cluster(id)")),
        data = data, x = TRUE, model = TRUE)
}

fit_cox_nocluster <- function(vars, data) {
  coxph(as.formula(paste("Surv(time, event) ~", paste(vars, collapse = " + "))),
        data = data, x = TRUE, model = TRUE)
}

summarize_group <- function(df, group_name) {
  data.frame(
    group = group_name,
    knees = nrow(df),
    participants = length(unique(df$id)),
    events = sum(df$event == 1, na.rm = TRUE),
    event_rate = mean(df$event == 1, na.rm = TRUE),
    age_mean = mean(df$age, na.rm = TRUE),
    female_pct = mean(df$female == 1, na.rm = TRUE),
    bmi_mean = mean(df$bmi, na.rm = TRUE),
    pain0_mean = mean(df$pain_0, na.rm = TRUE),
    function0_mean = mean(df$function_0, na.rm = TRUE),
    kl0_mean = mean(df$kl_0, na.rm = TRUE),
    jsn_medial0_mean = mean(df$jsn_medial_0, na.rm = TRUE),
    jsn_lateral0_mean = mean(df$jsn_lateral_0, na.rm = TRUE)
  )
}

oai <- prepare_oai()

vars_c <- c("age", "female", "bmi", "side", "pain_0", "function_0", "stiffness_0",
            "kl_0", "jsn_medial_0", "jsn_lateral_0")
vars_e <- c("age", "female", "bmi", "side", "pain_0", "function_0", "stiffness_0",
            "pain_change", "function_change", "kl_0", "kl_change",
            "jsn_medial_0", "jsn_medial_change", "jsn_lateral_0", "jsn_lateral_change")
common_vars <- unique(c(vars_c, vars_e))
analysis <- oai[complete.cases(oai[, c("time", "event", common_vars)]), ]
excluded <- oai[!oai$knee_id %in% analysis$knee_id, ]

fit_c <- fit_cox(vars_c, analysis)
fit_e <- fit_cox(vars_e, analysis)
saveRDS(fit_e, file.path(results_models, "oai_revision_model_e.rds"))

ph <- as.data.frame(cox.zph(fit_e)$table)
ph$term <- rownames(ph)
write.csv(ph, file.path(results_tables, "oai_revision_model_e_ph_test.csv"), row.names = FALSE)

risk60_c <- predict_risk(fit_c, analysis, 60)
risk60_e <- predict_risk(fit_e, analysis, 60)
event60_known <- analysis$time >= 60 | (analysis$event == 1 & analysis$time <= 60)
logistic_df <- analysis[event60_known, ]
logistic_df$event60 <- as.integer(logistic_df$event == 1 & logistic_df$time <= 60)
logistic_df$risk60_c <- risk60_c[event60_known]
logistic_df$risk60_e <- risk60_e[event60_known]

logit_e <- glm(
  event60 ~ age + female + bmi + side + pain_0 + function_0 + stiffness_0 +
    pain_change + function_change + kl_0 + kl_change + jsn_medial_0 +
    jsn_medial_change + jsn_lateral_0 + jsn_lateral_change,
  data = logistic_df,
  family = binomial()
)
logit_c <- glm(
  event60 ~ age + female + bmi + side + pain_0 + function_0 + stiffness_0 +
    kl_0 + jsn_medial_0 + jsn_lateral_0,
  data = logistic_df,
  family = binomial()
)
pred_logit_e <- predict(logit_e, type = "response")
pred_logit_c <- predict(logit_c, type = "response")
logistic_metrics <- data.frame(
  model = c("Model C fixed-horizon logistic", "Model E fixed-horizon logistic"),
  n = nrow(logistic_df),
  events_60m = sum(logistic_df$event60),
  auc_60m = c(binary_auc(logistic_df$event60, pred_logit_c), binary_auc(logistic_df$event60, pred_logit_e)),
  mean_predicted_risk = c(mean(pred_logit_c), mean(pred_logit_e)),
  observed_risk = mean(logistic_df$event60),
  aic = c(AIC(logit_c), AIC(logit_e))
)
write.csv(logistic_metrics, file.path(results_tables, "oai_revision_fixed_60m_logistic_sensitivity.csv"), row.names = FALSE)

increment <- data.frame(
  comparison = "Model E vs Model C on common complete set",
  n = nrow(analysis),
  participants = length(unique(analysis$id)),
  events = sum(analysis$event),
  lr_chisq = 2 * (as.numeric(logLik(fit_e)) - as.numeric(logLik(fit_c))),
  df = attr(logLik(fit_e), "df") - attr(logLik(fit_c), "df"),
  p_value = pchisq(2 * (as.numeric(logLik(fit_e)) - as.numeric(logLik(fit_c))),
                   df = attr(logLik(fit_e), "df") - attr(logLik(fit_c), "df"),
                   lower.tail = FALSE),
  delta_c_index = cindex_lp(analysis, predict(fit_e, type = "lp", reference = "zero")) -
    cindex_lp(analysis, predict(fit_c, type = "lp", reference = "zero")),
  delta_auc_60m_fixed_logistic = binary_auc(logistic_df$event60, pred_logit_e) - binary_auc(logistic_df$event60, pred_logit_c),
  delta_aic = extractAIC(fit_e)[2] - extractAIC(fit_c)[2]
)
write.csv(increment, file.path(results_tables, "oai_revision_model_c_vs_e_incremental_value.csv"), row.names = FALSE)

inc_exc <- rbind(summarize_group(analysis, "included_model_e_common_complete"),
                 summarize_group(excluded, "excluded_from_model_e_common_complete"))
write.csv(inc_exc, file.path(results_tables, "oai_revision_included_vs_excluded.csv"), row.names = FALSE)

risk_df <- analysis
risk_df$risk60 <- risk60_e
risk_df$risk_group_clinical <- cut(
  risk_df$risk60,
  breaks = c(-Inf, 0.05, 0.15, 0.30, Inf),
  labels = c("<5%", "5-15%", "15-30%", ">30%")
)
risk_rows <- lapply(split(risk_df, risk_df$risk_group_clinical), function(g) {
  fit <- survfit(Surv(time, event) ~ 1, data = g)
  s <- summary(fit, times = 60, extend = TRUE)
  data.frame(
    risk_group = as.character(g$risk_group_clinical[1]),
    knees = nrow(g),
    participants = length(unique(g$id)),
    total_events = sum(g$event),
    events_by_60m = sum(g$event == 1 & g$time <= 60),
    mean_predicted_60m_risk = mean(g$risk60),
    observed_km_60m_risk = if (length(s$surv)) 1 - s$surv[1] else NA_real_
  )
})
risk_strata <- do.call(rbind, risk_rows)
write.csv(risk_strata, file.path(results_tables, "oai_revision_model_e_clinical_risk_strata.csv"), row.names = FALSE)

cal_slope <- coef(coxph(Surv(time, event) ~ predict(fit_e, newdata = analysis, type = "lp", reference = "zero"), data = analysis))[1]
calibration_summary <- data.frame(
  model = "Model E",
  horizon_months = 60,
  mean_predicted_risk = mean(risk60_e),
  observed_km_risk = {
    s <- summary(survfit(Surv(time, event) ~ 1, data = analysis), times = 60, extend = TRUE)
    if (length(s$surv)) 1 - s$surv[1] else NA_real_
  },
  calibration_slope_survival = cal_slope,
  note = "Calibration intercept for survival risk is approximated by mean predicted vs observed risk; full intercept requires a fixed-horizon model."
)
write.csv(calibration_summary, file.path(results_tables, "oai_revision_model_e_calibration_summary.csv"), row.names = FALSE)

capture.output({
  cat("Revision-plan sensitivity analyses\n\n")
  cat("Included knees:", nrow(analysis), "participants:", length(unique(analysis$id)), "events:", sum(analysis$event), "\n")
  cat("Excluded eligible knees:", nrow(excluded), "participants:", length(unique(excluded$id)), "events:", sum(excluded$event), "\n\n")
  cat("PH test\n")
  print(ph)
  cat("\nFixed-horizon logistic sensitivity\n")
  print(logistic_metrics)
  cat("\nIncremental value\n")
  print(increment)
  cat("\nClinical risk strata\n")
  print(risk_strata)
  cat("\nIncluded vs excluded\n")
  print(inc_exc)
}, file = file.path(results_tables, "oai_revision_sensitivity_report.txt"))

cat("Wrote revision sensitivity outputs.\n")
print(increment)
print(logistic_metrics)
print(risk_strata)
