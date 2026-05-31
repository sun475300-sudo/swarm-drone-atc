# statistical_analyzer.R
# R stub for statistical analysis of SDACS simulation results.
# Computes descriptive stats, conflict distributions, and Monte Carlo summaries.

# ---------------------------------------------------------------------------
# Dependencies (install if missing)
# ---------------------------------------------------------------------------
required_pkgs <- c("dplyr", "ggplot2", "jsonlite")
missing_pkgs  <- required_pkgs[!required_pkgs %in% installed.packages()[, "Package"]]
if (length(missing_pkgs) > 0) {
  message("Installing missing packages: ", paste(missing_pkgs, collapse = ", "))
  install.packages(missing_pkgs, repos = "https://cloud.r-project.org")
}

library(dplyr)
library(ggplot2)
library(jsonlite)

# ---------------------------------------------------------------------------
# Load simulation results
# ---------------------------------------------------------------------------

load_results <- function(path = "results/monte_carlo_results.json") {
  if (!file.exists(path)) {
    warning("Results file not found: ", path)
    return(NULL)
  }
  jsonlite::fromJSON(path, flatten = TRUE)
}

# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

summarize_conflicts <- function(df) {
  if (is.null(df)) return(NULL)
  df %>%
    summarise(
      n_runs          = n(),
      mean_conflicts  = mean(conflicts, na.rm = TRUE),
      sd_conflicts    = sd(conflicts, na.rm = TRUE),
      mean_resolution = mean(resolution_rate, na.rm = TRUE),
      p95_conflicts   = quantile(conflicts, 0.95, na.rm = TRUE)
    )
}

# ---------------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------------

plot_conflict_histogram <- function(df, out_path = "results/conflict_histogram.png") {
  if (is.null(df)) return(invisible(NULL))
  p <- ggplot(df, aes(x = conflicts)) +
    geom_histogram(binwidth = 1, fill = "steelblue", colour = "white") +
    labs(title = "Conflict Count Distribution (Monte Carlo)",
         x = "Conflicts per run", y = "Frequency") +
    theme_minimal()
  ggsave(out_path, p, width = 8, height = 5)
  message("Saved: ", out_path)
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main <- function() {
  message("SDACS Statistical Analyzer — stub")
  results <- load_results()
  summary <- summarize_conflicts(results)
  if (!is.null(summary)) print(summary)
  plot_conflict_histogram(results)
}

if (!interactive()) main()
