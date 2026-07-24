#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(survival)
})

args_file <- sub("--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])
script_dir <- if (is.na(args_file)) getwd() else dirname(normalizePath(args_file))
root <- normalizePath(file.path(script_dir, ".."))
derived <- file.path(root, "derived")
tables <- file.path(root, "results", "tables")
latest <- file.path(tables, "latest_framework")
dir.create(latest, recursive = TRUE, showWarnings = FALSE)

clamp <- function(x, lo = 1e-8, hi = 1 - 1e-8) pmin(pmax(x, lo), hi)

binary_auc <- function(y, score) {
  ok <- !is.na(y) & is.finite(score)
  y <- as.integer(y[ok] == 1); score <- score[ok]
  n1 <- sum(y == 1); n0 <- sum(y == 0)
  if (n1 == 0 || n0 == 0) return(NA_real_)
  ranks <- rank(score, ties.method = "average")
  (sum(ranks[y == 1]) - n1 * (n1 + 1) / 2) / (n1 * n0)
}

td_auc <- function(time, event, score, horizon) {
  y <- rep(NA_integer_, length(time))
  y[event == 1 & time <= horizon] <- 1L
  y[time > horizon] <- 0L
  binary_auc(y, score)
}

censor_surv <- function(time, event, at) {
  fit <- survfit(Surv(time, 1 - event) ~ 1)
  vapply(at, function(tt) {
    s <- summary(fit, times = tt, extend = TRUE)$surv
    if (length(s)) max(s[1], 1e-6) else 1
  }, numeric(1))
}

ipcw_brier <- function(time, event, risk, horizon) {
  err <- rep(NA_real_, length(time))
  case <- event == 1 & time <= horizon
  control <- time > horizon
  if (any(case)) err[case] <- (1 - risk[case])^2 / censor_surv(time, event, time[case])
  if (any(control)) err[control] <- risk[control]^2 / censor_surv(time, event, horizon)[1]
  mean(err, na.rm = TRUE)
}

km_summary <- function(time, event, horizon) {
  s <- summary(survfit(Surv(time, event) ~ 1, conf.type = "log-log"), times = horizon, extend = TRUE)
  c(risk = 1 - s$surv[1], lower = 1 - s$upper[1], upper = 1 - s$lower[1])
}

prepare <- function(d, pain_mean = NULL, pain_sd = NULL) {
  d$right_knee <- as.integer(d$side_label == "right")
  d$kl_worsening <- as.integer(d$kl_change >= 1)
  if (is.null(pain_mean)) pain_mean <- mean(d$pain_landmark_0_10)
  if (is.null(pain_sd)) pain_sd <- sd(d$pain_landmark_0_10)
  d$pain_landmark_z <- (d$pain_landmark_0_10 - pain_mean) / pain_sd
  d
}

predict_risk <- function(fit, newdata, horizon) {
  bh <- basehaz(fit, centered = FALSE)
  h0 <- approx(bh$time, bh$hazard, xout = horizon, method = "constant", rule = 2, f = 0)$y
  lp <- predict(fit, newdata = newdata, type = "lp", reference = "zero")
  clamp(1 - exp(-h0 * exp(lp)))
}

oai_raw <- read.csv(file.path(derived, "transport", "oai_train_model_f_core.csv"), stringsAsFactors = FALSE)
mrkr_raw <- read.csv(file.path(derived, "transport", "mrkr_validation_model_f_core.csv"), stringsAsFactors = FALSE)
oai <- prepare(oai_raw)
mrkr <- prepare(mrkr_raw)
fit_f <- coxph(Surv(time_months, event_primary) ~ age + female + right_knee + pain_landmark_z +
                 kl_baseline + kl_worsening + cluster(patient_id), data = oai, x = TRUE, model = TRUE)
mrkr$lp_f <- predict(fit_f, newdata = mrkr, type = "lp", reference = "zero")
fit_update <- coxph(Surv(time_months, event_primary) ~ lp_f, data = mrkr, x = TRUE, model = TRUE)

horizons <- c(12, 24, 36, 60)
secondary <- do.call(rbind, lapply(horizons, function(h) {
  obs <- km_summary(mrkr$time_months, mrkr$event_primary, h)
  r0 <- predict_risk(fit_f, mrkr, h)
  r1 <- predict_risk(fit_update, mrkr, h)
  data.frame(
    horizon_months = h,
    at_risk = sum(mrkr$time_months >= h),
    events = sum(mrkr$event_primary == 1 & mrkr$time_months <= h),
    censored_before_horizon = sum(mrkr$event_primary == 0 & mrkr$time_months < h),
    observed_risk = obs["risk"], observed_lower_95 = obs["lower"], observed_upper_95 = obs["upper"],
    analysis = c("Original transport", "Apparent slope+baseline recalibration"),
    mean_predicted_risk = c(mean(r0), mean(r1)),
    brier = c(ipcw_brier(mrkr$time_months, mrkr$event_primary, r0, h),
              ipcw_brier(mrkr$time_months, mrkr$event_primary, r1, h))
  )
}))
write.csv(secondary, file.path(latest, "revised_supplementary_mrkr_secondary_horizons.csv"), row.names = FALSE)

followup <- do.call(rbind, lapply(list(OAI = oai, MRKR = mrkr), function(d) {
  cohort <- if (identical(d, oai)) "OAI" else "MRKR"
  do.call(rbind, lapply(horizons, function(h) {
    obs <- km_summary(d$time_months, d$event_primary, h)
    data.frame(cohort = cohort, horizon_months = h, at_risk = sum(d$time_months >= h),
      cumulative_events = sum(d$event_primary == 1 & d$time_months <= h),
      censored_before_horizon = sum(d$event_primary == 0 & d$time_months < h),
      observed_risk = obs["risk"], lower_95 = obs["lower"], upper_95 = obs["upper"])
  }))
}))
write.csv(followup, file.path(latest, "revised_supplementary_followup_horizons.csv"), row.names = FALSE)

# Patient-clustered subgroup AUC intervals.
enriched <- read.csv(file.path(derived, "MRKR", "mrkr_transport_knee_dataset_enriched.csv"), stringsAsFactors = FALSE)
keep <- c("knee_id", "race", "knee_oa_dx_before_landmark", "oa_enriched_kl2",
          "oa_enriched_kl2_or_dx", "oa_enriched_pain_present", "high_quality_landmark")
mr <- merge(mrkr, enriched[, keep], by = "knee_id", all.x = TRUE, suffixes = c("", "_enriched"))
if ("race_enriched" %in% names(mr)) mr$race <- ifelse(is.na(mr$race) | mr$race == "", mr$race_enriched, mr$race)
groups <- list(
  "All MRKR core" = rep(TRUE, nrow(mr)),
  "OA enriched: baseline KL>=2" = mr$oa_enriched_kl2 == 1,
  "OA enriched: knee OA ICD before landmark" = mr$knee_oa_dx_before_landmark == 1,
  "OA enriched: KL>=2 or OA ICD" = mr$oa_enriched_kl2_or_dx == 1,
  "Pain-present at landmark" = mr$oa_enriched_pain_present == 1,
  "High-quality landmark/pain window" = mr$high_quality_landmark == 1,
  "Female" = mr$female == 1, "Male" = mr$female == 0,
  "Age <60 years" = mr$age < 60, "Age 60-69 years" = mr$age >= 60 & mr$age < 70,
  "Age >=70 years" = mr$age >= 70,
  "Baseline KL 0-1" = mr$kl_baseline < 2, "Baseline KL 2" = mr$kl_baseline == 2,
  "Baseline KL 3-4" = mr$kl_baseline >= 3
)
for (race_name in names(sort(table(mr$race), decreasing = TRUE))[1:4]) {
  groups[[paste0("Race: ", race_name)]] <- mr$race == race_name
}
set.seed(20260715)
B <- 300
sub_rows <- lapply(names(groups), function(nm) {
  d <- mr[which(groups[[nm]] %in% TRUE), ]
  estimate <- td_auc(d$time_months, d$event_primary, d$lp_f, 24)
  ids <- unique(d$patient_id)
  boots <- replicate(B, {
    sampled <- sample(ids, length(ids), replace = TRUE)
    idx <- unlist(lapply(sampled, function(z) which(d$patient_id == z)), use.names = FALSE)
    td_auc(d$time_months[idx], d$event_primary[idx], d$lp_f[idx], 24)
  })
  data.frame(subgroup = nm, n_knees = nrow(d), n_patients = length(ids),
    events_by_24m = sum(d$event_primary == 1 & d$time_months <= 24), auc_24m = estimate,
    lower_95 = quantile(boots, .025, na.rm = TRUE), upper_95 = quantile(boots, .975, na.rm = TRUE))
})
write.csv(do.call(rbind, sub_rows), file.path(latest, "revised_supplementary_mrkr_subgroup_auc.csv"), row.names = FALSE)

# CHECK fixed-horizon uncertainty and calibration summary.
check <- read.csv(file.path(derived, "validation", "check_24m_external_tka_dataset.csv"), stringsAsFactors = FALSE)
fit_check <- readRDS(file.path(root, "results", "models", "cox_oai_24m_common_change.rds"))
check_risk <- predict_risk(fit_check, check, 60)
check_obs <- km_summary(check$time, check$event, 60)
mean_pred <- mean(check_risk)
oe <- check_obs["risk"] / mean_pred
cal_intercept <- log(-log(1 - clamp(check_obs["risk"]))) - log(-log(1 - clamp(mean_pred)))
check_summary <- data.frame(
  cohort = "CHECK exploratory validation", knees = nrow(check), participants = length(unique(check$id)),
  events_60m = sum(check$event == 1 & check$time <= 60), mean_predicted_60m = mean_pred,
  observed_60m = check_obs["risk"], observed_lower_95 = check_obs["lower"], observed_upper_95 = check_obs["upper"],
  oe_ratio = oe, oe_lower_95 = check_obs["lower"] / mean_pred, oe_upper_95 = check_obs["upper"] / mean_pred,
  calibration_in_the_large = cal_intercept, predicted_min = min(check_risk), predicted_max = max(check_risk)
)
write.csv(check_summary, file.path(latest, "revised_supplementary_check_calibration.csv"), row.names = FALSE)

cat("Wrote supplementary consistency-audit tables to", latest, "\n")
