#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(survival)
})

args_file <- sub("--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])
script_dir <- if (is.na(args_file)) getwd() else dirname(normalizePath(args_file))
root <- normalizePath(file.path(script_dir, ".."))

derived_oai <- file.path(root, "derived", "OAI")
derived_mrkr <- file.path(root, "derived", "MRKR")
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
  if (sum(data$event[ok] == 1) < 2) return(NA_real_)
  as.numeric(concordance(Surv(time, event) ~ I(-lp), data = data[ok, ])$concordance)
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

td_auc <- function(data, score, t) {
  ok <- is.finite(score) & !is.na(data$time) & !is.na(data$event)
  d <- data[ok, ]
  score <- score[ok]
  y <- rep(NA_integer_, nrow(d))
  y[d$event == 1 & d$time <= t] <- 1
  y[d$time > t] <- 0
  binary_auc(y, score)
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

prepare_oai_model_f <- function() {
  df <- read_csv(file.path(derived_oai, "oai_24m_landmark_dataset.csv"))
  df <- subset(df, landmark_eligible_24m == 1 & time_from_landmark_months > 0)
  out <- data.frame(
    id = as.character(df$id),
    knee_id = paste("OAI", df$id, df$side, sep = "_"),
    cohort = "OAI",
    side = factor(df$side, levels = c("right", "left")),
    time = df$time_from_landmark_months,
    event = df$event_after_landmark,
    age = df$subject_v00age_num,
    female = ifelse(df$enrollee_p02sex_num == 2, 1, 0),
    pain_24_0_10 = df$womac_pain_24m / 2,
    kl_0 = df$xray_sq_v00xrkl_num,
    kl_change = df$xray_kl_delta_0_24m
  )
  out[complete.cases(out[, c("time", "event", "age", "female", "side", "pain_24_0_10", "kl_0", "kl_change")]), ]
}

prepare_mrkr_model_f <- function() {
  df <- read_csv(file.path(derived_mrkr, "mrkr_transport_knee_dataset.csv"))
  df <- subset(df, model_f_complete == 1 & time_hardware_months > 0)
  out <- data.frame(
    id = as.character(df$empi_anon),
    knee_id = df$knee_id,
    cohort = "MRKR",
    side = factor(df$side_label, levels = c("right", "left")),
    time = df$time_hardware_months,
    event = df$event_hardware_after_landmark,
    age = df$age,
    female = df$female,
    pain_24_0_10 = df$pain_24,
    kl_0 = df$kl_0,
    kl_change = df$kl_change,
    cpt_arthroplasty_after_landmark = df$cpt_arthroplasty_after_landmark,
    cpt_primary_tka_after_landmark = df$cpt_primary_tka_after_landmark
  )
  out[complete.cases(out[, c("time", "event", "age", "female", "side", "pain_24_0_10", "kl_0", "kl_change")]), ]
}

horizon <- 60
vars_f <- c("age", "female", "side", "pain_24_0_10", "kl_0", "kl_change")
oai <- prepare_oai_model_f()
mrkr <- prepare_mrkr_model_f()

fit_f <- coxph(
  as.formula(paste("Surv(time, event) ~", paste(vars_f, collapse = " + "), "+ cluster(id)")),
  data = oai,
  x = TRUE,
  model = TRUE
)
saveRDS(fit_f, file.path(results_models, "oai_mrkr_transport_model_f.rds"))

oai$lp_model_f <- predict(fit_f, newdata = oai, type = "lp", reference = "zero")
mrkr$lp_model_f <- predict(fit_f, newdata = mrkr, type = "lp", reference = "zero")
oai$risk60_model_f <- predict_risk(fit_f, oai, horizon)
mrkr$risk60_model_f <- predict_risk(fit_f, mrkr, horizon)

metrics <- data.frame(
  cohort = c("OAI apparent", "MRKR external primary hardware"),
  outcome = c("KR/TKA after OAI 24m landmark", "Side-specific arthroplasty hardware after MRKR landmark"),
  n_knees = c(nrow(oai), nrow(mrkr)),
  n_patients = c(length(unique(oai$id)), length(unique(mrkr$id))),
  events_total = c(sum(oai$event), sum(mrkr$event)),
  events_by_60m = c(sum(oai$event == 1 & oai$time <= horizon), sum(mrkr$event == 1 & mrkr$time <= horizon)),
  c_index = c(cindex_lp(oai, oai$lp_model_f), cindex_lp(mrkr, mrkr$lp_model_f)),
  auc_60m = c(td_auc(oai, oai$lp_model_f, horizon), td_auc(mrkr, mrkr$lp_model_f, horizon)),
  brier_60m = c(ipcw_brier(oai, oai$risk60_model_f, horizon), ipcw_brier(mrkr, mrkr$risk60_model_f, horizon)),
  mean_predicted_60m_risk = c(mean(oai$risk60_model_f), mean(mrkr$risk60_model_f)),
  observed_km_60m_risk = c(
    {
      s <- summary(survfit(Surv(time, event) ~ 1, data = oai), times = horizon, extend = TRUE)
      if (length(s$surv)) 1 - s$surv[1] else NA_real_
    },
    {
      s <- summary(survfit(Surv(time, event) ~ 1, data = mrkr), times = horizon, extend = TRUE)
      if (length(s$surv)) 1 - s$surv[1] else NA_real_
    }
  )
)

cpt_sensitivity <- data.frame(
  cohort = "MRKR external patient-level CPT sensitivity",
  n_knees = nrow(mrkr),
  n_patients = length(unique(mrkr$id)),
  cpt_arthroplasty_events = sum(mrkr$cpt_arthroplasty_after_landmark),
  cpt_primary_tka_events = sum(mrkr$cpt_primary_tka_after_landmark),
  auc_cpt_arthroplasty = binary_auc(mrkr$cpt_arthroplasty_after_landmark, mrkr$lp_model_f),
  auc_cpt_primary_tka = binary_auc(mrkr$cpt_primary_tka_after_landmark, mrkr$lp_model_f),
  note = "CPT outcomes are patient-level and not side-specific; use as sensitivity only."
)

write.csv(metrics, file.path(results_tables, "oai_mrkr_transport_model_f_metrics.csv"), row.names = FALSE)
write.csv(cpt_sensitivity, file.path(results_tables, "oai_mrkr_transport_model_f_cpt_sensitivity.csv"), row.names = FALSE)
write.csv(coef_table(fit_f, "Model F OAI-MRKR transport"), file.path(results_tables, "oai_mrkr_transport_model_f_coefficients.csv"), row.names = FALSE)
write.csv(
  rbind(
    calibration_table(oai, oai$risk60_model_f, horizon, label = "OAI apparent"),
    calibration_table(mrkr, mrkr$risk60_model_f, horizon, label = "MRKR external primary hardware")
  ),
  file.path(results_tables, "oai_mrkr_transport_model_f_calibration_60m.csv"),
  row.names = FALSE
)
write.csv(mrkr, file.path(derived_mrkr, "mrkr_transport_model_f_predictions.csv"), row.names = FALSE)

capture.output({
  cat("OAI-MRKR transport Model F validation\n\n")
  cat("Model F variables:", paste(vars_f, collapse = ", "), "\n")
  cat("OAI training knees:", nrow(oai), "patients:", length(unique(oai$id)), "events:", sum(oai$event), "\n")
  cat("MRKR validation knees:", nrow(mrkr), "patients:", length(unique(mrkr$id)), "hardware events:", sum(mrkr$event), "\n\n")
  print(metrics)
  cat("\nCPT sensitivity\n")
  print(cpt_sensitivity)
  cat("\nCoefficients\n")
  print(coef_table(fit_f, "Model F OAI-MRKR transport"))
}, file = file.path(results_tables, "oai_mrkr_transport_model_f_report.txt"))

cat("Wrote OAI-MRKR transport validation outputs.\n")
print(metrics)
print(cpt_sensitivity)
