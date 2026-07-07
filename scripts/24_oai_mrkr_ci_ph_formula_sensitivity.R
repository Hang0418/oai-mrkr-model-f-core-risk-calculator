#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(survival)
})

args_file <- sub("--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])
script_dir <- if (is.na(args_file)) getwd() else dirname(normalizePath(args_file))
root <- normalizePath(file.path(script_dir, ".."))
derived <- file.path(root, "derived")
tables <- file.path(root, "results", "tables")
models <- file.path(root, "results", "models")
dir.create(tables, recursive = TRUE, showWarnings = FALSE)

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

cindex_lp <- function(data, lp, time_col = "time_months", event_col = "event_primary") {
  ok <- complete.cases(data[, c(time_col, event_col)]) & is.finite(lp)
  if (sum(data[[event_col]][ok] == 1) < 2) return(NA_real_)
  as.numeric(concordance(Surv(data[[time_col]][ok], data[[event_col]][ok]) ~ I(-lp[ok]))$concordance)
}

td_auc <- function(data, score, horizon, time_col = "time_months", event_col = "event_primary") {
  ok <- complete.cases(data[, c(time_col, event_col)]) & is.finite(score)
  d <- data[ok, ]
  score <- score[ok]
  y <- rep(NA_integer_, nrow(d))
  y[d[[event_col]] == 1 & d[[time_col]] <= horizon] <- 1
  y[d[[time_col]] > horizon] <- 0
  binary_auc(y, score)
}

bootstrap_ci <- function(data, lp, horizons = c(24), id_col = "patient_id", time_col = "time_months",
                         event_col = "event_primary", B = 500, seed = 20260707) {
  set.seed(seed)
  ids <- unique(data[[id_col]])
  out <- list()
  for (b in seq_len(B)) {
    sid <- sample(ids, length(ids), replace = TRUE)
    idx <- unlist(lapply(sid, function(id) which(data[[id_col]] == id)), use.names = FALSE)
    d <- data[idx, , drop = FALSE]
    lpb <- lp[idx]
    out[[length(out) + 1]] <- data.frame(metric = "c_index", horizon_months = 0L, estimate = cindex_lp(d, lpb, time_col, event_col))
    for (h in horizons) {
      out[[length(out) + 1]] <- data.frame(metric = "auc", horizon_months = h, estimate = td_auc(d, lpb, h, time_col, event_col))
    }
  }
  boot <- do.call(rbind, out)
  do.call(rbind, lapply(split(boot, interaction(boot$metric, boot$horizon_months, drop = TRUE), drop = TRUE), function(x) {
    data.frame(
      metric = x$metric[1],
      horizon_months = x$horizon_months[1],
      ci_lower_95 = unname(quantile(x$estimate, 0.025, na.rm = TRUE)),
      ci_upper_95 = unname(quantile(x$estimate, 0.975, na.rm = TRUE)),
      bootstrap_reps = B
    )
  }))
}

prepare_common <- function(df, cohort_name) {
  df$right_knee <- ifelse(df$side_label == "right", 1, 0)
  df$kl_worsening <- ifelse(df$kl_change >= 1, 1, 0)
  mu <- mean(df$pain_landmark_0_10, na.rm = TRUE)
  sig <- sd(df$pain_landmark_0_10, na.rm = TRUE)
  df$pain_landmark_z <- (df$pain_landmark_0_10 - mu) / sig
  df$cohort <- cohort_name
  attr(df, "pain_mean") <- mu
  attr(df, "pain_sd") <- sig
  df
}

predict_risk_from_fit <- function(model, newdata, horizon) {
  bh <- basehaz(model, centered = FALSE)
  h0 <- approx(bh$time, bh$hazard, xout = horizon, method = "constant", rule = 2, f = 0)$y
  lp <- predict(model, newdata = newdata, type = "lp", reference = "zero")
  pmin(pmax(1 - exp(-h0 * exp(lp)), 0), 1)
}

coef_ci <- function(model, name) {
  s <- summary(model)
  co <- as.data.frame(s$coefficients)
  ci <- as.data.frame(s$conf.int)
  data.frame(
    model = name,
    term = rownames(co),
    beta = co[, "coef"],
    hazard_ratio = ci[, "exp(coef)"],
    ci_lower_95 = ci[, "lower .95"],
    ci_upper_95 = ci[, "upper .95"],
    p_value = co[, "Pr(>|z|)"],
    row.names = NULL
  )
}

oai <- prepare_common(read_csv(file.path(derived, "transport", "oai_train_model_f_core.csv")), "OAI")
mrkr <- prepare_common(read_csv(file.path(derived, "transport", "mrkr_validation_model_f_core.csv")), "MRKR")

fit_f <- coxph(
  Surv(time_months, event_primary) ~ age + female + right_knee + pain_landmark_z +
    kl_baseline + kl_worsening + cluster(patient_id),
  data = oai,
  x = TRUE,
  model = TRUE
)
oai$lp_f <- predict(fit_f, newdata = oai, type = "lp", reference = "zero")
mrkr$lp_f <- predict(fit_f, newdata = mrkr, type = "lp", reference = "zero")
fit_recal <- coxph(Surv(time_months, event_primary) ~ lp_f, data = mrkr, x = TRUE, model = TRUE)

ci_rows <- list()
for (spec in list(
  list(label = "OAI Model F-core apparent", data = oai, lp = oai$lp_f),
  list(label = "MRKR original OAI-derived Model F-core", data = mrkr, lp = mrkr$lp_f)
)) {
  point <- data.frame(
    cohort_model = spec$label,
    metric = c("c_index", "auc", "auc", "auc"),
    horizon_months = c(0, 12, 24, 60),
    estimate = c(
      cindex_lp(spec$data, spec$lp),
      td_auc(spec$data, spec$lp, 12),
      td_auc(spec$data, spec$lp, 24),
      td_auc(spec$data, spec$lp, 60)
    )
  )
  ci <- bootstrap_ci(spec$data, spec$lp, horizons = c(12, 24, 60), B = 500)
  merged <- merge(point, ci, by = c("metric", "horizon_months"), all.x = TRUE)
  merged$cohort_model <- spec$label
  ci_rows[[length(ci_rows) + 1]] <- merged
}
perf_ci <- do.call(rbind, ci_rows)
perf_ci <- perf_ci[, c("cohort_model", "metric", "horizon_months", "estimate", "ci_lower_95", "ci_upper_95", "bootstrap_reps")]
write.csv(perf_ci, file.path(tables, "oai_mrkr_reviewer_discrimination_ci.csv"), row.names = FALSE)

bh <- basehaz(fit_f, centered = FALSE)
base_h <- data.frame(
  horizon_months = c(12, 24, 36, 60),
  baseline_cumulative_hazard = sapply(c(12, 24, 36, 60), function(h) {
    approx(bh$time, bh$hazard, xout = h, method = "constant", rule = 2, f = 0)$y
  })
)
write.csv(coef_ci(fit_f, "OAI Model F-core formula coefficients"), file.path(tables, "oai_mrkr_reviewer_model_f_formula_coefficients.csv"), row.names = FALSE)
write.csv(base_h, file.path(tables, "oai_mrkr_reviewer_model_f_baseline_hazard.csv"), row.names = FALSE)

standardization <- data.frame(
  cohort = c("OAI training", "MRKR validation"),
  pain_landmark_mean = c(attr(oai, "pain_mean"), attr(mrkr, "pain_mean")),
  pain_landmark_sd = c(attr(oai, "pain_sd"), attr(mrkr, "pain_sd")),
  note = "pain_landmark_z = (pain_landmark_0_10 - cohort mean) / cohort SD"
)
write.csv(standardization, file.path(tables, "oai_mrkr_reviewer_model_f_standardization.csv"), row.names = FALSE)

recal <- data.frame(
  model = "MRKR slope plus baseline recalibration",
  intercept_note = "Implemented as a Cox recalibration model fit in MRKR: Surv(time,event) ~ lp_f",
  slope = as.numeric(coef(fit_recal)[1]),
  baseline_cumulative_hazard_12m = approx(basehaz(fit_recal, centered = FALSE)$time, basehaz(fit_recal, centered = FALSE)$hazard, xout = 12, method = "constant", rule = 2, f = 0)$y,
  baseline_cumulative_hazard_24m = approx(basehaz(fit_recal, centered = FALSE)$time, basehaz(fit_recal, centered = FALSE)$hazard, xout = 24, method = "constant", rule = 2, f = 0)$y,
  baseline_cumulative_hazard_60m = approx(basehaz(fit_recal, centered = FALSE)$time, basehaz(fit_recal, centered = FALSE)$hazard, xout = 60, method = "constant", rule = 2, f = 0)$y
)
write.csv(recal, file.path(tables, "oai_mrkr_reviewer_recalibration_formula.csv"), row.names = FALSE)

model_e <- read_csv(file.path(derived, "validation", "oai_docx_plan_common_complete_dataset.csv"))
model_e$side <- ifelse(model_e$side == "right", 1, 0)
fit_e <- coxph(
  Surv(time, event) ~ age + female + bmi + side + pain_0 + function_0 + stiffness_0 +
    pain_change + function_change + kl_0 + kl_change + jsn_medial_0 + jsn_medial_change +
    jsn_lateral_0 + jsn_lateral_change + cluster(id),
  data = model_e,
  x = TRUE,
  model = TRUE
)
zph <- cox.zph(fit_e, transform = "km")
zph_table <- data.frame(
  term = rownames(zph$table),
  chisq = zph$table[, "chisq"],
  df = zph$table[, "df"],
  p_value = zph$table[, "p"],
  row.names = NULL
)
write.csv(zph_table, file.path(tables, "oai_mrkr_reviewer_model_e_schoenfeld_ph.csv"), row.names = FALSE)

model_e$log_time <- log(pmax(model_e$time, 0.1))
fit_e_tvc <- coxph(
  Surv(time, event) ~ age + female + bmi + side + pain_0 + function_0 + stiffness_0 +
    pain_change + function_change + kl_0 + kl_change + jsn_medial_0 + jsn_medial_change +
    jsn_lateral_0 + jsn_lateral_change +
    tt(age) + tt(pain_0) + tt(function_change) + tt(kl_0) + tt(kl_change) + tt(jsn_medial_0) +
    cluster(id),
  data = model_e,
  tt = function(x, t, ...) x * log(pmax(t, 0.1)),
  x = TRUE
)
coef_tvc <- coef_ci(fit_e_tvc, "Model E with prespecified time-varying coefficient terms")
write.csv(coef_tvc[grepl("^tt", coef_tvc$term), ], file.path(tables, "oai_mrkr_reviewer_model_e_time_varying_terms.csv"), row.names = FALSE)

model_e$lp_e <- predict(fit_e, newdata = model_e, type = "lp", reference = "zero")
model_e$lp_e_tvc <- predict(fit_e_tvc, newdata = model_e, type = "lp", reference = "zero")
ph_sensitivity <- data.frame(
  model = c("Original Model E Cox", "Model E with time-varying coefficient terms"),
  n_knees = nrow(model_e),
  events = sum(model_e$event == 1),
  c_index = c(cindex_lp(model_e, model_e$lp_e, "time", "event"), cindex_lp(model_e, model_e$lp_e_tvc, "time", "event")),
  auc_60m = c(td_auc(model_e, model_e$lp_e, 60, "time", "event"), td_auc(model_e, model_e$lp_e_tvc, 60, "time", "event"))
)
write.csv(ph_sensitivity, file.path(tables, "oai_mrkr_reviewer_model_e_ph_sensitivity_performance.csv"), row.names = FALSE)

cat("Wrote reviewer-requested CI, formula, recalibration, and PH sensitivity tables.\n")
