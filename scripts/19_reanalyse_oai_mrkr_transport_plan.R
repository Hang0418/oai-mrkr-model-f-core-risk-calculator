#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(survival)
})

args_file <- sub("--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])
script_dir <- if (is.na(args_file)) getwd() else dirname(normalizePath(args_file))
root <- normalizePath(file.path(script_dir, ".."))

derived_transport <- file.path(root, "derived", "transport")
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
  ok <- complete.cases(data[, c("time_months", "event_primary")]) & is.finite(lp)
  if (sum(data$event_primary[ok] == 1) < 2) return(NA_real_)
  as.numeric(concordance(Surv(time_months, event_primary) ~ I(-lp), data = data[ok, ])$concordance)
}

td_auc <- function(data, score, horizon) {
  ok <- complete.cases(data[, c("time_months", "event_primary")]) & is.finite(score)
  d <- data[ok, ]
  score <- score[ok]
  y <- rep(NA_integer_, nrow(d))
  y[d$event_primary == 1 & d$time_months <= horizon] <- 1
  y[d$time_months > horizon] <- 0
  binary_auc(y, score)
}

censor_surv <- function(data, horizon) {
  cens_event <- 1 - data$event_primary
  fit <- survfit(Surv(time_months, cens_event) ~ 1, data = data)
  s <- summary(fit, times = horizon, extend = TRUE)
  if (length(s$surv)) max(s$surv[1], 1e-6) else 1
}

ipcw_brier <- function(data, risk, horizon) {
  ok <- is.finite(risk) & complete.cases(data[, c("time_months", "event_primary")])
  d <- data[ok, ]
  r <- risk[ok]
  g_t <- censor_surv(d, horizon)
  err <- rep(NA_real_, nrow(d))
  case <- d$event_primary == 1 & d$time_months <= horizon
  control <- d$time_months > horizon
  err[case] <- (1 - r[case])^2 / pmax(censor_surv(d, d$time_months[case]), 1e-6)
  err[control] <- (0 - r[control])^2 / g_t
  mean(err, na.rm = TRUE)
}

km_risk <- function(data, horizon) {
  if (nrow(data) == 0) return(NA_real_)
  s <- summary(survfit(Surv(time_months, event_primary) ~ 1, data = data), times = horizon, extend = TRUE)
  if (length(s$surv)) 1 - s$surv[1] else NA_real_
}

events_by_horizon <- function(data, horizon) {
  if (nrow(data) == 0) return(0L)
  sum(data$event_primary == 1 & data$time_months <= horizon, na.rm = TRUE)
}

censored_before <- function(data, horizon) {
  if (nrow(data) == 0) return(0L)
  sum(data$event_primary == 0 & data$time_months < horizon, na.rm = TRUE)
}

at_risk_at <- function(data, horizon) {
  if (nrow(data) == 0) return(0L)
  sum(data$time_months >= horizon, na.rm = TRUE)
}

predict_risk_from_fit <- function(model, newdata, horizon) {
  bh <- basehaz(model, centered = FALSE)
  h0 <- approx(bh$time, bh$hazard, xout = horizon, method = "constant", rule = 2, f = 0)$y
  lp <- predict(model, newdata = newdata, type = "lp", reference = "zero")
  pmin(pmax(1 - exp(-h0 * exp(lp)), 0), 1)
}

predict_risk_from_lp <- function(model, lp, horizon) {
  bh <- basehaz(model, centered = FALSE)
  h0 <- approx(bh$time, bh$hazard, xout = horizon, method = "constant", rule = 2, f = 0)$y
  pmin(pmax(1 - exp(-h0 * exp(lp)), 0), 1)
}

calibration_table <- function(data, risk, horizon, label, groups = 10) {
  ok <- is.finite(risk) & complete.cases(data[, c("time_months", "event_primary")])
  d <- data[ok, ]
  d$risk <- risk[ok]
  cuts <- unique(quantile(d$risk, seq(0, 1, length.out = groups + 1), na.rm = TRUE))
  d$group <- if (length(cuts) <= 2) 1 else cut(d$risk, breaks = cuts, include.lowest = TRUE, labels = FALSE)
  out <- lapply(split(d, d$group, drop = TRUE), function(g) {
    data.frame(
      model = label,
      horizon_months = horizon,
      group = as.integer(g$group[1]),
      n = nrow(g),
      events_by_horizon = events_by_horizon(g, horizon),
      mean_predicted_risk = mean(g$risk),
      observed_km_risk = km_risk(g, horizon)
    )
  })
  do.call(rbind, out)
}

decision_curve <- function(data, risk, horizon, label) {
  ok <- is.finite(risk) &
    (data$time_months >= horizon | (data$event_primary == 1 & data$time_months <= horizon))
  d <- data[ok, ]
  r <- risk[ok]
  y <- as.integer(d$event_primary == 1 & d$time_months <= horizon)
  thresholds <- seq(0.02, 0.50, by = 0.02)
  n <- length(y)
  prev <- mean(y)
  do.call(rbind, lapply(thresholds, function(pt) {
    treat <- as.integer(r >= pt)
    tp <- sum(treat == 1 & y == 1)
    fp <- sum(treat == 1 & y == 0)
    data.frame(
      model = label,
      horizon_months = horizon,
      threshold = pt,
      n = n,
      events_by_horizon = sum(y),
      net_benefit_model = tp / n - fp / n * pt / (1 - pt),
      net_benefit_treat_all = prev - (1 - prev) * pt / (1 - pt),
      net_benefit_treat_none = 0
    )
  }))
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

prepare_common <- function(df, cohort_name) {
  df$right_knee <- ifelse(df$side_label == "right", 1, 0)
  df$kl_worsening <- ifelse(df$kl_change >= 1, 1, 0)
  df$pain_landmark_z <- as.numeric(scale(df$pain_landmark_0_10))
  df$pain_change_z <- as.numeric(scale(df$pain_change_0_10))
  df$cohort <- cohort_name
  df
}

metric_row <- function(data, lp, risk, horizon, cohort, model_label, outcome_label) {
  data.frame(
    cohort = cohort,
    model = model_label,
    outcome = outcome_label,
    horizon_months = horizon,
    n_knees = nrow(data),
    n_patients = length(unique(data$patient_id)),
    total_events = sum(data$event_primary == 1, na.rm = TRUE),
    events_by_horizon = events_by_horizon(data, horizon),
    censored_before_horizon = censored_before(data, horizon),
    at_risk_at_horizon = at_risk_at(data, horizon),
    c_index = cindex_lp(data, lp),
    auc_horizon = td_auc(data, lp, horizon),
    brier_horizon = if (is.null(risk)) NA_real_ else ipcw_brier(data, risk, horizon),
    mean_predicted_risk = if (is.null(risk)) NA_real_ else mean(risk, na.rm = TRUE),
    observed_km_risk = km_risk(data, horizon)
  )
}

make_combined_outcome <- function(mrkr) {
  out <- mrkr
  sens_event <- ifelse(is.na(out$event_sensitivity), 0, out$event_sensitivity)
  sens_time <- out$time_sensitivity_months
  primary_event <- out$event_primary
  primary_time <- out$time_months

  combined_event <- as.integer(primary_event == 1 | sens_event == 1)
  combined_time <- rep(NA_real_, nrow(out))
  both_event <- primary_event == 1 & sens_event == 1
  primary_only <- primary_event == 1 & sens_event != 1
  sens_only <- primary_event != 1 & sens_event == 1
  no_event <- combined_event == 0
  combined_time[both_event] <- pmin(primary_time[both_event], sens_time[both_event], na.rm = TRUE)
  combined_time[primary_only] <- primary_time[primary_only]
  combined_time[sens_only] <- sens_time[sens_only]
  combined_time[no_event] <- pmax(primary_time[no_event], sens_time[no_event], na.rm = TRUE)
  out$event_primary <- combined_event
  out$time_months <- combined_time
  out
}

horizons <- c(12, 24, 36, 60)
primary_horizon <- 24

oai <- prepare_common(read_csv(file.path(derived_transport, "oai_train_model_f_core.csv")), "OAI")
mrkr <- prepare_common(read_csv(file.path(derived_transport, "mrkr_validation_model_f_core.csv")), "MRKR")

vars_core <- c("age", "female", "right_knee", "pain_landmark_z", "kl_baseline", "kl_worsening")
fit_f_core <- coxph(
  Surv(time_months, event_primary) ~ age + female + right_knee + pain_landmark_z +
    kl_baseline + kl_worsening + cluster(patient_id),
  data = oai,
  x = TRUE,
  model = TRUE
)
saveRDS(fit_f_core, file.path(results_models, "oai_mrkr_plan_model_f_core.rds"))

oai$lp_f_core <- predict(fit_f_core, newdata = oai, type = "lp", reference = "zero")
mrkr$lp_f_core <- predict(fit_f_core, newdata = mrkr, type = "lp", reference = "zero")

fit_mrkr_slope <- coxph(Surv(time_months, event_primary) ~ lp_f_core, data = mrkr, x = TRUE, model = TRUE)
fit_mrkr_offset <- coxph(Surv(time_months, event_primary) ~ offset(lp_f_core), data = mrkr, x = TRUE, model = TRUE)

metric_rows <- list()
cal_rows <- list()
dca_rows <- list()
for (h in horizons) {
  oai$risk_original <- predict_risk_from_fit(fit_f_core, oai, h)
  mrkr$risk_original <- predict_risk_from_fit(fit_f_core, mrkr, h)
  mrkr$risk_recalibrated <- predict_risk_from_fit(fit_mrkr_slope, mrkr, h)
  metric_rows[[length(metric_rows) + 1]] <- metric_row(
    oai, oai$lp_f_core, oai$risk_original, h, "OAI", "Model F-core apparent",
    "OAI KR/TKA after 24m landmark"
  )
  metric_rows[[length(metric_rows) + 1]] <- metric_row(
    mrkr, mrkr$lp_f_core, mrkr$risk_original, h, "MRKR", "Original OAI-derived Model F-core",
    "Side-specific hardware-defined arthroplasty"
  )
  metric_rows[[length(metric_rows) + 1]] <- metric_row(
    mrkr, mrkr$lp_f_core, mrkr$risk_recalibrated, h, "MRKR", "MRKR slope+baseline recalibrated Model F-core",
    "Side-specific hardware-defined arthroplasty"
  )
  mrkr$risk_offset_only <- predict_risk_from_lp(fit_mrkr_offset, mrkr$lp_f_core, h)
  metric_rows[[length(metric_rows) + 1]] <- metric_row(
    mrkr, mrkr$lp_f_core, mrkr$risk_offset_only, h, "MRKR", "MRKR offset-only baseline recalibration",
    "Side-specific hardware-defined arthroplasty"
  )
  if (h == primary_horizon) {
    cal_rows[[length(cal_rows) + 1]] <- calibration_table(oai, oai$risk_original, h, "OAI apparent original")
    cal_rows[[length(cal_rows) + 1]] <- calibration_table(mrkr, mrkr$risk_original, h, "MRKR original OAI baseline")
    cal_rows[[length(cal_rows) + 1]] <- calibration_table(mrkr, mrkr$risk_recalibrated, h, "MRKR slope+baseline recalibrated")
    cal_rows[[length(cal_rows) + 1]] <- calibration_table(mrkr, mrkr$risk_offset_only, h, "MRKR offset-only recalibrated")
    dca_rows[[length(dca_rows) + 1]] <- decision_curve(mrkr, mrkr$risk_original, h, "MRKR original OAI baseline")
    dca_rows[[length(dca_rows) + 1]] <- decision_curve(mrkr, mrkr$risk_recalibrated, h, "MRKR slope+baseline recalibrated")
  }
}
metrics <- do.call(rbind, metric_rows)
calibration <- do.call(rbind, cal_rows)
dca <- do.call(rbind, dca_rows)

time_structure <- do.call(rbind, lapply(list(OAI = oai, MRKR = mrkr), function(d) {
  data.frame(
    cohort = unique(d$cohort)[1],
    knees = nrow(d),
    patients = length(unique(d$patient_id)),
    total_events = sum(d$event_primary == 1, na.rm = TRUE),
    event_rate = mean(d$event_primary == 1, na.rm = TRUE),
    median_followup_months = median(d$time_months, na.rm = TRUE),
    median_event_time_months = median(d$time_months[d$event_primary == 1], na.rm = TRUE),
    events_12m = events_by_horizon(d, 12),
    events_24m = events_by_horizon(d, 24),
    events_36m = events_by_horizon(d, 36),
    events_60m = events_by_horizon(d, 60),
    censored_before_24m = censored_before(d, 24),
    censored_before_36m = censored_before(d, 36),
    censored_before_60m = censored_before(d, 60),
    at_risk_12m = at_risk_at(d, 12),
    at_risk_24m = at_risk_at(d, 24),
    at_risk_36m = at_risk_at(d, 36),
    at_risk_60m = at_risk_at(d, 60)
  )
}))

strict_rows <- list()
for (cutoff in c(0, 3, 6, 12)) {
  d <- mrkr
  if (cutoff > 0) d <- subset(d, !(event_primary == 1 & time_months <= cutoff))
  fit_slope <- coxph(Surv(time_months, event_primary) ~ lp_f_core, data = d)
  risk_recal <- predict_risk_from_fit(fit_slope, d, primary_horizon)
  strict_rows[[length(strict_rows) + 1]] <- data.frame(
    strict_definition = ifelse(cutoff == 0, "MRKR all", paste0("Exclude events <= ", cutoff, " months")),
    cutoff_months = cutoff,
    n_knees = nrow(d),
    n_patients = length(unique(d$patient_id)),
    total_events = sum(d$event_primary == 1),
    events_by_24m = events_by_horizon(d, primary_horizon),
    c_index = cindex_lp(d, d$lp_f_core),
    auc_24m = td_auc(d, d$lp_f_core, primary_horizon),
    observed_km_24m_risk = km_risk(d, primary_horizon),
    original_mean_predicted_24m_risk = mean(predict_risk_from_fit(fit_f_core, d, primary_horizon)),
    recalibrated_mean_predicted_24m_risk = mean(risk_recal),
    calibration_slope = coef(fit_slope)[1],
    calibration_slope_p_value = summary(fit_slope)$coefficients[1, "Pr(>|z|)"]
  )
}
strict_sensitivity <- do.call(rbind, strict_rows)

outcome_rows <- list()
mrkr_hardware <- mrkr
mrkr_cpt <- mrkr
mrkr_cpt$event_primary <- ifelse(is.na(mrkr_cpt$event_sensitivity), 0, mrkr_cpt$event_sensitivity)
mrkr_cpt$time_months <- mrkr_cpt$time_sensitivity_months
mrkr_cpt <- subset(mrkr_cpt, !is.na(time_months) & time_months > 0)
mrkr_combined <- make_combined_outcome(mrkr)
outcome_sets <- list(
  hardware_primary = mrkr_hardware,
  cpt_patient_level_sensitivity = mrkr_cpt,
  combined_hardware_or_cpt = mrkr_combined
)
for (nm in names(outcome_sets)) {
  d <- outcome_sets[[nm]]
  fit_slope <- coxph(Surv(time_months, event_primary) ~ lp_f_core, data = d)
  outcome_rows[[length(outcome_rows) + 1]] <- data.frame(
    outcome_version = nm,
    n_knees = nrow(d),
    n_patients = length(unique(d$patient_id)),
    total_events = sum(d$event_primary == 1, na.rm = TRUE),
    events_by_24m = events_by_horizon(d, primary_horizon),
    c_index = cindex_lp(d, d$lp_f_core),
    auc_24m = td_auc(d, d$lp_f_core, primary_horizon),
    observed_km_24m_risk = km_risk(d, primary_horizon),
    calibration_slope = coef(fit_slope)[1],
    note = ifelse(nm == "cpt_patient_level_sensitivity", "CPT outcome is patient-level, not side-specific.", "")
  )
}
outcome_sensitivity <- do.call(rbind, outcome_rows)

mrkr$risk_original_24m <- predict_risk_from_fit(fit_f_core, mrkr, primary_horizon)
mrkr$risk_recalibrated_24m <- predict_risk_from_fit(fit_mrkr_slope, mrkr, primary_horizon)
mrkr$risk_group_recalibrated_24m <- cut(
  mrkr$risk_recalibrated_24m,
  breaks = c(-Inf, 0.10, 0.25, 0.50, Inf),
  labels = c("<10%", "10-25%", "25-50%", ">50%")
)
risk_strata <- do.call(rbind, lapply(split(mrkr, mrkr$risk_group_recalibrated_24m, drop = TRUE), function(g) {
  data.frame(
    risk_group_recalibrated_24m = as.character(g$risk_group_recalibrated_24m[1]),
    n_knees = nrow(g),
    n_patients = length(unique(g$patient_id)),
    total_events = sum(g$event_primary == 1),
    events_by_24m = events_by_horizon(g, primary_horizon),
    mean_original_predicted_24m_risk = mean(g$risk_original_24m),
    mean_recalibrated_predicted_24m_risk = mean(g$risk_recalibrated_24m),
    observed_km_24m_risk = km_risk(g, primary_horizon)
  )
}))

write.csv(coef_table(fit_f_core, "OAI Model F-core"), file.path(results_tables, "oai_mrkr_plan_model_f_core_coefficients.csv"), row.names = FALSE)
write.csv(metrics, file.path(results_tables, "oai_mrkr_plan_transport_metrics_by_horizon.csv"), row.names = FALSE)
write.csv(calibration, file.path(results_tables, "oai_mrkr_plan_calibration_24m.csv"), row.names = FALSE)
write.csv(dca, file.path(results_tables, "oai_mrkr_plan_decision_curve_24m.csv"), row.names = FALSE)
write.csv(time_structure, file.path(results_tables, "oai_mrkr_plan_time_structure_table.csv"), row.names = FALSE)
write.csv(strict_sensitivity, file.path(results_tables, "oai_mrkr_plan_mrkr_strict_sensitivity_24m.csv"), row.names = FALSE)
write.csv(outcome_sensitivity, file.path(results_tables, "oai_mrkr_plan_mrkr_outcome_sensitivity_24m.csv"), row.names = FALSE)
write.csv(risk_strata, file.path(results_tables, "oai_mrkr_plan_mrkr_risk_strata_24m.csv"), row.names = FALSE)
write.csv(mrkr, file.path(derived_transport, "mrkr_validation_model_f_plan_predictions.csv"), row.names = FALSE)

report_path <- file.path(results_tables, "oai_mrkr_plan_reanalysis_report.txt")
capture.output({
  cat("OAI-MRKR transport validation reanalysis according to project plan\n\n")
  cat("Primary horizon:", primary_horizon, "months\n")
  cat("Model F-core: age + female + right_knee + cohort-specific pain_landmark_z + kl_baseline + kl_worsening\n\n")
  cat("OAI training set:", nrow(oai), "knees;", length(unique(oai$patient_id)), "patients;", sum(oai$event_primary), "events\n")
  cat("MRKR validation set:", nrow(mrkr), "knees;", length(unique(mrkr$patient_id)), "patients;", sum(mrkr$event_primary), "events\n\n")
  cat("Model F-core coefficients\n")
  print(coef_table(fit_f_core, "OAI Model F-core"))
  cat("\nMRKR calibration slope on OAI linear predictor\n")
  print(summary(fit_mrkr_slope)$coefficients)
  cat("\nMetrics by horizon\n")
  print(metrics)
  cat("\nTime structure\n")
  print(time_structure)
  cat("\nStrict sensitivity\n")
  print(strict_sensitivity)
  cat("\nOutcome sensitivity\n")
  print(outcome_sensitivity)
  cat("\nRisk strata\n")
  print(risk_strata)
}, file = report_path)

cat("Wrote OAI-MRKR project-plan reanalysis outputs.\n")
print(metrics[metrics$horizon_months == primary_horizon, ])
print(strict_sensitivity)
print(outcome_sensitivity)
