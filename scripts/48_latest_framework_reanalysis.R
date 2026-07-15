#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(survival)
  library(data.table)
})

args_file <- sub("--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])
script_dir <- if (is.na(args_file)) getwd() else dirname(normalizePath(args_file))
root <- normalizePath(file.path(script_dir, ".."))
tables <- file.path(root, "results", "tables", "latest_framework")
dir.create(tables, recursive = TRUE, showWarnings = FALSE)

clamp <- function(x) pmin(pmax(x, 1e-6), 1 - 1e-6)
binary_auc <- function(y, score) {
  ok <- !is.na(y) & is.finite(score); y <- as.integer(y[ok]); score <- score[ok]
  n1 <- sum(y == 1); n0 <- sum(y == 0)
  if (n1 == 0 || n0 == 0) return(NA_real_)
  r <- rank(score, ties.method = "average")
  (sum(r[y == 1]) - n1 * (n1 + 1) / 2) / (n1 * n0)
}
cindex_lp <- function(time, event, score) {
  ok <- is.finite(time) & !is.na(event) & is.finite(score)
  as.numeric(concordance(Surv(time[ok], event[ok]) ~ I(-score[ok]))$concordance)
}
td_auc <- function(time, event, score, horizon) {
  y <- rep(NA_integer_, length(time))
  y[event == 1 & time <= horizon] <- 1L
  y[time > horizon] <- 0L
  binary_auc(y, score)
}
censor_surv <- function(time, event, at) {
  fit <- survfit(Surv(time, 1 - event) ~ 1)
  # Step-function interpolation is equivalent to repeated summary() calls but
  # avoids a costly survival-object traversal for every event time.
  pmax(approx(c(0, fit$time), c(1, fit$surv), xout = at,
              method = "constant", f = 0, rule = 2)$y, 1e-6)
}
ipcw_brier <- function(time, event, risk, horizon) {
  err <- rep(NA_real_, length(time))
  case <- event == 1 & time <= horizon
  control <- time > horizon
  if (any(case)) err[case] <- (1 - risk[case])^2 / censor_surv(time, event, time[case])
  if (any(control)) err[control] <- risk[control]^2 / censor_surv(time, event, horizon)[1]
  mean(err, na.rm = TRUE)
}
km_risk <- function(time, event, horizon) {
  sf <- summary(survfit(Surv(time, event) ~ 1), times = horizon, extend = TRUE)
  risk <- 1 - sf$surv[1]
  se <- sf$std.err[1]
  c(estimate = risk, lower = max(0, risk - 1.96 * se), upper = min(1, risk + 1.96 * se))
}
pred_risk <- function(fit, newdata, horizon) {
  bh <- basehaz(fit, centered = FALSE)
  h0 <- approx(bh$time, bh$hazard, xout = horizon, method = "constant", rule = 2, f = 0)$y
  lp <- predict(fit, newdata = newdata, type = "lp", reference = "zero")
  clamp(1 - exp(-h0 * exp(lp)))
}

# Strictly nested OAI Models A-E.
oai_path <- file.path(root, "derived", "validation", "oai_docx_plan_common_complete_dataset.csv")
oai <- read.csv(oai_path, stringsAsFactors = FALSE, check.names = TRUE)
oai$right_knee <- as.integer(oai$side == "right")
fml <- list(
  A = Surv(time, event) ~ age + female + bmi + right_knee,
  B = Surv(time, event) ~ age + female + bmi + right_knee + pain_0 + function_0 + stiffness_0,
  C = Surv(time, event) ~ age + female + bmi + right_knee + pain_0 + function_0 + stiffness_0 +
    kl_0 + jsn_medial_0 + jsn_lateral_0,
  D = Surv(time, event) ~ age + female + bmi + right_knee + pain_0 + function_0 + stiffness_0 +
    kl_0 + jsn_medial_0 + jsn_lateral_0 + pain_change + function_change,
  E = Surv(time, event) ~ age + female + bmi + right_knee + pain_0 + function_0 + stiffness_0 +
    kl_0 + jsn_medial_0 + jsn_lateral_0 + pain_change + function_change +
    kl_change + jsn_medial_change + jsn_lateral_change
)
fits <- lapply(fml, function(z) coxph(z, data = oai, x = TRUE, model = TRUE))
scores <- lapply(fits, predict, newdata = oai, type = "lp", reference = "zero")
risks60 <- lapply(fits, pred_risk, newdata = oai, horizon = 60)

apparent <- do.call(rbind, lapply(names(fits), function(nm) {
  fit <- fits[[nm]]; score <- scores[[nm]]; risk60 <- risks60[[nm]]
  data.frame(model = nm, n_knees = nrow(oai), n_patients = length(unique(oai$id)),
    events = sum(oai$event), parameters = length(coef(fit)),
    c_index = cindex_lp(oai$time, oai$event, score),
    auc_60m = td_auc(oai$time, oai$event, score, 60),
    brier_60m = ipcw_brier(oai$time, oai$event, risk60, 60),
    aic = AIC(fit), stringsAsFactors = FALSE)
}))

set.seed(20260720)
ids <- unique(oai$id); B_ci <- 500; B_opt <- 250
boot_fixed <- vector("list", B_ci)
for (b in seq_len(B_ci)) {
  sampled <- sample(ids, length(ids), replace = TRUE)
  idx <- unlist(lapply(sampled, function(z) which(oai$id == z)), use.names = FALSE)
  db <- oai[idx, ]
  boot_fixed[[b]] <- do.call(rbind, lapply(names(scores), function(nm) {
    sc <- scores[[nm]][idx]
    data.frame(iteration = b, model = nm,
      c_index = cindex_lp(db$time, db$event, sc),
      auc_60m = td_auc(db$time, db$event, sc, 60),
      brier_60m = ipcw_brier(db$time, db$event, risks60[[nm]][idx], 60))
  }))
}
boot_fixed <- do.call(rbind, boot_fixed)

set.seed(20260721)
optimism <- matrix(NA_real_, nrow = B_opt, ncol = length(fml), dimnames = list(NULL, names(fml)))
optimism_auc <- matrix(NA_real_, nrow = B_opt, ncol = length(fml), dimnames = list(NULL, names(fml)))
optimism_brier <- matrix(NA_real_, nrow = B_opt, ncol = length(fml), dimnames = list(NULL, names(fml)))
for (b in seq_len(B_opt)) {
  sampled <- sample(ids, length(ids), replace = TRUE)
  idx <- unlist(lapply(sampled, function(z) which(oai$id == z)), use.names = FALSE)
  db <- oai[idx, ]
  for (nm in names(fml)) {
    fb <- tryCatch(coxph(fml[[nm]], data = db, x = TRUE, model = TRUE), error = function(e) NULL)
    if (is.null(fb)) next
    sb <- predict(fb, newdata = db, type = "lp", reference = "zero")
    st <- predict(fb, newdata = oai, type = "lp", reference = "zero")
    optimism[b, nm] <- cindex_lp(db$time, db$event, sb) - cindex_lp(oai$time, oai$event, st)
    rb <- pred_risk(fb, db, 60)
    rt <- pred_risk(fb, oai, 60)
    optimism_auc[b, nm] <- td_auc(db$time, db$event, sb, 60) - td_auc(oai$time, oai$event, st, 60)
    # For prediction error, optimism is the increase in Brier score when the
    # bootstrap fit is applied back to the original OAI sample.
    optimism_brier[b, nm] <- ipcw_brier(oai$time, oai$event, rt, 60) -
      ipcw_brier(db$time, db$event, rb, 60)
  }
}

perf <- do.call(rbind, lapply(names(fml), function(nm) {
  z <- boot_fixed[boot_fixed$model == nm, ]
  a <- apparent[apparent$model == nm, ]
  opt_auc <- mean(optimism_auc[, nm], na.rm = TRUE)
  opt_brier <- mean(optimism_brier[, nm], na.rm = TRUE)
  data.frame(a,
    c_index_lower_95 = quantile(z$c_index, .025, na.rm = TRUE),
    c_index_upper_95 = quantile(z$c_index, .975, na.rm = TRUE),
    optimism_c = mean(optimism[, nm], na.rm = TRUE),
    optimism_corrected_c = a$c_index - mean(optimism[, nm], na.rm = TRUE),
    auc_60m_lower_95 = quantile(z$auc_60m, .025, na.rm = TRUE),
    auc_60m_upper_95 = quantile(z$auc_60m, .975, na.rm = TRUE),
    optimism_auc_60m = opt_auc,
    optimism_corrected_auc_60m = a$auc_60m - opt_auc,
    corrected_auc_60m_lower_95 = quantile(z$auc_60m, .025, na.rm = TRUE) - opt_auc,
    corrected_auc_60m_upper_95 = quantile(z$auc_60m, .975, na.rm = TRUE) - opt_auc,
    optimism_brier_60m = opt_brier,
    optimism_corrected_brier_60m = a$brier_60m + opt_brier,
    corrected_brier_60m_lower_95 = quantile(z$brier_60m, .025, na.rm = TRUE) + opt_brier,
    corrected_brier_60m_upper_95 = quantile(z$brier_60m, .975, na.rm = TRUE) + opt_brier)
}))

comparisons <- data.frame()
seq_pairs <- list(c("A", "B"), c("B", "C"), c("C", "D"), c("D", "E"), c("C", "E"))
for (pair in seq_pairs) {
  small <- pair[1]; large <- pair[2]
  lr <- 2 * (as.numeric(logLik(fits[[large]])) - as.numeric(logLik(fits[[small]])))
  df <- attr(logLik(fits[[large]]), "df") - attr(logLik(fits[[small]]), "df")
  bs <- merge(boot_fixed[boot_fixed$model == small, ], boot_fixed[boot_fixed$model == large, ],
              by = "iteration", suffixes = c("_small", "_large"))
  dc <- bs$c_index_large - bs$c_index_small
  da <- bs$auc_60m_large - bs$auc_60m_small
  comparisons <- rbind(comparisons, data.frame(
    comparison = paste0("Model ", large, " vs ", small),
    delta_c_index = perf$c_index[perf$model == large] - perf$c_index[perf$model == small],
    delta_c_lower_95 = quantile(dc, .025, na.rm = TRUE), delta_c_upper_95 = quantile(dc, .975, na.rm = TRUE),
    delta_auc_60m = perf$auc_60m[perf$model == large] - perf$auc_60m[perf$model == small],
    delta_auc_lower_95 = quantile(da, .025, na.rm = TRUE), delta_auc_upper_95 = quantile(da, .975, na.rm = TRUE),
    lr_chisq = lr, df = df, p_value = pchisq(lr, df, lower.tail = FALSE)))
}

# Model E horizon performance with patient-clustered bootstrap intervals.
horizons <- c(12, 24, 36, 60)
e_h <- do.call(rbind, lapply(horizons, function(h) {
  auc_boot <- numeric(B_ci)
  for (b in seq_len(B_ci)) {
    sampled <- sample(ids, length(ids), replace = TRUE)
    idx <- unlist(lapply(sampled, function(z) which(oai$id == z)), use.names = FALSE)
    auc_boot[b] <- td_auc(oai$time[idx], oai$event[idx], scores$E[idx], h)
  }
  data.frame(horizon_months = h, auc = td_auc(oai$time, oai$event, scores$E, h),
    lower_95 = quantile(auc_boot, .025, na.rm = TRUE), upper_95 = quantile(auc_boot, .975, na.rm = TRUE),
    events = sum(oai$event == 1 & oai$time <= h), at_risk = sum(oai$time >= h))
}))

oai$risk_e_60m <- pred_risk(fits$E, oai, 60)
oai$risk_quartile <- cut(oai$risk_e_60m, quantile(oai$risk_e_60m, 0:4/4), include.lowest = TRUE,
                         labels = paste0("Q", 1:4))
write.csv(oai[, c("id", "knee_id", "time", "event", "risk_e_60m", "risk_quartile")],
          file.path(tables, "latest_oai_model_e_risk_predictions.csv"), row.names = FALSE)
write.csv(perf, file.path(tables, "latest_oai_staged_nested_performance.csv"), row.names = FALSE)
write.csv(comparisons, file.path(tables, "latest_oai_incremental_comparisons.csv"), row.names = FALSE)
write.csv(e_h, file.path(tables, "latest_oai_model_e_horizon_auc.csv"), row.names = FALSE)

# MRKR interval construction from original image metadata.
mrkr <- read.csv(file.path(root, "derived", "transport", "mrkr_validation_model_f_core.csv"),
                 stringsAsFactors = FALSE, check.names = TRUE)
mrkr$right_knee <- as.integer(mrkr$side_label == "right")
mrkr$kl_worsening <- as.integer(mrkr$kl_change >= 1)
oai_f <- read.csv(file.path(root, "derived", "transport", "oai_train_model_f_core.csv"), stringsAsFactors = FALSE)
oai_f$right_knee <- as.integer(oai_f$side_label == "right")
oai_f$kl_worsening <- as.integer(oai_f$kl_change >= 1)
pain_mean <- mean(oai_f$pain_landmark_0_10); pain_sd <- sd(oai_f$pain_landmark_0_10)
oai_f$pain_landmark_z <- (oai_f$pain_landmark_0_10 - pain_mean) / pain_sd
mrkr$pain_landmark_z <- (mrkr$pain_landmark_0_10 - mean(mrkr$pain_landmark_0_10)) /
  sd(mrkr$pain_landmark_0_10)
fit_f <- coxph(Surv(time_months, event_primary) ~ age + female + right_knee + pain_landmark_z +
                 kl_baseline + kl_worsening, data = oai_f, x = TRUE, model = TRUE)
mrkr$lp_f <- predict(fit_f, newdata = mrkr, type = "lp", reference = "zero")
mrkr$risk_original_24m <- pred_risk(fit_f, mrkr, 24)

events <- fread(file.path(tables, "latest_mrkr_hardware_detection_intervals.csv"))

ev_idx <- match(mrkr$knee_id, events$knee_id)
left <- ifelse(mrkr$event_primary == 1, events$interval_left_months[ev_idx], mrkr$time_months)
right <- ifelse(mrkr$event_primary == 1, events$interval_right_months[ev_idx], Inf)
mid <- ifelse(mrkr$event_primary == 1, (left + right) / 2, mrkr$time_months)
hybrid <- mrkr$time_months
use_cpt <- mrkr$event_primary == 1 & !is.na(events$cpt_within_interval_90[ev_idx]) & events$cpt_within_interval_90[ev_idx]
hybrid[use_cpt] <- events$cpt_months[ev_idx][use_cpt]

metric_exact <- function(label, time, event, score = mrkr$lp_f, risk = mrkr$risk_original_24m) {
  km <- km_risk(time, event, 24)
  data.frame(definition = label, n_knees = length(time), total_events = sum(event),
    events_by_24m = sum(event == 1 & time <= 24),
    c_index = cindex_lp(time, event, score), auc_24m = td_auc(time, event, score, 24),
    observed_24m = km["estimate"], observed_lower_95 = km["lower"], observed_upper_95 = km["upper"],
    brier_24m = ipcw_brier(time, event, risk, 24), timing_note = "Exact/right-censored analysis")
}
timing <- rbind(
  metric_exact("First hardware-positive image (right endpoint)", mrkr$time_months, mrkr$event_primary),
  metric_exact("Hardware-anchored; CPT-timed within the detection interval and +/-90 days", hybrid, mrkr$event_primary),
  metric_exact("Midpoint of last-negative to first-positive interval", mid, mrkr$event_primary)
)

# Parametric Weibull interval-censored sensitivity; fixed-horizon AUC/Brier use
# only knees whose 24-month status is identified by the censoring interval.
ic <- data.frame(left = left, right = right, lp_f = mrkr$lp_f)
ic_fit <- survreg(Surv(left, right, type = "interval2") ~ lp_f, data = ic, dist = "weibull")
mu <- predict(ic_fit, newdata = ic, type = "lp")
ic_risk24 <- clamp(1 - exp(-((24 / exp(mu))^(1 / ic_fit$scale))))
known_y <- rep(NA_integer_, nrow(ic))
known_y[is.finite(ic$right) & ic$right <= 24] <- 1L
known_y[ic$left > 24] <- 0L
ic_auc <- binary_auc(known_y, ic_risk24)
ic_brier <- mean((known_y - ic_risk24)^2, na.rm = TRUE)
timing <- rbind(timing, data.frame(
  definition = "Weibull interval-censored model", n_knees = nrow(ic),
  total_events = sum(mrkr$event_primary), events_by_24m = sum(is.finite(right) & right <= 24),
  c_index = NA_real_, auc_24m = ic_auc, observed_24m = mean(ic_risk24),
  observed_lower_95 = NA_real_, observed_upper_95 = NA_real_, brier_24m = ic_brier,
  timing_note = paste0("Model-based risk; AUC/Brier among ", sum(!is.na(known_y)),
                       " knees with interval-identified 24-month status")))

# Clustered bootstrap intervals for exact timing definitions.
set.seed(20260722)
mr_ids <- unique(mrkr$patient_id); B_m <- 300
boot_t <- vector("list", B_m)
boot_h <- vector("list", B_m)
for (b in seq_len(B_m)) {
  sampled <- sample(mr_ids, length(mr_ids), replace = TRUE)
  idx <- unlist(lapply(sampled, function(z) which(mrkr$patient_id == z)), use.names = FALSE)
  defs <- list(right = mrkr$time_months, hybrid = hybrid, midpoint = mid)
  boot_t[[b]] <- do.call(rbind, lapply(names(defs), function(nm) data.frame(
    iteration = b, definition_key = nm,
    auc_24m = td_auc(defs[[nm]][idx], mrkr$event_primary[idx], mrkr$lp_f[idx], 24))))
  boot_h[[b]] <- do.call(rbind, lapply(c(12, 24, 36, 60), function(h) data.frame(
    iteration = b, horizon_months = h,
    auc = td_auc(mrkr$time_months[idx], mrkr$event_primary[idx], mrkr$lp_f[idx], h))))
}
boot_t <- do.call(rbind, boot_t)
boot_h <- do.call(rbind, boot_h)
keys <- c("right", "hybrid", "midpoint")
timing$auc_lower_95 <- NA_real_; timing$auc_upper_95 <- NA_real_
for (i in seq_along(keys)) {
  z <- boot_t$auc_24m[boot_t$definition_key == keys[i]]
  timing$auc_lower_95[i] <- quantile(z, .025, na.rm = TRUE)
  timing$auc_upper_95[i] <- quantile(z, .975, na.rm = TRUE)
}

interval_summary <- data.frame(
  statistic = c("Events with reconstructed interval", "Median interval, days", "IQR lower, days", "IQR upper, days",
                "Intervals >365 days", "Intervals crossing 24-month horizon", "CPT dates used in hybrid analysis"),
  value = c(nrow(events), median(events$interval_right_months - events$interval_left_months) * 30.4375,
            quantile(events$interval_right_months - events$interval_left_months, .25) * 30.4375,
            quantile(events$interval_right_months - events$interval_left_months, .75) * 30.4375,
            sum((events$interval_right_months - events$interval_left_months) * 30.4375 > 365 + 1e-6),
            sum(events$interval_left_months < 24 & events$interval_right_months > 24),
            sum(events$cpt_within_interval_90, na.rm = TRUE)))
write.csv(timing, file.path(tables, "latest_mrkr_timing_sensitivity.csv"), row.names = FALSE)
write.csv(interval_summary, file.path(tables, "latest_mrkr_interval_summary.csv"), row.names = FALSE)
mrkr_horizon <- do.call(rbind, lapply(c(12, 24, 36, 60), function(h) {
  z <- boot_h$auc[boot_h$horizon_months == h]
  data.frame(horizon_months = h,
    auc = td_auc(mrkr$time_months, mrkr$event_primary, mrkr$lp_f, h),
    lower_95 = quantile(z, .025, na.rm = TRUE), upper_95 = quantile(z, .975, na.rm = TRUE),
    events = sum(mrkr$event_primary == 1 & mrkr$time_months <= h),
    at_risk = sum(mrkr$time_months >= h))
}))
write.csv(mrkr_horizon, file.path(tables, "latest_mrkr_horizon_auc.csv"), row.names = FALSE)

cat("Strictly nested OAI performance\n"); print(perf)
cat("\nIncremental comparisons\n"); print(comparisons)
cat("\nMRKR timing sensitivity\n"); print(timing)
cat("\nInterval summary\n"); print(interval_summary)
