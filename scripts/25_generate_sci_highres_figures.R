#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(ggplot2)
  library(grid)
  library(rms)
  library(survival)
})

args_file <- sub("--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])
script_dir <- if (is.na(args_file)) getwd() else dirname(normalizePath(args_file))
root <- normalizePath(file.path(script_dir, ".."))
tables <- file.path(root, "results", "tables")
figs <- file.path(root, "results", "figures")
dir.create(figs, recursive = TRUE, showWarnings = FALSE)

read_csv <- function(path) read.csv(path, stringsAsFactors = FALSE, check.names = TRUE)

blue <- "#1F5D99"; navy <- "#0B2545"; teal <- "#1F7A5C"; orange <- "#B45F06"
red <- "#9B1C1C"; gray <- "#52616B"; light_blue <- "#EAF3FB"
light_orange <- "#FFF4E6"; light_green <- "#EAF7F0"; light_red <- "#FFF1F1"

theme_sci <- function(base_size = 10) {
  theme_minimal(base_size = base_size, base_family = "Helvetica") +
    theme(
      panel.grid.minor = element_blank(),
      panel.grid.major.x = element_blank(),
      axis.title = element_text(color = "#1F2933"),
      axis.text = element_text(color = "#1F2933"),
      plot.title = element_text(face = "bold", color = navy, size = base_size + 2),
      plot.subtitle = element_text(color = gray, size = base_size),
      legend.position = "bottom",
      legend.title = element_blank(),
      strip.text = element_text(face = "bold", color = navy),
      plot.margin = margin(8, 10, 8, 10)
    )
}

save_plot <- function(plot, stem, width, height) {
  ggsave(file.path(figs, paste0(stem, ".png")), plot, width = width, height = height, dpi = 600, bg = "white")
  ggsave(file.path(figs, paste0(stem, ".pdf")), plot, width = width, height = height, bg = "white")
  ggsave(file.path(figs, paste0(stem, ".svg")), plot, width = width, height = height, bg = "white")
}

grid_save <- function(stem, width, height, draw_fun) {
  png(file.path(figs, paste0(stem, ".png")), width = width, height = height, units = "in", res = 600, type = "cairo", bg = "white")
  draw_fun(); dev.off()
  pdf(file.path(figs, paste0(stem, ".pdf")), width = width, height = height, bg = "white")
  draw_fun(); dev.off()
  svg(file.path(figs, paste0(stem, ".svg")), width = width, height = height, bg = "white")
  draw_fun(); dev.off()
}

box_grob <- function(x, y, w, h, label, fill, col = navy, fontsize = 8.5, fontface = "plain") {
  grid.roundrect(x, y, w, h, r = unit(0.06, "snpc"), gp = gpar(fill = fill, col = col, lwd = 1))
  grid.text(label, x, y, gp = gpar(col = navy, fontsize = fontsize, fontface = fontface))
}

arrow_grob <- function(x0, y0, x1, y1, col = gray) {
  grid.segments(x0, y0, x1, y1, arrow = arrow(length = unit(0.12, "inches"), type = "closed"), gp = gpar(col = col, lwd = 1.1))
}

fig1 <- function() {
  draw <- function() {
    grid.newpage()
    grid.text("OAI model development", x = 0.23, y = 0.96, gp = gpar(fontface = "bold", fontsize = 14, col = navy))
    grid.text("MRKR transport validation", x = 0.75, y = 0.96, gp = gpar(fontface = "bold", fontsize = 14, col = navy))
    oai <- c(
      "OAI knee rows assembled\n9,592 knees / 4,796 participants",
      "Exclude baseline/prior KR/TKA\n69 knees",
      "Exclude KR/TKA <=24-month landmark\n74 knees",
      "Exclude no post-landmark follow-up\n692 knees",
      "Exclude missing 24-month pain\n443 knees",
      "Exclude missing Model F-core predictors\n5,210 knees",
      "OAI Model F-core training set\n3,104 knees / 1,656 participants\n566 KR/TKA events",
      "OAI Model E common-complete set\n3,066 knees / 1,640 participants\n559 KR/TKA events"
    )
    fills <- c(light_blue, rep(light_orange, 5), light_green, light_green)
    ys <- seq(0.86, 0.17, length.out = length(oai))
    for (i in seq_along(oai)) {
      box_grob(0.24, ys[i], 0.38, 0.075, oai[i], fills[i], fontsize = 8.2, fontface = ifelse(i %in% c(1, 7, 8), "bold", "plain"))
      if (i < length(oai)) arrow_grob(0.24, ys[i] - 0.045, 0.24, ys[i + 1] + 0.045)
    }
    mrkr <- c(
      "MRKR baseline-landmark knee pairs\n9,115 knees / 5,162 patients",
      "Exclude no positive hardware follow-up\n4,506 knees",
      "Exclude missing/ambiguous laterality\n0 knees",
      "Exclude missing landmark pain\n1,197 knees",
      "Exclude missing KL information\n0 knees",
      "Exclude missing age/sex\n0 knees",
      "MRKR Model F-core validation set\n3,412 knees / 2,179 patients\n1,140 hardware events"
    )
    fills2 <- c(light_blue, rep(light_orange, 5), light_green)
    ys2 <- seq(0.86, 0.24, length.out = length(mrkr))
    for (i in seq_along(mrkr)) {
      box_grob(0.75, ys2[i], 0.38, 0.078, mrkr[i], fills2[i], fontsize = 8.2, fontface = ifelse(i %in% c(1, 7), "bold", "plain"))
      if (i < length(mrkr)) arrow_grob(0.75, ys2[i] - 0.047, 0.75, ys2[i + 1] + 0.047)
    }
    grid.text("KR/TKA, knee replacement or total knee arthroplasty; KL, Kellgren-Lawrence grade.", x = 0.5, y = 0.05, gp = gpar(fontsize = 8, col = gray))
  }
  grid_save("figure_oai_mrkr_sci_1_cohort_flow", 12.5, 7.2, draw)
}

fig2 <- function() {
  draw <- function() {
    grid.newpage()
    grid.text("Scientific OAI dynamic model", x = 0.18, y = 0.94, gp = gpar(fontface = "bold", fontsize = 13, col = navy))
    grid.text("Common-variable transport model", x = 0.68, y = 0.94, gp = gpar(fontface = "bold", fontsize = 13, col = navy))
    box_grob(0.18, 0.78, 0.26, 0.11, "OAI 24-month\nlandmark cohort", light_blue, fontface = "bold")
    box_grob(0.18, 0.57, 0.26, 0.11, "Sequential models\nA to E", light_blue)
    box_grob(0.18, 0.34, 0.28, 0.14, "Primary Model E\nbaseline symptoms + KL/JSN\n+ 0-24m dynamic change", light_green, fontsize = 8, fontface = "bold")
    arrow_grob(0.18, 0.72, 0.18, 0.63); arrow_grob(0.18, 0.51, 0.18, 0.41)
    box_grob(0.50, 0.75, 0.22, 0.15, "OAI Model F-core\nage, sex, side,\nstandardized pain,\nbaseline KL, KL worsening", light_blue, fontsize = 8, fontface = "bold")
    box_grob(0.80, 0.75, 0.22, 0.15, "MRKR validation\nside-specific hardware\noutcome", light_blue, fontsize = 8, fontface = "bold")
    box_grob(0.50, 0.47, 0.22, 0.12, "Transport validation\nC-index, AUC,\ncalibration, DCA", light_green, fontsize = 8)
    box_grob(0.80, 0.47, 0.22, 0.12, "Slope + baseline\nrecalibration", light_green, fontsize = 8)
    box_grob(0.65, 0.23, 0.26, 0.12, "Risk strata and\nsensitivity analyses", light_orange, fontsize = 8.5, fontface = "bold")
    arrow_grob(0.32, 0.78, 0.39, 0.78)
    arrow_grob(0.61, 0.75, 0.69, 0.75)
    arrow_grob(0.50, 0.67, 0.50, 0.53)
    arrow_grob(0.80, 0.67, 0.80, 0.53)
    arrow_grob(0.55, 0.41, 0.62, 0.30)
    arrow_grob(0.75, 0.41, 0.68, 0.30)
  }
  grid_save("figure_oai_mrkr_sci_2_modeling_framework", 11.2, 5.6, draw)
}

fig3 <- function() {
  df <- read_csv(file.path(tables, "oai_docx_plan_model_comparison.csv"))
  labels <- c("A\nBasic", "B\nSymptoms", "C\nSymptoms+\nImaging", "D\nDynamic\nClinical", "E\nDynamic\nClinical-\nImaging")
  d1 <- data.frame(model = factor(labels, levels = labels), C_index = df$c_index, Optimism_corrected = df$optimism_corrected_c_index)
  long1 <- reshape(d1, varying = c("C_index", "Optimism_corrected"), v.names = "value", timevar = "metric", times = c("Apparent", "Bootstrap-corrected"), direction = "long")
  p1 <- ggplot(long1, aes(model, value, group = metric, color = metric)) + geom_line(linewidth = .8) + geom_point(size = 2) + labs(y = "C-index", x = NULL, title = "A Overall discrimination") + scale_color_manual(values = c(blue, orange)) + theme_sci(9)
  p2 <- ggplot(data.frame(model = factor(labels, levels = labels), auc = df$auc_60m), aes(model, auc, group = 1)) + geom_line(color = blue, linewidth = .8) + geom_point(color = blue, size = 2) + labs(y = "60-month AUC", x = NULL, title = "B Fixed-horizon discrimination") + theme_sci(9)
  p3 <- ggplot(data.frame(model = factor(labels, levels = labels), brier = df$brier_60m), aes(model, brier, group = 1)) + geom_line(color = red, linewidth = .8) + geom_point(color = red, size = 2) + scale_y_reverse() + labs(y = "60-month Brier\n(lower is better)", x = NULL, title = "C Prediction error") + theme_sci(9)
  png(file.path(figs, "figure_oai_mrkr_sci_3_oai_staged_performance.png"), 12.2, 4.2, units = "in", res = 600, type = "cairo"); grid.arrange <- getExportedValue("gridExtra", "grid.arrange"); grid.arrange(p1, p2, p3, ncol = 3, top = textGrob("Staged OAI model performance in the 24-month landmark analysis", gp = gpar(fontface = "bold", fontsize = 13, col = navy))); dev.off()
  pdf(file.path(figs, "figure_oai_mrkr_sci_3_oai_staged_performance.pdf"), 12.2, 4.2); grid.arrange(p1, p2, p3, ncol = 3, top = textGrob("Staged OAI model performance in the 24-month landmark analysis", gp = gpar(fontface = "bold", fontsize = 13, col = navy))); dev.off()
  svg(file.path(figs, "figure_oai_mrkr_sci_3_oai_staged_performance.svg"), 12.2, 4.2); grid.arrange(p1, p2, p3, ncol = 3, top = textGrob("Staged OAI model performance in the 24-month landmark analysis", gp = gpar(fontface = "bold", fontsize = 13, col = navy))); dev.off()
}

make_simple_figs <- function() {
  cal <- read_csv(file.path(tables, "oai_docx_plan_calibration_60m.csv"))
  dca <- read_csv(file.path(tables, "oai_docx_plan_decision_curve_60m.csv"))
  p4a <- ggplot(cal, aes(mean_predicted_risk, observed_km_risk)) + geom_abline(linetype = "dashed", color = gray) + geom_line(color = blue) + geom_point(color = blue, size = 2) + labs(title = "A Calibration", x = "Mean predicted 60-month risk", y = "Observed KM 60-month risk") + theme_sci()
  p4b <- ggplot(dca, aes(threshold)) + geom_line(aes(y = net_benefit_model, color = "Model E"), linewidth = 1) + geom_line(aes(y = net_benefit_treat_all, color = "Treat all"), linewidth = 1) + geom_line(aes(y = net_benefit_treat_none, color = "Treat none"), linewidth = 1) + scale_color_manual(values = c("Model E" = blue, "Treat all" = red, "Treat none" = gray)) + labs(title = "B Decision curve", x = "Threshold probability", y = "Net benefit") + theme_sci()
  combo_save(list(p4a, p4b), "figure_oai_mrkr_sci_4_oai_model_e_calibration_dca", "OAI Model E calibration and decision-curve analysis at 60 months", 11.5, 4.8)

  time <- read_csv(file.path(tables, "oai_mrkr_plan_time_structure_table.csv"))
  d <- do.call(rbind, lapply(c(12,24,36,60), function(h) data.frame(cohort=time$cohort, horizon=factor(h, levels=c(12,24,36,60)), events=time[[paste0("events_",h,"m")]], at_risk=time[[paste0("at_risk_",h,"m")]])))
  p5 <- ggplot(d, aes(horizon, events, fill = cohort)) + geom_col(position = position_dodge(.75), width = .62) + geom_text(aes(label = paste0("risk ", at_risk)), position = position_dodge(.75), vjust = -.35, size = 2.7) + scale_fill_manual(values = c(OAI=blue, MRKR=orange)) + labs(title = "OAI and MRKR time-event structure", x = "Months after landmark", y = "Events by horizon") + theme_sci()
  save_plot(p5, "figure_oai_mrkr_sci_5_time_event_structure", 8.8, 5)

  transport <- read_csv(file.path(tables, "oai_mrkr_plan_transport_metrics_by_horizon.csv"))
  mrkr_perf <- subset(
    transport,
    cohort == "MRKR" & model %in% c("Original OAI-derived Model F-core", "MRKR slope+baseline recalibrated Model F-core")
  )
  mrkr_perf$model_label <- ifelse(
    mrkr_perf$model == "Original OAI-derived Model F-core",
    "Original OAI-derived",
    "Slope+baseline recalibrated"
  )
  p6a <- ggplot(unique(mrkr_perf[, c("horizon_months", "auc_horizon")]), aes(horizon_months, auc_horizon)) +
    geom_line(color = blue, linewidth = .9) +
    geom_point(color = blue, size = 2) +
    scale_x_continuous(breaks = c(12, 24, 36, 60)) +
    coord_cartesian(ylim = c(.66, .79)) +
    labs(title = "A MRKR time-dependent AUC", x = "Months after landmark", y = "AUC") +
    theme_sci(8.5)
  p6b <- ggplot(subset(mrkr_perf, model_label == "Original OAI-derived"), aes(horizon_months)) +
    geom_line(aes(y = mean_predicted_risk, color = "Predicted"), linewidth = .9) +
    geom_point(aes(y = mean_predicted_risk, color = "Predicted"), size = 2) +
    geom_line(aes(y = observed_km_risk, color = "Observed"), linewidth = .9) +
    geom_point(aes(y = observed_km_risk, color = "Observed"), size = 2) +
    scale_x_continuous(breaks = c(12, 24, 36, 60)) +
    scale_y_continuous(labels = scales::percent_format(accuracy = 1)) +
    scale_color_manual(values = c(Predicted = red, Observed = gray)) +
    labs(title = "B Original OAI-derived risk", x = "Months after landmark", y = "Risk") +
    theme_sci(8.5)
  p6c <- ggplot(subset(mrkr_perf, model_label == "Slope+baseline recalibrated"), aes(horizon_months)) +
    geom_line(aes(y = mean_predicted_risk, color = "Predicted"), linewidth = .9) +
    geom_point(aes(y = mean_predicted_risk, color = "Predicted"), size = 2) +
    geom_line(aes(y = observed_km_risk, color = "Observed"), linewidth = .9) +
    geom_point(aes(y = observed_km_risk, color = "Observed"), size = 2) +
    scale_x_continuous(breaks = c(12, 24, 36, 60)) +
    scale_y_continuous(labels = scales::percent_format(accuracy = 1)) +
    scale_color_manual(values = c(Predicted = teal, Observed = gray)) +
    labs(title = "C Recalibrated risk", x = "Months after landmark", y = "Risk") +
    theme_sci(8.5)
  cal2 <- subset(read_csv(file.path(tables, "oai_mrkr_plan_calibration_24m.csv")), model %in% c("MRKR original OAI baseline","MRKR slope+baseline recalibrated"))
  p6d <- ggplot(cal2, aes(mean_predicted_risk, observed_km_risk, color = model)) +
    geom_abline(linetype = "dashed", color = gray) +
    geom_line(linewidth = .9) +
    geom_point(size = 1.8) +
    scale_x_continuous(labels = scales::percent_format(accuracy = 1)) +
    scale_y_continuous(labels = scales::percent_format(accuracy = 1)) +
    scale_color_manual(values = c("MRKR original OAI baseline"=red, "MRKR slope+baseline recalibrated"=teal), labels = c("Original", "Recalibrated")) +
    labs(title = "D Calibration at 24 months", x = "Mean predicted risk", y = "Observed KM risk") +
    theme_sci(8.5)
  p6e <- ggplot(mrkr_perf, aes(factor(horizon_months), brier_horizon, fill = model_label)) +
    geom_col(position = position_dodge(.7), width = .58) +
    scale_fill_manual(values = c("Original OAI-derived" = red, "Slope+baseline recalibrated" = teal)) +
    labs(title = "E Brier score", x = "Months after landmark", y = "Brier score") +
    theme_sci(8.5)
  grid.arrange <- getExportedValue("gridExtra", "grid.arrange")
  title6 <- textGrob("MRKR transport validation and recalibration of the OAI-derived Model F-core", gp = gpar(fontface = "bold", fontsize = 13, col = navy))
  png(file.path(figs, "figure_oai_mrkr_sci_6_mrkr_calibration_recalibration.png"), 12.5, 7.5, units = "in", res = 600, type = "cairo", bg = "white")
  grid.arrange(p6a, p6b, p6c, p6d, p6e, ncol = 3, top = title6)
  dev.off()
  pdf(file.path(figs, "figure_oai_mrkr_sci_6_mrkr_calibration_recalibration.pdf"), 12.5, 7.5, bg = "white")
  grid.arrange(p6a, p6b, p6c, p6d, p6e, ncol = 3, top = title6)
  dev.off()
  svg(file.path(figs, "figure_oai_mrkr_sci_6_mrkr_calibration_recalibration.svg"), 12.5, 7.5, bg = "white")
  grid.arrange(p6a, p6b, p6c, p6d, p6e, ncol = 3, top = title6)
  dev.off()

  strata <- read_csv(file.path(tables, "oai_mrkr_plan_mrkr_risk_strata_24m.csv"))
  strata$group <- factor(strata$risk_group_recalibrated_24m, levels = c("<10%","10-25%","25-50%",">50%"))
  sl <- rbind(data.frame(group=strata$group, risk=strata$mean_recalibrated_predicted_24m_risk, type="Predicted"), data.frame(group=strata$group, risk=strata$observed_km_24m_risk, type="Observed"))
  p7 <- ggplot(sl, aes(group, risk, fill = type)) + geom_col(position = position_dodge(.7), width = .58) + geom_text(data = strata, aes(group, pmax(mean_recalibrated_predicted_24m_risk, observed_km_24m_risk)+.045, label = paste0("n=", n_knees, "\ne=", events_by_24m)), inherit.aes = FALSE, size = 2.7) + scale_fill_manual(values=c(Predicted=teal, Observed=blue)) + coord_cartesian(ylim=c(0,.65)) + labs(title = "MRKR recalibrated 24-month risk strata", x = "Risk stratum", y = "24-month risk") + theme_sci()
  save_plot(p7, "figure_oai_mrkr_sci_7_mrkr_risk_strata", 8.4, 4.8)

  strict <- read_csv(file.path(tables, "oai_mrkr_plan_mrkr_strict_sensitivity_24m.csv")); strict$label <- factor(c("All", ">3m", ">6m", ">12m"), levels=c("All",">3m",">6m",">12m"))
  out <- read_csv(file.path(tables, "oai_mrkr_plan_mrkr_outcome_sensitivity_24m.csv")); out$label <- factor(c("Hardware","CPT","Combined"), levels=c("Hardware","CPT","Combined"))
  p8a <- ggplot(strict, aes(label, auc_24m, group=1)) + geom_hline(yintercept=.5, linetype="dashed", color=gray) + geom_line(color=blue) + geom_point(color=blue, size=2) + geom_text(aes(label=paste0("n=",n_knees,"\ne=",events_by_24m)), vjust=-.7, size=2.6) + coord_cartesian(ylim=c(.58,.75)) + labs(title="A Early-event exclusions", x=NULL, y="24-month AUC") + theme_sci()
  p8b <- ggplot(out, aes(label, auc_24m, group=1)) + geom_hline(yintercept=.5, linetype="dashed", color=gray) + geom_line(color=orange) + geom_point(color=orange, size=2) + geom_text(aes(label=paste0("n=",n_knees,"\ne=",events_by_24m)), vjust=-.7, size=2.6) + coord_cartesian(ylim=c(.58,.75)) + labs(title="B Outcome definitions", x=NULL, y="24-month AUC") + theme_sci()
  combo_save(list(p8a, p8b), "figure_oai_mrkr_sci_8_mrkr_sensitivity", "MRKR early-event and outcome-definition sensitivity analyses", 10.5, 4.8)
}

combo_save <- function(plots, stem, title, width, height) {
  grid.arrange <- getExportedValue("gridExtra", "grid.arrange")
  top <- textGrob(title, gp = gpar(fontface = "bold", fontsize = 13, col = navy))
  png(file.path(figs, paste0(stem, ".png")), width, height, units = "in", res = 600, type = "cairo", bg = "white"); grid.arrange(grobs = plots, ncol = length(plots), top = top); dev.off()
  pdf(file.path(figs, paste0(stem, ".pdf")), width, height, bg = "white"); grid.arrange(grobs = plots, ncol = length(plots), top = top); dev.off()
  svg(file.path(figs, paste0(stem, ".svg")), width, height, bg = "white"); grid.arrange(grobs = plots, ncol = length(plots), top = top); dev.off()
}

supp_figs <- function() {
  nom_data <- read.csv(file.path(root, "derived", "validation", "oai_docx_plan_common_complete_dataset.csv"), stringsAsFactors = FALSE)
  nom_data$side <- factor(nom_data$side, levels = c("left", "right"), labels = c("Left knee", "Right knee"))
  nom_data$female <- factor(nom_data$female, levels = c(0, 1), labels = c("Male", "Female"))
  label(nom_data$age) <- "Age, years"
  label(nom_data$female) <- "Sex"
  label(nom_data$bmi) <- "BMI"
  label(nom_data$side) <- "Knee side"
  label(nom_data$pain_0) <- "Baseline WOMAC pain"
  label(nom_data$function_0) <- "Baseline WOMAC function"
  label(nom_data$stiffness_0) <- "Baseline WOMAC stiffness"
  label(nom_data$pain_change) <- "0-24m WOMAC pain change"
  label(nom_data$function_change) <- "0-24m WOMAC function change"
  label(nom_data$kl_0) <- "Baseline KL grade"
  label(nom_data$kl_change) <- "0-24m KL change"
  label(nom_data$jsn_medial_0) <- "Baseline medial JSN"
  label(nom_data$jsn_medial_change) <- "0-24m medial JSN change"
  label(nom_data$jsn_lateral_0) <- "Baseline lateral JSN"
  label(nom_data$jsn_lateral_change) <- "0-24m lateral JSN change"
  dd <- datadist(nom_data)
  old_opts <- options(datadist = "dd")
  assign("dd", dd, envir = .GlobalEnv)
  nom_fit <- cph(
    Surv(time, event) ~ age + female + bmi + side + pain_0 + function_0 +
      stiffness_0 + pain_change + function_change + kl_0 + kl_change +
      jsn_medial_0 + jsn_medial_change + jsn_lateral_0 + jsn_lateral_change,
    data = nom_data, x = TRUE, y = TRUE, surv = TRUE
  )
  surv_fun <- Survival(nom_fit)
  nom <- nomogram(
    nom_fit,
    fun = list(
      function(lp) 1 - surv_fun(36, lp),
      function(lp) 1 - surv_fun(60, lp)
    ),
    funlabel = c("Predicted 36-month risk", "Predicted 60-month risk"),
    fun.at = c(0.01, 0.03, 0.05, 0.10, 0.20, 0.40, 0.60),
    lp = FALSE,
    maxscale = 100
  )
  draw_nom <- function() {
    par(mar = c(4.6, 3.0, 3.0, 1.0), family = "Helvetica", col.axis = "#1F2933", col.lab = "#1F2933")
    plot(nom, xfrac = 0.34, cex.axis = 0.62, cex.var = 0.74, lmgp = 0.22, col.grid = NULL, tcl = -0.18)
    title("Supplementary Figure S1. Formal nomogram for OAI dynamic Model E", col.main = navy, cex.main = 1.1, font.main = 2)
    mtext("Risk axes are converted from the Cox model baseline survival at 36 and 60 months after the 24-month landmark.", side = 1, line = 3.2, cex = 0.68, col = gray)
  }
  png(file.path(figs, "supplementary_figure_s1_model_e_nomogram.png"), width = 11.5, height = 8.2, units = "in", res = 600, type = "cairo", bg = "white")
  draw_nom(); dev.off()
  pdf(file.path(figs, "supplementary_figure_s1_model_e_nomogram.pdf"), width = 11.5, height = 8.2, bg = "white")
  draw_nom(); dev.off()
  svg(file.path(figs, "supplementary_figure_s1_model_e_nomogram.svg"), width = 11.5, height = 8.2, bg = "white")
  draw_nom(); dev.off()
  options(old_opts)

  draw_calc <- function() {
    grid.newpage()
    grid.text("Model F-core research-use risk calculator", .50, .925, gp=gpar(fontface="bold", fontsize=18, col=navy))
    grid.text("OAI-derived common-variable Cox model with optional local recalibration", .50, .875, gp=gpar(fontsize=9.5, col=gray))

    box_grob(.31,.52,.43,.58,"", "#FAFCFE", col="#D8E2EC")
    grid.text("Inputs", .13, .775, just="left", gp=gpar(fontface="bold", fontsize=12.5, col=navy))
    labs <- c("Age", "Sex", "Pain score", "Baseline KL", "24-month KL", "Recalibration")
    vals <- c("64 years", "Female", "6 / 10", "2", "3", "MRKR")
    ys <- seq(.71,.34,length.out=6)
    for (i in seq_along(labs)) {
      grid.text(labs[i], .13, ys[i], just="left", gp=gpar(fontface="bold", fontsize=9.5, col=navy))
      box_grob(.39, ys[i], .16, .044, vals[i], "white", col="#CBD5E1", fontsize=8.4)
    }
    grid.text("KL worsening is derived automatically from paired KL grades.", .31, .245, gp=gpar(fontsize=8.2, col=gray))

    box_grob(.72,.52,.34,.58,"", "#FFFFFF", col="#D8E2EC")
    grid.text("Outputs", .58, .775, just="left", gp=gpar(fontface="bold", fontsize=12.5, col=navy))
    box_grob(.72,.655,.27,.13,"24-month recalibrated risk\n31.6%", light_green, fontsize=12, fontface="bold")
    box_grob(.72,.505,.27,.105,"Risk stratum\n25-50%", light_blue, fontsize=10.5, fontface="bold")
    box_grob(.72,.365,.27,.10,"Interpretation\nElevated research risk stratum", "#F4F8FF", fontsize=8.7, fontface="bold")

    grid.text("Version 0.1 | Formula basis: OAI Model F-core | Local recalibration: MRKR slope + baseline", .50, .175, gp=gpar(fontsize=8.2, col=gray))
    box_grob(.50,.095,.68,.075,"Research use only. Not validated for clinical decisions, surgical indication,\nor individual treatment without prospective local validation.", light_red, col=red, fontsize=7.7, fontface="bold")
  }
  grid_save("supplementary_figure_s2_model_f_calculator_mockup", 10.8, 5.8, draw_calc)

  sub <- subset(read_csv(file.path(tables, "oai_mrkr_highimpact_mrkr_subgroup_performance_24m.csv")), subgroup != "All MRKR core")
  sub <- sub[order(sub$auc_24m), ]; sub$subgroup <- factor(sub$subgroup, levels=sub$subgroup)
  pS3 <- ggplot(sub, aes(auc_24m, subgroup)) + geom_vline(xintercept=.5, linetype="dashed", color=gray) + geom_point(aes(size=n_knees), color=blue, alpha=.78) + geom_text(aes(label=paste0("n=",n_knees,", e=",events_by_24m)), hjust=-.05, size=2.6) + scale_size(range=c(2,7), guide="none") + coord_cartesian(xlim=c(.52,.79)) + labs(title="Supplementary Figure S3. MRKR subgroup performance at 24 months", x="24-month AUC", y=NULL) + theme_sci(9)
  save_plot(pS3, "supplementary_figure_s3_mrkr_subgroups", 8.5, 6.8)
}

fig1(); fig2(); fig3(); make_simple_figs(); supp_figs()
cat("Generated SCI high-resolution PNG/PDF/SVG figures.\n")
