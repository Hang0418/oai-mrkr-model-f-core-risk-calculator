#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(survival)
})

args_file <- sub("--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])
script_dir <- if (is.na(args_file)) getwd() else dirname(normalizePath(args_file))
root <- normalizePath(file.path(script_dir, ".."))
fig_dir <- file.path(root, "results", "figures")
dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)

data <- read.csv(file.path(root, "derived", "validation", "oai_docx_plan_common_complete_dataset.csv"), stringsAsFactors = FALSE)
fit_model <- readRDS(file.path(root, "results", "models", "oai_revision_model_e.rds"))

predict_risk <- function(model, newdata, horizon) {
  bh <- basehaz(model, centered = FALSE)
  h0 <- approx(bh$time, bh$hazard, xout = horizon, method = "constant", rule = 2, f = 0)$y
  lp <- predict(model, newdata = newdata, type = "lp", reference = "zero")
  pmin(pmax(1 - exp(-h0 * exp(lp)), 0), 1)
}

data$risk60 <- predict_risk(fit_model, data, 60)
data$risk_group <- cut(data$risk60, breaks = c(-Inf, 0.05, 0.15, 0.30, Inf),
                       labels = c("<5%", "5-15%", "15-30%", ">30%"))
sf <- survfit(Surv(time, event) ~ risk_group, data = data)

cols <- c("#2C7BB6", "#00A6A6", "#F9A03F", "#C1121F")
png(file.path(fig_dir, "figure4_clinical_risk_cumulative_incidence.png"), width = 1300, height = 980, res = 150)
layout(matrix(c(1, 2), nrow = 2), heights = c(4.4, 1.45))
plot(sf, fun = "event", col = cols, lwd = 2, xlim = c(0, 96), ylim = c(0, 0.70),
     xlab = "Months after 24-month landmark", ylab = "Cumulative KR/TKA incidence",
     mark.time = FALSE, main = "Clinical risk strata based on Model E predicted 5-year risk")
legend("topleft", legend = levels(data$risk_group), col = cols, lwd = 2, bty = "n", title = "Predicted risk")
grid(col = "grey90")

times <- c(0, 24, 60, 96)
groups <- levels(data$risk_group)
risk_tab <- sapply(groups, function(g) {
  sapply(times, function(t) sum(data$risk_group == g & data$time >= t, na.rm = TRUE))
})
risk_tab <- t(risk_tab)
par(mar = c(3, 6.5, 0.5, 1))
plot(NA, xlim = c(0, 96), ylim = c(0.5, length(groups) + 0.8), axes = FALSE, xlab = "Months after landmark", ylab = "")
axis(1, at = times)
text(-15, length(groups) + 0.55, "No. at risk", xpd = TRUE, adj = 0, font = 2)
for (i in seq_along(groups)) {
  y <- length(groups) - i + 1
  text(-15, y, groups[i], xpd = TRUE, adj = 0, col = cols[i])
  text(times, y, risk_tab[i, ], col = "black")
}
dev.off()

cat("Generated figure4_clinical_risk_cumulative_incidence.png\n")
