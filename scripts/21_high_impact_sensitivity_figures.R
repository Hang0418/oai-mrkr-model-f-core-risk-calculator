#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(survival)
  library(ggplot2)
  library(grid)
})

args_file <- sub("--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])
script_dir <- if (is.na(args_file)) getwd() else dirname(normalizePath(args_file))
root <- normalizePath(file.path(script_dir, ".."))

derived_transport <- file.path(root, "derived", "transport")
derived_mrkr <- file.path(root, "derived", "MRKR")
results_tables <- file.path(root, "results", "tables")
fig_dir <- file.path(root, "results", "figures")
dir.create(results_tables, recursive = TRUE, showWarnings = FALSE)
dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)

read_csv <- function(path) read.csv(path, stringsAsFactors = FALSE, check.names = TRUE)

theme_pub <- function(base_size = 10) {
  theme_minimal(base_size = base_size, base_family = "Helvetica") +
    theme(
      panel.grid.minor = element_blank(),
      panel.grid.major.x = element_blank(),
      axis.title = element_text(color = "#1F2933"),
      axis.text = element_text(color = "#1F2933"),
      plot.title = element_text(face = "bold", size = base_size + 2, color = "#0B2545"),
      plot.subtitle = element_text(size = base_size, color = "#3E4C59"),
      legend.position = "bottom",
      legend.title = element_blank(),
      strip.text = element_text(face = "bold", color = "#0B2545"),
      plot.margin = margin(8, 10, 8, 10)
    )
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

km_risk <- function(data, horizon) {
  if (nrow(data) == 0) return(NA_real_)
  s <- summary(survfit(Surv(time_months, event_primary) ~ 1, data = data), times = horizon, extend = TRUE)
  if (length(s$surv)) 1 - s$surv[1] else NA_real_
}

predict_risk_from_fit <- function(model, newdata, horizon) {
  bh <- basehaz(model, centered = FALSE)
  h0 <- approx(bh$time, bh$hazard, xout = horizon, method = "constant", rule = 2, f = 0)$y
  lp <- predict(model, newdata = newdata, type = "lp", reference = "zero")
  pmin(pmax(1 - exp(-h0 * exp(lp)), 0), 1)
}

prepare_common <- function(df) {
  df$right_knee <- ifelse(df$side_label == "right", 1, 0)
  df$kl_worsening <- ifelse(df$kl_change >= 1, 1, 0)
  df$pain_landmark_z <- as.numeric(scale(df$pain_landmark_0_10))
  df
}

metric_group <- function(d, label, horizon = 24) {
  if (nrow(d) < 30 || sum(d$event_primary == 1, na.rm = TRUE) < 5) {
    return(data.frame(
      subgroup = label, n_knees = nrow(d), n_patients = length(unique(d$patient_id)),
      total_events = sum(d$event_primary == 1, na.rm = TRUE), events_by_24m = NA_integer_,
      c_index = NA_real_, auc_24m = NA_real_, observed_km_24m_risk = NA_real_,
      original_mean_predicted_24m_risk = NA_real_, calibration_slope = NA_real_,
      calibration_slope_p_value = NA_real_
    ))
  }
  slope <- coxph(Surv(time_months, event_primary) ~ lp_f_core, data = d)
  data.frame(
    subgroup = label,
    n_knees = nrow(d),
    n_patients = length(unique(d$patient_id)),
    total_events = sum(d$event_primary == 1, na.rm = TRUE),
    events_by_24m = sum(d$event_primary == 1 & d$time_months <= horizon, na.rm = TRUE),
    c_index = cindex_lp(d, d$lp_f_core),
    auc_24m = td_auc(d, d$lp_f_core, horizon),
    observed_km_24m_risk = km_risk(d, horizon),
    original_mean_predicted_24m_risk = mean(d$risk_original_24m, na.rm = TRUE),
    calibration_slope = coef(slope)[1],
    calibration_slope_p_value = summary(slope)$coefficients[1, "Pr(>|z|)"]
  )
}

oai <- prepare_common(read_csv(file.path(derived_transport, "oai_train_model_f_core.csv")))
mrkr <- prepare_common(read_csv(file.path(derived_transport, "mrkr_validation_model_f_core.csv")))
enriched <- read_csv(file.path(derived_mrkr, "mrkr_transport_knee_dataset_enriched.csv"))
mrkr <- merge(
  mrkr,
  enriched[, c("knee_id", "race", "ethnicity", "knee_oa_dx_before_landmark", "oa_enriched_kl2",
               "oa_enriched_kl2_or_dx", "oa_enriched_pain_present", "high_quality_landmark",
               "pain_day_distance_24", "baseline_to_landmark_months")],
  by = "knee_id",
  all.x = TRUE,
  suffixes = c("", "_enriched")
)
if ("race_enriched" %in% names(mrkr)) {
  mrkr$race <- ifelse(is.na(mrkr$race) | mrkr$race == "", mrkr$race_enriched, mrkr$race)
}

fit_f <- coxph(
  Surv(time_months, event_primary) ~ age + female + right_knee + pain_landmark_z +
    kl_baseline + kl_worsening + cluster(patient_id),
  data = oai,
  x = TRUE,
  model = TRUE
)
mrkr$lp_f_core <- predict(fit_f, newdata = mrkr, type = "lp", reference = "zero")
mrkr$risk_original_24m <- predict_risk_from_fit(fit_f, mrkr, 24)

subgroups <- list(
  "All MRKR core" = mrkr,
  "OA enriched: baseline KL>=2" = subset(mrkr, oa_enriched_kl2 == 1),
  "OA enriched: knee OA ICD before landmark" = subset(mrkr, knee_oa_dx_before_landmark == 1),
  "OA enriched: KL>=2 or OA ICD" = subset(mrkr, oa_enriched_kl2_or_dx == 1),
  "Pain-present at landmark" = subset(mrkr, oa_enriched_pain_present == 1),
  "High-quality landmark/pain window" = subset(mrkr, high_quality_landmark == 1),
  "Female" = subset(mrkr, female == 1),
  "Male" = subset(mrkr, female == 0),
  "Age <60 years" = subset(mrkr, age < 60),
  "Age 60-69 years" = subset(mrkr, age >= 60 & age < 70),
  "Age >=70 years" = subset(mrkr, age >= 70),
  "Baseline KL 0-1" = subset(mrkr, kl_baseline < 2),
  "Baseline KL 2" = subset(mrkr, kl_baseline == 2),
  "Baseline KL 3-4" = subset(mrkr, kl_baseline >= 3)
)

race_counts <- sort(table(mrkr$race), decreasing = TRUE)
for (race_name in names(race_counts)[seq_len(min(4, length(race_counts)))]) {
  subgroups[[paste0("Race: ", race_name)]] <- subset(mrkr, race == race_name)
}

subgroup_perf <- do.call(rbind, Map(metric_group, subgroups, names(subgroups)))
write.csv(subgroup_perf, file.path(results_tables, "oai_mrkr_highimpact_mrkr_subgroup_performance_24m.csv"), row.names = FALSE)

# Figure A: study design flow.
flow <- data.frame(
  x = c(1, 2.7, 4.4, 2.7, 4.4, 6.1),
  y = c(3, 3, 3, 1.6, 1.6, 1.6),
  label = c(
    "OAI 24-month landmark\nModel E development",
    "Sequential OAI models\nA to E",
    "Complete dynamic Model E\ninternal validation",
    "Common-variable\nModel F-core",
    "MRKR real-world\ntransport validation",
    "MRKR recalibration\nand sensitivity"
  )
)
arrows <- data.frame(x = c(1.55, 3.25, 2.7, 3.25, 4.95), y = c(3, 3, 2.65, 1.6, 1.6),
                     xend = c(2.15, 3.85, 2.7, 3.85, 5.55), yend = c(3, 3, 1.95, 1.6, 1.6))
p_flow <- ggplot() +
  geom_segment(data = arrows, aes(x = x, y = y, xend = xend, yend = yend),
               arrow = arrow(length = unit(0.18, "cm")), linewidth = 0.5, color = "#52616B") +
  geom_label(data = flow, aes(x = x, y = y, label = label),
             size = 3.1, label.size = 0.35, label.r = unit(0.08, "lines"),
             fill = "#F7F9FB", color = "#0B2545", label.padding = unit(0.28, "lines")) +
  annotate("text", x = 2.7, y = 3.65, label = "OAI mechanistic dynamic model", fontface = "bold", size = 3.4, color = "#0B2545") +
  annotate("text", x = 4.4, y = 0.95, label = "Common-variable transport model", fontface = "bold", size = 3.4, color = "#0B2545") +
  xlim(0.2, 6.9) + ylim(0.6, 4.0) +
  theme_void()
ggsave(file.path(fig_dir, "figure_oai_mrkr_highimpact_1_design_flow.png"), p_flow, width = 8.5, height = 4.2, dpi = 450)

# Figure B: time structure comparison.
time_structure <- read_csv(file.path(results_tables, "oai_mrkr_plan_time_structure_table.csv"))
time_long <- rbind(
  data.frame(cohort = time_structure$cohort, horizon = 12, events = time_structure$events_12m, at_risk = time_structure$at_risk_12m),
  data.frame(cohort = time_structure$cohort, horizon = 24, events = time_structure$events_24m, at_risk = time_structure$at_risk_24m),
  data.frame(cohort = time_structure$cohort, horizon = 36, events = time_structure$events_36m, at_risk = time_structure$at_risk_36m),
  data.frame(cohort = time_structure$cohort, horizon = 60, events = time_structure$events_60m, at_risk = time_structure$at_risk_60m)
)
p_time <- ggplot(time_long, aes(x = factor(horizon), y = events, fill = cohort)) +
  geom_col(position = position_dodge(width = 0.72), width = 0.62) +
  geom_text(aes(label = paste0("risk ", at_risk)), position = position_dodge(width = 0.72), vjust = -0.35, size = 2.7, color = "#1F2933") +
  scale_fill_manual(values = c("OAI" = "#2E74B5", "MRKR" = "#B45F06")) +
  labs(title = "Event-time structure differs between OAI and MRKR",
       subtitle = "Numbers above bars show knees still at risk at each horizon",
       x = "Months after landmark", y = "Events by horizon") +
  theme_pub()
ggsave(file.path(fig_dir, "figure_oai_mrkr_highimpact_2_time_structure.png"), p_time, width = 7.2, height = 4.6, dpi = 450)

# Figure C: calibration before and after recalibration.
cal <- read_csv(file.path(results_tables, "oai_mrkr_plan_calibration_24m.csv"))
cal <- subset(cal, model %in% c("MRKR original OAI baseline", "MRKR slope+baseline recalibrated"))
p_cal <- ggplot(cal, aes(x = mean_predicted_risk, y = observed_km_risk, color = model)) +
  geom_abline(slope = 1, intercept = 0, linetype = "dashed", color = "#52616B") +
  geom_point(aes(size = n), alpha = 0.85) +
  geom_line(linewidth = 0.7) +
  scale_color_manual(values = c("MRKR original OAI baseline" = "#9B1C1C", "MRKR slope+baseline recalibrated" = "#1F7A5C")) +
  scale_x_continuous(labels = scales::percent_format(accuracy = 1), limits = c(0, NA)) +
  scale_y_continuous(labels = scales::percent_format(accuracy = 1), limits = c(0, NA)) +
  labs(title = "MRKR 24-month calibration before and after recalibration",
       x = "Mean predicted 24-month risk", y = "Observed Kaplan-Meier 24-month risk") +
  guides(size = "none") +
  theme_pub()
ggsave(file.path(fig_dir, "figure_oai_mrkr_highimpact_3_calibration.png"), p_cal, width = 6.4, height = 5.0, dpi = 450)

# Figure D: recalibrated risk strata.
strata <- read_csv(file.path(results_tables, "oai_mrkr_plan_mrkr_risk_strata_24m.csv"))
strata$risk_group_recalibrated_24m <- factor(strata$risk_group_recalibrated_24m, levels = c("<10%", "10-25%", "25-50%", ">50%"))
strata_long <- rbind(
  data.frame(group = strata$risk_group_recalibrated_24m, risk = strata$mean_recalibrated_predicted_24m_risk, type = "Predicted"),
  data.frame(group = strata$risk_group_recalibrated_24m, risk = strata$observed_km_24m_risk, type = "Observed")
)
p_strata <- ggplot(strata_long, aes(x = group, y = risk, fill = type)) +
  geom_col(position = position_dodge(width = 0.7), width = 0.58) +
  geom_text(data = strata, aes(x = risk_group_recalibrated_24m, y = pmax(mean_recalibrated_predicted_24m_risk, observed_km_24m_risk) + 0.045,
                               label = paste0("n=", n_knees, "\n24m events=", events_by_24m)),
            inherit.aes = FALSE, size = 2.7, color = "#1F2933") +
  scale_fill_manual(values = c("Predicted" = "#1F7A5C", "Observed" = "#2E74B5")) +
  scale_y_continuous(labels = scales::percent_format(accuracy = 1), limits = c(0, 0.65)) +
  labs(title = "MRKR recalibrated risk strata show a graded event pattern",
       x = "Slope+baseline recalibrated 24-month risk group", y = "24-month risk") +
  theme_pub()
ggsave(file.path(fig_dir, "figure_oai_mrkr_highimpact_4_risk_strata.png"), p_strata, width = 7.2, height = 4.8, dpi = 450)

# Figure E: strict and outcome sensitivity.
strict <- read_csv(file.path(results_tables, "oai_mrkr_plan_mrkr_strict_sensitivity_24m.csv"))
strict$analysis <- "Early-event exclusion"
strict$label <- c("All", ">3m", ">6m", ">12m")
strict$label <- factor(strict$label, levels = c("All", ">3m", ">6m", ">12m"))
outcome <- read_csv(file.path(results_tables, "oai_mrkr_plan_mrkr_outcome_sensitivity_24m.csv"))
outcome$analysis <- "Outcome definition"
outcome$label <- c("Hardware", "CPT", "Combined")
outcome$label <- factor(outcome$label, levels = c("Hardware", "CPT", "Combined"))
sens <- rbind(
  strict[, c("analysis", "label", "n_knees", "total_events", "auc_24m", "c_index")],
  outcome[, c("analysis", "label", "n_knees", "total_events", "auc_24m", "c_index")]
)
p_sens <- ggplot(sens, aes(x = label, y = auc_24m, group = analysis, color = analysis)) +
  geom_hline(yintercept = 0.5, linetype = "dashed", color = "#9AA5B1") +
  geom_point(size = 2.8) +
  geom_line(linewidth = 0.7) +
  geom_text(aes(label = sprintf("n=%s\ne=%s", n_knees, total_events)), vjust = -0.75, size = 2.55, color = "#1F2933", lineheight = 0.9) +
  facet_wrap(~analysis, scales = "free_x") +
  scale_color_manual(values = c("Early-event exclusion" = "#B45F06", "Outcome definition" = "#2E74B5")) +
  coord_cartesian(ylim = c(0.55, 0.74)) +
  labs(title = "MRKR sensitivity analyses preserve moderate discrimination",
       x = NULL, y = "24-month AUC") +
  theme_pub() + theme(legend.position = "none")
ggsave(file.path(fig_dir, "figure_oai_mrkr_highimpact_5_sensitivity.png"), p_sens, width = 8.0, height = 4.8, dpi = 450)

# Supplementary subgroup plot.
plot_sub <- subset(subgroup_perf, !is.na(auc_24m))
plot_sub$subgroup <- factor(plot_sub$subgroup, levels = rev(plot_sub$subgroup))
p_sub <- ggplot(plot_sub, aes(x = auc_24m, y = subgroup)) +
  geom_vline(xintercept = 0.5, linetype = "dashed", color = "#9AA5B1") +
  geom_point(color = "#2E74B5", size = 2.4) +
  geom_text(aes(label = paste0("n=", n_knees, ", e=", total_events)), hjust = -0.05, size = 2.55, color = "#1F2933") +
  coord_cartesian(xlim = c(0.55, 0.82)) +
  labs(title = "MRKR subgroup transportability of the OAI-derived Model F-core",
       x = "24-month AUC", y = NULL) +
  theme_pub(base_size = 9)
ggsave(file.path(fig_dir, "figure_oai_mrkr_highimpact_supp_subgroups.png"), p_sub, width = 7.5, height = 7.0, dpi = 450)

cat("Wrote high-impact subgroup table and figures.\n")
print(subgroup_perf)
