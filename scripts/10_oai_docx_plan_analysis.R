#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(survival)
  library(ggplot2)
})

args_file <- sub("--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])
script_dir <- if (is.na(args_file)) getwd() else dirname(normalizePath(args_file))
root <- normalizePath(file.path(script_dir, ".."))

derived_oai <- file.path(root, "derived", "OAI")
derived_validation <- file.path(root, "derived", "validation")
results_tables <- file.path(root, "results", "tables")
results_figures <- file.path(root, "results", "figures")
results_models <- file.path(root, "results", "models")

dir.create(derived_validation, recursive = TRUE, showWarnings = FALSE)
dir.create(results_tables, recursive = TRUE, showWarnings = FALSE)
dir.create(results_figures, recursive = TRUE, showWarnings = FALSE)
dir.create(results_models, recursive = TRUE, showWarnings = FALSE)

set.seed(20260618)
times_eval <- c(24, 60, 96)

read_csv <- function(path) read.csv(path, stringsAsFactors = FALSE, check.names = TRUE)

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
    pain_24 = df$womac_pain_24m,
    pain_change = df$womac_pain_delta_0_24m,
    function_0 = df$womac_function_0m,
    function_24 = df$womac_function_24m,
    function_change = df$womac_function_delta_0_24m,
    stiffness_0 = df$baseline_womac_stiffness_num,
    total_0 = df$baseline_womac_total_num,
    kl_0 = df$xray_sq_v00xrkl_num,
    kl_24 = df$xray_kl_current_24m,
    kl_change = df$xray_kl_delta_0_24m,
    jsn_medial_0 = df$xray_sq_v00xrjsm_num,
    jsn_medial_24 = df$xray_jsn_medial_current_24m,
    jsn_medial_change = df$xray_jsn_medial_delta_0_24m,
    jsn_lateral_0 = df$xray_sq_v00xrjsl_num,
    jsn_lateral_24 = df$xray_jsn_lateral_current_24m,
    jsn_lateral_change = df$xray_jsn_lateral_current_24m - df$xray_sq_v00xrjsl_num,
    pain_trajectory = df$pain_trajectory_rule_0_24m
  )
}

cindex_lp <- function(data, lp) {
  ok <- complete.cases(data[, c("time", "event")]) & is.finite(lp)
  if (sum(data$event[ok]) < 2) return(NA_real_)
  as.numeric(concordance(Surv(time, event) ~ I(-lp), data = data[ok, ])$concordance)
}

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

td_auc <- function(data, score, t) {
  ok <- is.finite(score) & !is.na(data$time) & !is.na(data$event)
  d <- data[ok, ]
  score <- score[ok]
  y <- rep(NA_integer_, nrow(d))
  y[d$event == 1 & d$time <= t] <- 1
  y[d$time > t] <- 0
  binary_auc(y, score)
}

censor_surv <- function(data, t) {
  cens_event <- 1 - data$event
  fit <- survfit(Surv(time, cens_event) ~ 1, data = data)
  s <- summary(fit, times = t, extend = TRUE)
  if (length(s$surv)) max(s$surv[1], 1e-6) else 1
}

ipcw_brier <- function(data, risk, t) {
  ok <- is.finite(risk) & !is.na(data$time) & !is.na(data$event)
  d <- data[ok, ]
  r <- risk[ok]
  g_t <- censor_surv(d, t)
  err <- rep(NA_real_, nrow(d))
  case <- d$event == 1 & d$time <= t
  control <- d$time > t
  err[case] <- (1 - r[case])^2 / pmax(censor_surv(d, d$time[case]), 1e-6)
  err[control] <- (0 - r[control])^2 / g_t
  mean(err, na.rm = TRUE)
}

predict_risk <- function(model, newdata, horizon) {
  bh <- basehaz(model, centered = FALSE)
  h0 <- approx(bh$time, bh$hazard, xout = horizon, method = "constant", rule = 2, f = 0)$y
  lp <- predict(model, newdata = newdata, type = "lp", reference = "zero")
  pmin(pmax(1 - exp(-h0 * exp(lp)), 0), 1)
}

calibration_table <- function(data, risk, horizon, groups = 10, label = "") {
  ok <- complete.cases(data[, c("time", "event")]) & is.finite(risk)
  d <- data[ok, ]
  d$risk <- risk[ok]
  cuts <- unique(quantile(d$risk, seq(0, 1, length.out = groups + 1), na.rm = TRUE))
  d$group <- if (length(cuts) <= 2) 1 else cut(d$risk, breaks = cuts, include.lowest = TRUE, labels = FALSE)
  out <- lapply(split(d, d$group), function(g) {
    fit <- survfit(Surv(time, event) ~ 1, data = g)
    s <- summary(fit, times = horizon, extend = TRUE)
    data.frame(
      model = label,
      group = as.integer(g$group[1]),
      n = nrow(g),
      events_by_horizon = sum(g$event == 1 & g$time <= horizon),
      mean_predicted_risk = mean(g$risk),
      observed_km_risk = if (length(s$surv)) 1 - s$surv[1] else NA_real_
    )
  })
  do.call(rbind, out)
}

decision_curve <- function(data, risk, horizon, thresholds, label) {
  ok <- complete.cases(data[, c("time", "event")]) & is.finite(risk) &
    (data$time >= horizon | (data$event == 1 & data$time <= horizon))
  d <- data[ok, ]
  r <- risk[ok]
  y <- as.integer(d$event == 1 & d$time <= horizon)
  n <- length(y)
  prev <- mean(y)
  out <- lapply(thresholds, function(pt) {
    treat <- as.integer(r >= pt)
    tp <- sum(treat == 1 & y == 1)
    fp <- sum(treat == 1 & y == 0)
    data.frame(
      model = label,
      threshold = pt,
      n = n,
      events_by_horizon = sum(y),
      net_benefit_model = tp / n - fp / n * pt / (1 - pt),
      net_benefit_treat_all = prev - (1 - prev) * pt / (1 - pt),
      net_benefit_treat_none = 0
    )
  })
  do.call(rbind, out)
}

fit_cox <- function(vars, data) {
  f <- as.formula(paste("Surv(time, event) ~", paste(vars, collapse = " + "), "+ cluster(id)"))
  coxph(f, data = data, x = TRUE, model = TRUE)
}

fit_cox_nocluster <- function(vars, data) {
  f <- as.formula(paste("Surv(time, event) ~", paste(vars, collapse = " + ")))
  coxph(f, data = data, x = TRUE, model = TRUE)
}

bootstrap_cindex <- function(data, vars, b = 100) {
  ids <- unique(data$id)
  fit0 <- fit_cox(vars, data)
  apparent <- cindex_lp(data, predict(fit0, newdata = data, type = "lp", reference = "zero"))
  optimism <- c()
  failures <- 0
  for (i in seq_len(b)) {
    sampled <- sample(ids, length(ids), replace = TRUE)
    boot <- do.call(rbind, lapply(seq_along(sampled), function(j) {
      z <- data[data$id == sampled[j], ]
      z
    }))
    fit <- try(fit_cox_nocluster(vars, boot), silent = TRUE)
    if (inherits(fit, "try-error")) {
      failures <- failures + 1
      next
    }
    lp_boot <- try(predict(fit, newdata = boot, type = "lp", reference = "zero"), silent = TRUE)
    lp_test <- try(predict(fit, newdata = data, type = "lp", reference = "zero"), silent = TRUE)
    if (inherits(lp_boot, "try-error") || inherits(lp_test, "try-error")) {
      failures <- failures + 1
      next
    }
    optimism <- c(optimism, cindex_lp(boot, lp_boot) - cindex_lp(data, lp_test))
  }
  data.frame(
    apparent_c_index = apparent,
    bootstrap_repetitions = b,
    bootstrap_used = length(optimism),
    bootstrap_failures = failures,
    optimism = mean(optimism, na.rm = TRUE),
    optimism_corrected_c_index = apparent - mean(optimism, na.rm = TRUE)
  )
}

patient_split_validation <- function(data, vars, repeats = 50, train_frac = 0.7) {
  ids <- unique(data$id)
  out <- lapply(seq_len(repeats), function(i) {
    train_ids <- sample(ids, floor(length(ids) * train_frac))
    train <- data[data$id %in% train_ids, ]
    test <- data[!data$id %in% train_ids, ]
    fit <- try(fit_cox_nocluster(vars, train), silent = TRUE)
    if (inherits(fit, "try-error")) return(NULL)
    lp <- predict(fit, newdata = test, type = "lp", reference = "zero")
    data.frame(
      split_repeat = i,
      train_participants = length(unique(train$id)),
      test_participants = length(unique(test$id)),
      test_knees = nrow(test),
      test_events = sum(test$event),
      c_index = cindex_lp(test, lp)
    )
  })
  do.call(rbind, out)
}

coef_table <- function(model, name) {
  s <- summary(model)
  co <- as.data.frame(s$coefficients)
  ci <- as.data.frame(s$conf.int)
  data.frame(
    model = name,
    term = rownames(co),
    hazard_ratio = ci[, "exp(coef)"],
    ci_lower_95 = ci[, "lower .95"],
    ci_upper_95 = ci[, "upper .95"],
    p_value = co[, "Pr(>|z|)"],
    row.names = NULL
  )
}

symptom_structure_groups <- function(data) {
  p75 <- quantile(data$pain_24, 0.75, na.rm = TRUE)
  data$pain_high <- data$pain_24 >= p75
  data$structure_high <- data$kl_24 >= 3 | data$jsn_medial_24 >= 2 | data$jsn_lateral_24 >= 2
  data$symptom_structure_group <- ifelse(
    data$pain_high & data$structure_high, "High pain / high structure",
    ifelse(data$pain_high & !data$structure_high, "High pain / low structure",
           ifelse(!data$pain_high & data$structure_high, "Low pain / high structure", "Low pain / low structure"))
  )
  data$symptom_structure_group <- factor(
    data$symptom_structure_group,
    levels = c("Low pain / low structure", "High pain / low structure", "Low pain / high structure", "High pain / high structure")
  )
  data
}

oai <- prepare_oai()

models <- list(
  A_basic = c("age", "female", "bmi", "side"),
  B_baseline_symptoms = c("age", "female", "bmi", "side", "pain_0", "function_0", "stiffness_0"),
  C_baseline_symptoms_imaging = c("age", "female", "bmi", "side", "pain_0", "function_0", "stiffness_0", "kl_0", "jsn_medial_0", "jsn_lateral_0"),
  D_dynamic_clinical = c("age", "female", "bmi", "side", "pain_0", "function_0", "stiffness_0", "pain_change", "function_change"),
  E_dynamic_clinical_imaging = c("age", "female", "bmi", "side", "pain_0", "function_0", "stiffness_0", "pain_change", "function_change", "kl_0", "kl_change", "jsn_medial_0", "jsn_medial_change", "jsn_lateral_0", "jsn_lateral_change")
)

complete_for <- function(vars) oai[complete.cases(oai[, c("time", "event", vars)]), ]
all_vars <- unique(unlist(models))
common_complete <- complete_for(all_vars)
write.csv(common_complete, file.path(derived_validation, "oai_docx_plan_common_complete_dataset.csv"), row.names = FALSE)

metric_rows <- list()
coef_rows <- list()
cal_rows <- list()
dca_rows <- list()
split_rows <- list()
boot_rows <- list()

for (nm in names(models)) {
  vars <- models[[nm]]
  data_model_specific <- complete_for(vars)
  data_common <- common_complete
  fit <- fit_cox(vars, data_common)
  saveRDS(fit, file.path(results_models, paste0("oai_docx_", nm, ".rds")))
  lp <- predict(fit, newdata = data_common, type = "lp", reference = "zero")
  risks <- lapply(times_eval, function(t) predict_risk(fit, data_common, t))
  names(risks) <- paste0("risk_", times_eval)
  row <- data.frame(
    model = nm,
    analysis_set = "common_complete",
    n = nrow(data_common),
    participants = length(unique(data_common$id)),
    events = sum(data_common$event),
    model_specific_n = nrow(data_model_specific),
    model_specific_participants = length(unique(data_model_specific$id)),
    model_specific_events = sum(data_model_specific$event),
    c_index = cindex_lp(data_common, lp),
    aic = extractAIC(fit)[2],
    likelihood_ratio = fit$loglik[2] - fit$loglik[1]
  )
  for (t in times_eval) {
    risk <- risks[[paste0("risk_", t)]]
    row[[paste0("auc_", t, "m")]] <- td_auc(data_common, lp, t)
    row[[paste0("brier_", t, "m")]] <- ipcw_brier(data_common, risk, t)
    fit_km <- survfit(Surv(time, event) ~ 1, data = data_common)
    s <- summary(fit_km, times = t, extend = TRUE)
    row[[paste0("mean_pred_risk_", t, "m")]] <- mean(risk)
    row[[paste0("observed_km_risk_", t, "m")]] <- if (length(s$surv)) 1 - s$surv[1] else NA_real_
  }
  metric_rows[[nm]] <- row
  coef_rows[[nm]] <- coef_table(fit, nm)
  if (nm == "E_dynamic_clinical_imaging") {
    cal_rows[[nm]] <- calibration_table(data_common, risks[["risk_60"]], 60, label = nm)
    dca_rows[[nm]] <- decision_curve(data_common, risks[["risk_60"]], 60, seq(0.02, 0.30, 0.02), label = nm)
  }
  boot <- bootstrap_cindex(data_common, vars, b = 100)
  boot$model <- nm
  boot_rows[[nm]] <- boot
  split <- patient_split_validation(data_common, vars, repeats = 50)
  split$model <- nm
  split_rows[[nm]] <- split
}

metrics <- do.call(rbind, metric_rows)
boot <- do.call(rbind, boot_rows)
splits <- do.call(rbind, split_rows)
coefs <- do.call(rbind, coef_rows)
cal <- do.call(rbind, cal_rows)
dca <- do.call(rbind, dca_rows)

metrics <- merge(metrics, boot[, c("model", "optimism", "optimism_corrected_c_index", "bootstrap_used")], by = "model", all.x = TRUE)
split_summary <- aggregate(c_index ~ model, data = splits, function(x) c(mean = mean(x), sd = sd(x), q025 = quantile(x, 0.025), q975 = quantile(x, 0.975)))
split_summary <- do.call(data.frame, split_summary)
names(split_summary) <- c("model", "split_c_index_mean", "split_c_index_sd", "split_c_index_q025", "split_c_index_q975")
metrics <- merge(metrics, split_summary, by = "model", all.x = TRUE)

write.csv(metrics, file.path(results_tables, "oai_docx_plan_model_comparison.csv"), row.names = FALSE)
write.csv(boot, file.path(results_tables, "oai_docx_plan_bootstrap_validation.csv"), row.names = FALSE)
write.csv(splits, file.path(results_tables, "oai_docx_plan_repeated_patient_split.csv"), row.names = FALSE)
write.csv(coefs, file.path(results_tables, "oai_docx_plan_cox_coefficients.csv"), row.names = FALSE)
write.csv(cal, file.path(results_tables, "oai_docx_plan_calibration_60m.csv"), row.names = FALSE)
write.csv(dca, file.path(results_tables, "oai_docx_plan_decision_curve_60m.csv"), row.names = FALSE)

main_data <- symptom_structure_groups(common_complete)
fit_group <- coxph(
  Surv(time, event) ~ symptom_structure_group + age + female + bmi + side + cluster(id),
  data = main_data,
  x = TRUE,
  model = TRUE
)
group_coef <- coef_table(fit_group, "symptom_structure_group")
write.csv(group_coef, file.path(results_tables, "oai_docx_plan_symptom_structure_group_hr.csv"), row.names = FALSE)

group_summary <- aggregate(
  cbind(event, pain_24, kl_24, jsn_medial_24) ~ symptom_structure_group,
  data = main_data,
  FUN = function(x) c(n = length(x), mean = mean(x, na.rm = TRUE))
)
write.csv(group_summary, file.path(results_tables, "oai_docx_plan_symptom_structure_group_summary.csv"), row.names = FALSE)

main_fit <- readRDS(file.path(results_models, "oai_docx_E_dynamic_clinical_imaging.rds"))
main_risk60 <- predict_risk(main_fit, common_complete, 60)
risk_df <- common_complete
risk_df$risk60 <- main_risk60
risk_df$risk_group <- cut(
  risk_df$risk60,
  breaks = quantile(risk_df$risk60, c(0, 1 / 3, 2 / 3, 1), na.rm = TRUE),
  include.lowest = TRUE,
  labels = c("Low", "Intermediate", "High")
)
km <- survfit(Surv(time, event) ~ risk_group, data = risk_df)
png(file.path(results_figures, "oai_docx_plan_km_by_risk_group.png"), width = 1200, height = 850, res = 140)
plot(km, col = c("#2C7BB6", "#00A6A6", "#D7191C"), lwd = 2, xlab = "Months after 24-month landmark", ylab = "KR/TKA-free survival", mark.time = FALSE)
legend("bottomleft", legend = levels(risk_df$risk_group), col = c("#2C7BB6", "#00A6A6", "#D7191C"), lwd = 2, bty = "n")
dev.off()

png(file.path(results_figures, "oai_docx_plan_calibration_60m.png"), width = 1000, height = 760, res = 140)
plot(cal$mean_predicted_risk, cal$observed_km_risk, pch = 19, col = "#1F77B4",
     xlab = "Mean predicted 5-year risk", ylab = "Observed Kaplan-Meier 5-year risk",
     main = "OAI 24-month landmark calibration: Model E")
abline(0, 1, lty = 2, col = "grey40")
lines(cal$mean_predicted_risk, cal$observed_km_risk, col = "#1F77B4", lwd = 2)
dev.off()

png(file.path(results_figures, "oai_docx_plan_decision_curve_60m.png"), width = 1100, height = 760, res = 140)
plot(dca$threshold, dca$net_benefit_model, type = "l", lwd = 2, col = "#1F77B4",
     xlab = "Risk threshold", ylab = "Net benefit", main = "OAI 24-month landmark decision curve: Model E")
lines(dca$threshold, dca$net_benefit_treat_all, lwd = 2, col = "#D62728")
lines(dca$threshold, dca$net_benefit_treat_none, lwd = 2, col = "grey40")
legend("topright", legend = c("Model E", "Treat all", "Treat none"), col = c("#1F77B4", "#D62728", "grey40"), lwd = 2, bty = "n")
dev.off()

capture.output({
  cat("OAI DOCX-plan 24-month landmark analysis\n\n")
  cat("Common complete analysis set knees:", nrow(common_complete), "\n")
  cat("Participants:", length(unique(common_complete$id)), "\n")
  cat("KR/TKA events after landmark:", sum(common_complete$event), "\n\n")
  cat("Model comparison\n")
  print(metrics)
  cat("\nSymptom-structure group model\n")
  print(summary(fit_group))
}, file = file.path(results_tables, "oai_docx_plan_analysis_report.txt"))

cat("Wrote OAI DOCX-plan analysis outputs.\n")
print(metrics)
