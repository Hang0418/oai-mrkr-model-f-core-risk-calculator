#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(ggplot2)
})

args_file <- sub("--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])
script_dir <- if (is.na(args_file)) getwd() else dirname(normalizePath(args_file))
root <- normalizePath(file.path(script_dir, ".."))
tables <- file.path(root, "results", "tables")
figs <- file.path(root, "results", "figures")
dir.create(figs, recursive = TRUE, showWarnings = FALSE)

blue <- "#1F5D99"
navy <- "#0B2545"
teal <- "#1F7A5C"
red <- "#9B1C1C"
gray <- "#52616B"

theme_sci <- function(base_size = 10) {
  theme_minimal(base_size = base_size, base_family = "Helvetica") +
    theme(
      panel.grid.minor = element_blank(),
      panel.grid.major.x = element_blank(),
      panel.grid.major.y = element_line(color = "#E6EAF0", linewidth = 0.35),
      axis.title = element_text(color = "#1F2933"),
      axis.text = element_text(color = "#1F2933"),
      plot.title = element_text(face = "bold", color = navy, size = base_size + 2),
      plot.subtitle = element_text(color = gray, size = base_size),
      legend.position = "none",
      plot.margin = margin(10, 12, 10, 12)
    )
}

metrics <- read.csv(file.path(tables, "oai_24m_landmark_validation_metrics.csv"), stringsAsFactors = FALSE)
oai <- subset(metrics, model == "common_change" & validation == "OAI apparent/internal")[1, ]
check <- subset(metrics, model == "common_change" & validation == "CHECK external exploratory TKA")[1, ]

plot_df <- data.frame(
  group = factor(
    c("OAI\nmean predicted", "OAI\nobserved", "CHECK\nmean predicted", "CHECK\nobserved"),
    levels = c("OAI\nmean predicted", "OAI\nobserved", "CHECK\nmean predicted", "CHECK\nobserved")
  ),
  cohort = c("OAI", "OAI", "CHECK", "CHECK"),
  type = c("Mean predicted", "Observed", "Mean predicted", "Observed"),
  risk = c(oai$mean_predicted_risk, oai$observed_km_risk, check$mean_predicted_risk, check$observed_km_risk)
)

p <- ggplot(plot_df, aes(group, risk, fill = type)) +
  geom_col(width = 0.62, color = "white", linewidth = 0.35) +
  geom_text(aes(label = sprintf("%.1f%%", 100 * risk)), vjust = -0.45, size = 3.8, color = navy, fontface = "bold") +
  scale_fill_manual(values = c("Mean predicted" = blue, "Observed" = teal)) +
  scale_y_continuous(labels = function(x) sprintf("%.0f%%", 100 * x), limits = c(0, max(plot_df$risk) * 1.28), expand = expansion(mult = c(0, 0.02))) +
  labs(
    title = "Supplementary Figure 4. Exploratory CHECK validation\nof the OAI-derived CHECK-compatible dynamic model",
    subtitle = "Predicted versus observed 60-month post-landmark TKA/KR risk; CHECK validation was event-limited",
    x = NULL,
    y = "60-month risk"
  ) +
  theme_sci(11) +
  theme(
    axis.text.x = element_text(face = "bold"),
    plot.title = element_text(size = 12.0, lineheight = 1.04)
  )

stem <- "supplementary_figure_s4_check_exploratory_validation"
ggsave(file.path(figs, paste0(stem, ".png")), p, width = 8.2, height = 5.2, dpi = 600, bg = "white")
ggsave(file.path(figs, paste0(stem, ".pdf")), p, width = 8.2, height = 5.2, bg = "white")
ggsave(file.path(figs, paste0(stem, ".svg")), p, width = 8.2, height = 5.2, bg = "white")

message(file.path(figs, paste0(stem, ".png")))
