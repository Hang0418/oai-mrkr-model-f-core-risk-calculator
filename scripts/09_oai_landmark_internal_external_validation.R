#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(survival)
  library(ggplot2)
})

args_file <- sub("--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])
script_dir <- if (is.na(args_file)) getwd() else dirname(normalizePath(args_file))
root <- normalizePath(file.path(script_dir, ".."))

derived_oai <- file.path(root, "derived", "OAI")
derived_check <- file.path(root, "derived", "CHECK")
derived_validation <- file.path(root, "derived", "validation")
results_tables <- file.path(root, "results", "tables")
results_figures <- file.path(root, "results", "figures")
results_models <- file.path(root, "results", "models")

dir.create(derived_validation, recursive = TRUE, showWarnings = FALSE)
dir.create(results_tables, recursive = TRUE, showWarnings = FALSE)
dir.create(results_figures, recursive = TRUE, showWarnings = FALSE)
dir.create(results_models, recursive = TRUE, showWarnings = FALSE)

horizon_months <- 60
set.seed(20260618)

read_csv <- function(path) {
  read.csv(path, stringsAsFactors = FALSE, check.names = TRUE)
}

fmt_p <- function(x) {
  ifelse(is.na(x), NA_character_, ifelse(x < 0.001, "<0.001", sprintf("%.3f", x)))
}

prepare_oai <- function() {
  df <- read_csv(file.path(derived_oai, "oai_24m_landmark_dataset.csv"))
  df <- subset(df, landmark_complete_core_24m == 1)
  out <- data.frame(
    cohort = "OAI",
    id = as.character(df$id),
    knee_id = paste("OAI", df$id, df$side, sep = "_"),
    side = df$side,
    time = df$time_from_landmark_months,
    event = df$event_after_landmark,
    age = df$subject_v00age_num,
    female = ifelse(df$enrollee_p02sex_num == 2, 1, 0),
    bmi = df$clinical00_p01bmi_num,
    right_knee = ifelse(df$side == "right", 1, 0),
    prior_knee_injury = df$baseline_prior_knee_injury_num,
    prior_knee_surgery = df$baseline_prior_knee_surgery_num,
    womac_pain_24m = df$womac_pain_24m,
    womac_pain_delta_0_24m = df$womac_pain_delta_0_24m,
    womac_function_24m = df$womac_function_24m,
    womac_function_delta_0_24m = df$womac_function_delta_0_24m,
    kl_24m = df$xray_kl_current_24m,
    kl_delta_0_24m = df$xray_kl_delta_0_24m,
    jsn_medial_24m = df$xray_jsn_medial_current_24m,
    jsn_medial_delta_0_24m = df$xray_jsn_medial_delta_0_24m,
    pain_trajectory = df$pain_trajectory_rule_0_24m
  )
  out <- out[is.finite(out$time) & out$time > 0, ]
  out$pain_trajectory <- factor(
    out$pain_trajectory,
    levels = c("low_stable", "moderate_stable", "worsening", "high_persistent", "improving", "missing")
  )
  out
}

prepare_check <- function() {
  knee <- read_csv(file.path(derived_check, "check_knee_level_first_pass.csv"))
  long <- read_csv(file.path(derived_check, "check_pain_trajectory_long.csv"))
  t0 <- subset(long, visit == 0)
  t2 <- subset(long, visit == 2)
  keep0 <- c("knee_id", "womac_pain", "womac_function")
  keep2 <- c("knee_id", "womac_pain", "womac_function")
  names(t0)[match(keep0[-1], names(t0))] <- paste0(keep0[-1], "_0m")
  names(t2)[match(keep2[-1], names(t2))] <- paste0(keep2[-1], "_24m")
  sx <- merge(t0[, c("knee_id", "womac_pain_0m", "womac_function_0m")],
              t2[, c("knee_id", "womac_pain_24m", "womac_function_24m")],
              by = "knee_id", all = TRUE)
  df <- merge(knee, sx, by = "knee_id", all.x = TRUE)

  event_after <- ifelse(df$tka_through_t8 == 1 & !is.na(df$tka_month) & df$tka_month > 24, 1, 0)
  event_time <- ifelse(event_after == 1, df$tka_month - 24, 72)
  out <- data.frame(
    cohort = "CHECK",
    id = as.character(df$nsin),
    knee_id = df$knee_id,
    side = df$side,
    time = event_time,
    event = event_after,
    age = df$baseline_age,
    female = ifelse(df$sex_code == 2, 1, 0),
    bmi = df$baseline_bmi,
    right_knee = ifelse(df$side == "right", 1, 0),
    womac_pain_24m = df$womac_pain_24m,
    womac_pain_delta_0_24m = df$womac_pain_24m - df$womac_pain_0m,
    womac_function_24m = df$womac_function_24m,
    womac_function_delta_0_24m = df$womac_function_24m - df$womac_function_0m,
    kl_24m = df$kl_t2,
    kl_delta_0_24m = df$kl_t2 - df$kl_t0,
    jsn_medial_24m = df$jsn_medial_t2,
    jsn_medial_delta_0_24m = df$jsn_medial_t2 - df$jsn_medial_t0,
    kl_progression_t0_t5 = df$kl_progression_t0_t5,
    kl_progression_t0_t8 = df$kl_progression_t0_t8,
    medial_jsn_progression_t0_t5 = df$medial_jsn_progression_t0_t5,
    medial_jsn_progression_t0_t8 = df$medial_jsn_progression_t0_t8
  )
  out <- subset(out, is.na(time) | time > 0)
  out
}

complete_model_frame <- function(df, vars) {
  df[complete.cases(df[, c("time", "event", vars)]), ]
}

common_vars <- c(
  "age", "female", "bmi", "right_knee",
  "womac_pain_24m", "womac_pain_delta_0_24m",
  "womac_function_24m", "womac_function_delta_0_24m",
  "kl_24m", "kl_delta_0_24m",
  "jsn_medial_24m", "jsn_medial_delta_0_24m"
)

full_vars <- c(
  common_vars,
  "prior_knee_injury", "prior_knee_surgery"
)

common_formula <- as.formula(paste("Surv(time, event) ~", paste(common_vars, collapse = " + "), "+ cluster(id)"))
full_formula <- as.formula(paste("Surv(time, event) ~", paste(full_vars, collapse = " + "), "+ cluster(id)"))

fit_model <- function(formula, data) {
  coxph(formula, data = data, x = TRUE, model = TRUE)
}

cindex_lp <- function(data, lp) {
  cc <- complete.cases(data[, c("time", "event")]) & is.finite(lp)
  if (sum(data$event[cc]) < 2) return(NA_real_)
  as.numeric(concordance(Surv(time, event) ~ I(-lp), data = data[cc, ])$concordance)
}

predict_risk <- function(model, newdata, horizon) {
  bh <- basehaz(model, centered = FALSE)
  if (nrow(bh) == 0) return(rep(NA_real_, nrow(newdata)))
  h0 <- approx(bh$time, bh$hazard, xout = horizon, method = "constant", rule = 2, f = 0)$y
  lp <- predict(model, newdata = newdata, type = "lp", reference = "zero")
  risk <- 1 - exp(-h0 * exp(lp))
  pmin(pmax(as.numeric(risk), 0), 1)
}

calibration_table <- function(data, risk, horizon, groups = 10, label = "") {
  ok <- complete.cases(data[, c("time", "event")]) & is.finite(risk)
  d <- data[ok, ]
  d$risk <- risk[ok]
  cuts <- unique(quantile(d$risk, probs = seq(0, 1, length.out = groups + 1), na.rm = TRUE))
  if (length(cuts) <= 2) {
    d$risk_group <- 1
  } else {
    d$risk_group <- cut(d$risk, breaks = cuts, include.lowest = TRUE, labels = FALSE)
  }
  rows <- lapply(split(d, d$risk_group), function(g) {
    fit <- survfit(Surv(time, event) ~ 1, data = g)
    s <- summary(fit, times = horizon, extend = TRUE)
    obs <- if (length(s$surv)) 1 - s$surv[1] else NA_real_
    obs_se <- if (length(s$std.err)) s$std.err[1] else NA_real_
    data.frame(
      validation = label,
      group = as.integer(g$risk_group[1]),
      n = nrow(g),
      events = sum(g$event == 1 & g$time <= horizon, na.rm = TRUE),
      mean_predicted_risk = mean(g$risk, na.rm = TRUE),
      observed_km_risk = obs,
      observed_km_se = obs_se
    )
  })
  do.call(rbind, rows)
}

decision_curve <- function(data, risk, horizon, thresholds, label = "") {
  ok <- complete.cases(data[, c("time", "event")]) & is.finite(risk) &
    (data$time >= horizon | (data$event == 1 & data$time <= horizon))
  d <- data[ok, ]
  r <- risk[ok]
  y <- as.integer(d$event == 1 & d$time <= horizon)
  n <- length(y)
  prevalence <- mean(y)
  rows <- lapply(thresholds, function(pt) {
    treat <- as.integer(r >= pt)
    tp <- sum(treat == 1 & y == 1)
    fp <- sum(treat == 1 & y == 0)
    nb_model <- tp / n - fp / n * (pt / (1 - pt))
    nb_all <- prevalence - (1 - prevalence) * (pt / (1 - pt))
    data.frame(
      validation = label,
      threshold = pt,
      n = n,
      events_by_horizon = sum(y),
      net_benefit_model = nb_model,
      net_benefit_treat_all = nb_all,
      net_benefit_treat_none = 0
    )
  })
  do.call(rbind, rows)
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

bootstrap_optimism <- function(data, formula, vars, b = 100) {
  ids <- unique(data$id)
  apparent_model <- fit_model(formula, data)
  apparent_lp <- predict(apparent_model, newdata = data, type = "lp", reference = "zero")
  apparent_c <- cindex_lp(data, apparent_lp)
  boot_formula <- as.formula(paste("Surv(time, event) ~", paste(vars, collapse = " + ")))
  optimism <- c()
  failures <- 0
  for (i in seq_len(b)) {
    sampled_ids <- sample(ids, length(ids), replace = TRUE)
    boot <- do.call(rbind, lapply(seq_along(sampled_ids), function(j) {
      z <- data[data$id == sampled_ids[j], ]
      z$boot_cluster_id <- paste0(z$id, "_", j)
      z
    }))
    fit <- try(coxph(boot_formula, data = boot, x = TRUE, model = TRUE), silent = TRUE)
    if (inherits(fit, "try-error")) {
      failures <- failures + 1
      next
    }
    boot_lp <- try(predict(fit, newdata = boot, type = "lp", reference = "zero"), silent = TRUE)
    test_lp <- try(predict(fit, newdata = data, type = "lp", reference = "zero"), silent = TRUE)
    if (inherits(boot_lp, "try-error") || inherits(test_lp, "try-error")) {
      failures <- failures + 1
      next
    }
    c_boot <- cindex_lp(boot, boot_lp)
    c_test <- cindex_lp(data, test_lp)
    if (is.finite(c_boot) && is.finite(c_test)) optimism <- c(optimism, c_boot - c_test)
  }
  data.frame(
    bootstrap_repetitions_requested = b,
    bootstrap_repetitions_used = length(optimism),
    bootstrap_failures = failures,
    apparent_c_index = apparent_c,
    mean_optimism = mean(optimism, na.rm = TRUE),
    optimism_corrected_c_index = apparent_c - mean(optimism, na.rm = TRUE)
  )
}

coef_table <- function(model, model_name) {
  s <- summary(model)
  co <- as.data.frame(s$coefficients)
  ci <- as.data.frame(s$conf.int)
  terms <- rownames(co)
  data.frame(
    model = model_name,
    term = terms,
    beta = co[, "coef"],
    hazard_ratio = ci[, "exp(coef)"],
    ci_lower_95 = ci[, "lower .95"],
    ci_upper_95 = ci[, "upper .95"],
    robust_se = if ("robust se" %in% colnames(co)) co[, "robust se"] else co[, "se(coef)"],
    p_value = co[, "Pr(>|z|)"],
    p_value_formatted = fmt_p(co[, "Pr(>|z|)"]),
    row.names = NULL
  )
}

model_metrics <- function(model, data, risk, model_name, validation, horizon) {
  lp <- predict(model, newdata = data, type = "lp", reference = "zero")
  cal <- calibration_table(data, risk, horizon, label = validation)
  data.frame(
    model = model_name,
    validation = validation,
    n = nrow(data),
    participants = length(unique(data$id)),
    events_total = sum(data$event == 1, na.rm = TRUE),
    events_by_horizon = sum(data$event == 1 & data$time <= horizon, na.rm = TRUE),
    c_index = cindex_lp(data, lp),
    mean_predicted_risk = mean(risk, na.rm = TRUE),
    observed_km_risk = {
      fit <- survfit(Surv(time, event) ~ 1, data = data)
      s <- summary(fit, times = horizon, extend = TRUE)
      if (length(s$surv)) 1 - s$surv[1] else NA_real_
    },
    calibration_slope = {
      cal_model <- try(coxph(Surv(time, event) ~ lp, data = data), silent = TRUE)
      if (inherits(cal_model, "try-error")) NA_real_ else as.numeric(coef(cal_model)[1])
    },
    horizon_months = horizon
  )
}

plot_calibration <- function(cal, path, title) {
  p <- ggplot(cal, aes(x = mean_predicted_risk, y = observed_km_risk)) +
    geom_abline(slope = 1, intercept = 0, linetype = "dashed", color = "grey40") +
    geom_point(aes(size = n), color = "#1F77B4") +
    geom_line(color = "#1F77B4") +
    facet_wrap(~validation) +
    coord_equal(xlim = c(0, max(cal$mean_predicted_risk, cal$observed_km_risk, na.rm = TRUE) * 1.1),
                ylim = c(0, max(cal$mean_predicted_risk, cal$observed_km_risk, na.rm = TRUE) * 1.1)) +
    labs(title = title, x = "Mean predicted risk", y = "Observed Kaplan-Meier risk", size = "N") +
    theme_minimal(base_size = 12)
  ggsave(path, p, width = 7.5, height = 5.5, dpi = 180)
}

plot_dca <- function(dca, path, title) {
  long <- rbind(
    data.frame(validation = dca$validation, threshold = dca$threshold, strategy = "Model", net_benefit = dca$net_benefit_model),
    data.frame(validation = dca$validation, threshold = dca$threshold, strategy = "Treat all", net_benefit = dca$net_benefit_treat_all),
    data.frame(validation = dca$validation, threshold = dca$threshold, strategy = "Treat none", net_benefit = dca$net_benefit_treat_none)
  )
  p <- ggplot(long, aes(x = threshold, y = net_benefit, color = strategy)) +
    geom_line(linewidth = 0.9) +
    facet_wrap(~validation, scales = "free_y") +
    labs(title = title, x = "Risk threshold", y = "Net benefit") +
    theme_minimal(base_size = 12) +
    scale_color_manual(values = c("Model" = "#1F77B4", "Treat all" = "#D62728", "Treat none" = "grey35"))
  ggsave(path, p, width = 8.5, height = 5.5, dpi = 180)
}

oai <- prepare_oai()
check <- prepare_check()

oai_common <- complete_model_frame(oai, common_vars)
oai_full <- complete_model_frame(oai, full_vars)
check_common <- complete_model_frame(check, common_vars)
check_common <- subset(check_common, is.na(time) | time > 0)

write.csv(oai_common, file.path(derived_validation, "oai_24m_common_change_model_dataset.csv"), row.names = FALSE)
write.csv(oai_full, file.path(derived_validation, "oai_24m_full_change_model_dataset.csv"), row.names = FALSE)
write.csv(check_common, file.path(derived_validation, "check_24m_external_tka_dataset.csv"), row.names = FALSE)

fit_common <- fit_model(common_formula, oai_common)
fit_full <- fit_model(full_formula, oai_full)
saveRDS(fit_common, file.path(results_models, "cox_oai_24m_common_change.rds"))
saveRDS(fit_full, file.path(results_models, "cox_oai_24m_full_change.rds"))

risk_oai_common <- predict_risk(fit_common, oai_common, horizon_months)
risk_oai_full <- predict_risk(fit_full, oai_full, horizon_months)
risk_check_common <- predict_risk(fit_common, check_common, horizon_months)

coef_out <- rbind(
  coef_table(fit_common, "common_change"),
  coef_table(fit_full, "full_change")
)
write.csv(coef_out, file.path(results_tables, "cox_oai_24m_change_model_coefficients.csv"), row.names = FALSE)

metrics <- rbind(
  model_metrics(fit_common, oai_common, risk_oai_common, "common_change", "OAI apparent/internal", horizon_months),
  model_metrics(fit_full, oai_full, risk_oai_full, "full_change", "OAI apparent/internal", horizon_months),
  model_metrics(fit_common, check_common, risk_check_common, "common_change", "CHECK external exploratory TKA", horizon_months)
)

boot_common <- bootstrap_optimism(oai_common, common_formula, common_vars, b = 100)
boot_common$model <- "common_change"
boot_full <- bootstrap_optimism(oai_full, full_formula, full_vars, b = 100)
boot_full$model <- "full_change"
boot <- rbind(boot_common, boot_full)
write.csv(boot, file.path(results_tables, "oai_24m_internal_bootstrap_validation.csv"), row.names = FALSE)

metrics <- merge(metrics, boot[, c("model", "optimism_corrected_c_index", "mean_optimism", "bootstrap_repetitions_used")],
                 by = "model", all.x = TRUE)
write.csv(metrics, file.path(results_tables, "oai_24m_landmark_validation_metrics.csv"), row.names = FALSE)

cal_common_oai <- calibration_table(oai_common, risk_oai_common, horizon_months, label = "OAI common apparent")
cal_full_oai <- calibration_table(oai_full, risk_oai_full, horizon_months, label = "OAI full apparent")
cal_check <- calibration_table(check_common, risk_check_common, horizon_months, label = "CHECK TKA exploratory")
cal <- rbind(cal_common_oai, cal_full_oai, cal_check)
write.csv(cal, file.path(results_tables, "oai_check_24m_calibration_60m.csv"), row.names = FALSE)

thresholds <- seq(0.02, 0.30, by = 0.02)
dca <- rbind(
  decision_curve(oai_common, risk_oai_common, horizon_months, thresholds, label = "OAI common apparent"),
  decision_curve(oai_full, risk_oai_full, horizon_months, thresholds, label = "OAI full apparent"),
  decision_curve(check_common, risk_check_common, horizon_months, thresholds, label = "CHECK TKA exploratory")
)
write.csv(dca, file.path(results_tables, "oai_check_24m_decision_curve_60m.csv"), row.names = FALSE)

plot_calibration(cal, file.path(results_figures, "oai_check_24m_calibration_60m.png"),
                 "60-month risk calibration after 24-month landmark")
plot_dca(dca, file.path(results_figures, "oai_check_24m_decision_curve_60m.png"),
         "Decision curve at 60 months after landmark")

zph_common <- as.data.frame(cox.zph(fit_common)$table)
zph_common$term <- rownames(zph_common)
zph_common$model <- "common_change"
zph_full <- as.data.frame(cox.zph(fit_full)$table)
zph_full$term <- rownames(zph_full)
zph_full$model <- "full_change"
write.csv(rbind(zph_common, zph_full), file.path(results_tables, "cox_oai_24m_change_model_ph_test.csv"), row.names = FALSE)

# CHECK structural progression validation: the OAI common TKA risk score should
# still be interpretable as a transportability/risk-ranking score. We assess
# whether it ranks CHECK KL/JSN progression, not as a direct TKA probability.
check_common$risk_oai_common_60m <- risk_check_common
structural_outcomes <- c(
  "kl_progression_t0_t5", "kl_progression_t0_t8",
  "medial_jsn_progression_t0_t5", "medial_jsn_progression_t0_t8"
)
struct_rows <- lapply(structural_outcomes, function(outcome) {
  d <- check_common[complete.cases(check_common[, c(outcome, "risk_oai_common_60m")]), ]
  y <- d[[outcome]]
  fit <- glm(y ~ risk_oai_common_60m, data = d, family = binomial())
  auc <- binary_auc(y, d$risk_oai_common_60m)
  data.frame(
    validation = "CHECK structural progression",
    outcome = outcome,
    n = nrow(d),
    events = sum(y == 1, na.rm = TRUE),
    event_rate = mean(y == 1, na.rm = TRUE),
    odds_ratio_per_0_10_predicted_tka_risk = exp(coef(fit)[2] * 0.10),
    p_value = summary(fit)$coefficients[2, 4],
    c_index_auc = auc
  )
})
structural <- do.call(rbind, struct_rows)
write.csv(structural, file.path(results_tables, "check_structural_progression_validation.csv"), row.names = FALSE)

capture.output({
  cat("OAI 24-month landmark dynamic prediction validation\n")
  cat("Horizon after landmark:", horizon_months, "months\n\n")
  cat("OAI common dataset knees:", nrow(oai_common), "events:", sum(oai_common$event), "participants:", length(unique(oai_common$id)), "\n")
  cat("OAI full dataset knees:", nrow(oai_full), "events:", sum(oai_full$event), "participants:", length(unique(oai_full$id)), "\n")
  cat("CHECK common dataset knees:", nrow(check_common), "events after 24m:", sum(check_common$event), "participants:", length(unique(check_common$id)), "\n\n")
  cat("Metrics\n")
  print(metrics)
  cat("\nBootstrap internal validation\n")
  print(boot)
  cat("\nCommon model coefficients\n")
  print(summary(fit_common))
  cat("\nFull model coefficients\n")
  print(summary(fit_full))
  cat("\nCHECK structural progression validation\n")
  print(structural)
}, file = file.path(results_tables, "oai_check_24m_validation_report.txt"))

cat("Wrote validation outputs to", results_tables, "\n")
cat("OAI common knees:", nrow(oai_common), "events:", sum(oai_common$event), "\n")
cat("OAI full knees:", nrow(oai_full), "events:", sum(oai_full$event), "\n")
cat("CHECK external knees:", nrow(check_common), "events:", sum(check_common$event), "\n")
print(metrics)
