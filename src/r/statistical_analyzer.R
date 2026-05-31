# Statistical Analyzer — SDACS Phase 617
library(stats)

compute_metrics <- function(conflicts, resolutions) {
  list(
    resolution_rate = 1 - conflicts / (conflicts + resolutions),
    mean_conflicts = mean(conflicts),
    sd_conflicts = sd(conflicts)
  )
}

plot_performance <- function(data) {
  hist(data, main = "SDACS Performance", xlab = "Conflicts")
}
